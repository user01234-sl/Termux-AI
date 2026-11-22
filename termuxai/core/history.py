import os
import sqlite3
import stat
from pathlib import Path
from datetime import datetime, timezone


DATA_DIR = Path.home() / ".local" / "share" / "termuxai"
DB_FILE = DATA_DIR / "history.db"

MAX_CONVERSATIONS = 10
MAX_MESSAGES = 50


def _secure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DATA_DIR.is_symlink() or not DATA_DIR.is_dir():
        raise OSError("The history path must be a real directory.")
    os.chmod(DATA_DIR, 0o700)


def _prepare_database_file():
    """Create/open the DB as an owner-only regular file, refusing symlinks."""
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    flags = os.O_RDWR | nofollow
    if not nofollow and DB_FILE.is_symlink():
        raise OSError("The history database must not be a symbolic link.")
    try:
        fd = os.open(str(DB_FILE), flags | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if not nofollow and DB_FILE.is_symlink():
            raise OSError("The history database must not be a symbolic link.")
        fd = os.open(str(DB_FILE), flags)

    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("The history database is not a regular file.")
        os.fchmod(fd, 0o600)
    finally:
        os.close(fd)


def get_connection():
    _secure_data_dir()
    _prepare_database_file()

    connection = sqlite3.connect(DB_FILE, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA secure_delete = ON")
    # The containing directory is private, and the database is created 0600
    # before SQLite can create its rollback journal.
    os.chmod(DB_FILE, 0o600)
    return connection


def init_db():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL DEFAULT '',
                mode TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (conversation_id)
                    REFERENCES conversations(id)
                    ON DELETE CASCADE
            )
        """)


def create_conversation(mode):
    init_db()

    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO conversations
                (title, mode, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            ("", mode, now, now)
        )

        chat_id = cursor.lastrowid

        # Keep only the newest conversations.
        connection.execute(
            """
            DELETE FROM conversations
            WHERE id NOT IN (
                SELECT id
                FROM conversations
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
            )
            """,
            (MAX_CONVERSATIONS,)
        )

        return chat_id


def add_message(chat_id, role, content):
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO messages
                (conversation_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (chat_id, role, content, now)
        )

        connection.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE id = ?
            """,
            (now, chat_id)
        )

        # Keep only the newest messages in this conversation.
        connection.execute(
            """
            DELETE FROM messages
            WHERE conversation_id = ?
            AND id NOT IN (
                SELECT id
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id DESC
                LIMIT ?
            )
            """,
            (chat_id, chat_id, MAX_MESSAGES)
        )


def get_conversations():
    init_db()

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, mode, created_at, updated_at
            FROM conversations
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            (MAX_CONVERSATIONS,)
        ).fetchall()

        return [dict(row) for row in rows]


def get_conversation(chat_id):
    init_db()

    with get_connection() as connection:
        conversation = connection.execute(
            """
            SELECT id, mode, created_at, updated_at
            FROM conversations
            WHERE id = ?
            """,
            (chat_id,)
        ).fetchone()

        if conversation is None:
            return None, []

        rows = connection.execute(
            """
            SELECT role, content, timestamp
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (chat_id,)
        ).fetchall()

        return dict(conversation), [dict(row) for row in rows]


def clear_history():
    """Delete all saved conversations and compact the SQLite database."""
    init_db()
    with get_connection() as connection:
        connection.execute("DELETE FROM conversations")
        connection.commit()
        # secure_delete overwrites deleted cells where SQLite supports it;
        # VACUUM rebuilds the database without the deleted conversation pages.
        connection.execute("VACUUM")

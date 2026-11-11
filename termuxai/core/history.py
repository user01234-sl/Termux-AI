import sqlite3
from pathlib import Path
from datetime import datetime, timezone


DATA_DIR = Path.home() / ".local" / "share" / "termuxai"
DB_FILE = DATA_DIR / "history.db"

MAX_CONVERSATIONS = 10
MAX_MESSAGES = 50


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

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

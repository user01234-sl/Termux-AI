# Changelog

## [0.4.1] - Security hardening

- Refuse symbolic links for API-key, configuration, model-catalogue, local-server-log and SQLite history files where supported.
- Refuse symbolic links for private model/configuration/history/log directories.
- Create/open the SQLite history database with owner-only permissions before SQLite writes.
- Sanitize AI responses, history content and model names before terminal display to prevent markup/control-character spoofing.
- Validate configuration types, allowed modes and string lengths when loading or saving settings.
- Avoid printing raw model-download exceptions that may contain sensitive URLs.
- Add security regression tests for symlink handling, terminal text sanitization and configuration validation.

## [0.4.0] - Lightweight installation and usability

- Made llama.cpp optional during installation; online AI is the default.
- Added `--with-offline` to install the optional local inference engine.
- Documented how to add offline support after installation.
- Replaced animated connection indicators with simple status text.
- Removed a redundant active-model lookup before starting offline AI.


## 0.3.1

- Added `httpx` as an explicit runtime dependency for online and offline API calls.
- Moved the default offline model location to `~/.local/share/termuxai/models/`.
- Added `TERMUXAI_MODEL_PATH` to support a custom GGUF model path.
- Kept compatibility with the previous project-local `models/` location.
- Improved local server detection by checking both the health endpoint and the OpenAI-compatible models endpoint.
- Added regression tests for model path resolution and local server detection.


## 0.3.2

- Require HTTPS for remote Online AI endpoints; allow plain HTTP only for loopback local services.
- Reject endpoint URLs containing embedded credentials, query strings, or fragments.
- Disable redirects and environment-proxy inheritance for API requests.
- Use explicit connection, read, write, and pool timeouts.
- Avoid printing raw provider response bodies and raw network exceptions.
- Restrict configuration and API-key directories/files to owner-only permissions where supported.
- Write secrets and configuration atomically using owner-only temporary files.
- Add Online AI security regression tests.


## 0.3.3

- Restrict the conversation-history directory to owner-only permissions where supported.
- Restrict the SQLite history database file to owner-only permissions where supported.
- Enable SQLite secure-delete behavior and compact the database after clearing history.
- Add an option to delete all saved conversations from the history screen, with confirmation.
- Stop displaying arbitrary provider-generated text during connection tests.
- Add regression tests for history permissions and history deletion.


## 0.3.4

- Hide API keys from provider object representations and default debug output.
- Restrict local llama.cpp log directory and file permissions where supported.
- Stop printing raw local server log contents when startup fails; show the private log path instead.
- Replace raw conversation-history save exceptions with a generic privacy-preserving message.
- Add regression tests for credential-safe representations and local log permissions.


## 0.3.5

- Implemented Model Manager with streamed downloads of direct HTTPS GGUF links.
- Added a managed model catalogue with active-model selection and per-model context size, port, CPU threads and GPU-layer settings.
- Added safe model deletion and startup-command preview.
- Offline AI now launches the selected model using argument-list subprocess execution and binds only to loopback.
- Added download size limits, temporary-file handling, URL checks and owner-only model storage permissions.


## 0.3.6

- Added an Import Model option to copy existing local `.gguf` files into the managed model library.
- Kept the original model file unchanged during import.
- Added checks for missing files, unsupported extensions, empty files, oversized files and duplicate filenames.
- Register imported models in the same catalogue as downloaded models, with the same per-model startup settings.
- Added regression tests for successful copy imports and import validation.

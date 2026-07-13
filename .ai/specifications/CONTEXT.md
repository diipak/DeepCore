---
Category: Specification
Status: Approved
Dependencies: [architecture/ARCHITECTURE.md]
Source-of-truth: True
---

# DeepCore Context

## What is DeepCore?
DeepCore is a privacy-first, local-first personal intelligence platform. It stores, structures, and links personal data assets (such as documents, notes, transactions, and ideas) locally, providing a deterministic foundation before introducing AI agents or LLMs.

---

## Current Architecture

DeepCore uses a modular Python structure featuring:
- **FastAPI**: Lightweight web framework for local API access.
- **SQLAlchemy & SQLite**: Relational local storage with transactional integrity.
- **Pydantic V2**: Strict data validation.
- **Providers**: Sync frameworks to ingest, normalize, and register data from local or remote sources.

---

## Current Modules

- **`deepcore.storage.sqlite`**: Configures database sessions (`db.py`) and standard SQLAlchemy schema models (`models.py`).
- **`deepcore.core.objects`**: Validates the core schemas (`schemas.py`) including supported `ObjectType` values.
- **`deepcore.core.registry`**: Business logic encapsulation (`service.py`) for querying, registering, and archiving objects.
- **`deepcore.core.providers`**: Extensible interfaces for syncing third-party systems (`base.py`) and manual user input (`manual.py`).
- **`deepcore.api`**: FastAPI application routing (`main.py`, `routes.py`).

---

## Important Architecture Decisions

1. **SQLite Database Config**: The database file location is configurable using the `DEEPCORE_DB_PATH` environment variable, defaulting to `deepcore.db` locally.
2. **Object Types**: Validated against standard vocabulary matching local personal files: `document`, `project`, `video`, `note`, `repository`, `transaction`, `merchant`, and `idea`.
3. **Registry Schema Flexibility**: Added `metadata_json` (for provider-specific dynamic data) and `provider_version` (for migrations) fields directly to `registry_objects` to avoid schema bloat.
4. **ID / UUID Query Support**: Services accept either integer `id` or string `uuid` to locate objects, enabling fast lookups and external decoupling.

---

## Development Rules

1. **Deterministic First**: Ensure base functionality works without requiring AI or non-deterministic layers.
2. **Local-first Security**: Keep databases local; do not transmit personal data outside the client machine.
3. **Clean Dependencies**: Specify dependencies strictly in `requirements.txt` and install in `.venv` using the local virtualenv tools.

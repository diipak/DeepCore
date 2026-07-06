# DeepCore Registry MVP

DeepCore is a local-first personal intelligence platform. This module implements the foundational Registry MVP for organizing user objects and their relationships.

## Project Architecture

```
DeepCore/
├── requirements.txt
├── README.md
├── deepcore/
│   ├── config.py             # Configurable settings (DB path via DEEPCORE_DB_PATH)
│   ├── api/
│   │   ├── main.py           # FastAPI app initialization
│   │   └── routes.py         # HTTP endpoints (GET /objects, POST /objects, GET /objects/{id})
│   ├── core/
│   │   ├── objects/
│   │   │   └── schemas.py    # Pydantic schemas for object validation
│   │   ├── providers/
│   │   │   ├── base.py       # Provider ABC (discover, normalize, sync)
│   │   │   └── manual.py     # Manual provider implementation
│   │   └── registry/
│   │       └── service.py    # RegistryService business logic
│   └── storage/
│       └── sqlite/
│           ├── db.py         # Database engine and session provider
│           └── models.py     # SQLAlchemy DB models (registry_objects, registry_relationships)
└── tests/
    ├── conftest.py           # Testing fixtures and transactional DB setup
    └── test_registry.py      # Automated tests
```

## Setup & Running

1. **Initialize virtual environment and install dependencies**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run tests**:
   ```bash
   pytest tests/
   ```

3. **Run the local API server**:
   ```bash
   uvicorn deepcore.api.main:app --port 8000 --reload
   ```
   You can view the interactive documentation at `http://127.0.0.1:8000/docs`.

## Database Config
The database location is configurable via the `DEEPCORE_DB_PATH` environment variable. By default, it creates a `deepcore.db` SQLite file in the working directory.

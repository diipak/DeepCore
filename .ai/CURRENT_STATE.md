# Current State - DeepCore Registry MVP

## Phase 1 Completion

DeepCore Memory Foundation completed.

### Capabilities

- **Registry Object Model**: Relational representation of documents, projects, videos, notes, repositories, transactions, merchants, and ideas.
- **Multi-Provider Ingestion**: Structured base classes for deterministic third-party ingestion.
- **Intentional Capture Flow**: Unified ingestion gateway (`CaptureService`) with automated regex provider routing and metadata stamping.
- **Batch Sync Flow**: Local-first recursive directories processing to sync knowledge vaults.
- **CLI Interface**: Typer commands (`capture`, `list`, `stats`, `sync markdown`, `sync history`) for terminal usage.
- **Object Fingerprinting**: SHA256 checksums mapping to objects to isolate file content identification.
- **Sync History**: Database run logging (`sync_runs` table) tracking historical counts and statuses.
- **Missing Object Lifecycle**: Scoped note deletion tracking to flag deleted files as `missing` rather than destroying memory records.
- **Migration Safety**: Programmatic, self-healing database upgrades with compatibility for SQLAlchemy 2.x execution patterns.

### Validation

Real user data synced:
- YouTube objects
- Markdown knowledge folder

### Architecture Principles

- **Memory Preservation**: Existing DeepCore memory must survive application upgrades.
- **Migration Testing**: Database schema changes require accompanying migration tests to ensure safe schema transitions.

---

## Phase 2 — Recall Layer v0.1 (In Progress)

Phase 2 Recall Layer started. DeepCore can now retrieve stored memories.

### Capabilities

- **Registry Search**: Case-insensitive database query searching across titles, descriptions, and locations.
- **Object Detail Retrieval**: Retrieval of full metadata using database integer ID or UUID.
- **Recent Memories**: Fetching of newest active memory objects sorted by created_at.
- **Recall CLI Interface**: Typer commands (`find`, `show`, `recent`) for CLI-based deterministic memory retrieval.

---

## Active Capabilities

- **State-aware Syncing**: Automatically handles renames, copies, updates, and restores using content hashes.
- **Personal Knowledge Archiving**: Retains note metadata, relative/absolute directories, and size/creation info.
- **Registry stats calculations**: Breakdown of total objects by type and source system.

---

## Technical Debt

- **Future Migration System**:
  - The current schema updates use programmatic inspection and running manual `ALTER TABLE` statements (in `models.py:run_migrations`).
  - As the database schemas expand, migrate this self-healing structure to a formal migration tool like **Alembic** (or equivalent) to track schema history robustly.

---

## Next Recommended Step / Known Future Extensions

- **Obsidian Awareness Layer**:
  - Link discovery and parsing (`[[backlinks]]` and embeds)
  - Frontmatter metadata extraction (YAML/JSON block parse)
  - Obsidian tags extraction
  - Obsidian Canvas files parsing
- **Registry Relationship Management**:
  - Implement association layer endpoints (`registry_relationships` CRUD operations) to connect notes and videos.

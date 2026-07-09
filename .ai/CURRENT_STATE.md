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

## Phase 2 Completion

DeepCore Recall Layer v0.1 completed.

### Capabilities

- **Registry Search**: Case-insensitive database query searching across titles, descriptions, and locations.
- **Object Detail Retrieval**: Retrieval of full metadata using database integer ID or UUID.
- **Recent Memories**: Fetching of newest active memory objects sorted by `created_at` descending.
- **Recall CLI Interface**: Typer commands (`find`, `show`, `recent`) for CLI-based deterministic memory retrieval.

### Validation

- Unit and CLI integration tests in [test_recall.py](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/tests/test_recall.py) and [test_cli.py](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/tests/test_cli.py).

---

## Phase 3 Completion

Phase 3 Content Index started. DeepCore can now inspect contents of memories.

### Capabilities

- **Content Database Model**: A dedicated `content_index` table using the SQLAlchemy `Text` type, linked to registry objects with cascade deletion.
- **Deduplicated Content Indexing**: `ContentService` reads markdown files, hashes contents to prevent duplicate index runs, and updates existing records on modification.
- **Deterministic Content Search**: Raw structured text search using SQLite `LIKE` matching.
- **Content CLI Subcommands**: `deepcore index` for scanning and indexing all active memories, `deepcore content search` with context snippet generation at CLI layer, and `deepcore content show` for previews.

### Validation

- Migration safety tests in [test_content_index.py](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/tests/test_content_index.py) confirming existing databases upgrade safely without registry data loss.
- Comprehensive test suite in [test_content_index.py](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/tests/test_content_index.py) covering indexing, deduplication, modified file re-indexing, missing file resilience, and search query precision.
- Real user data validated:
  - Indexed 38 objects, successfully creating 37 content indexes and skipping 1 unmodified note.
  - Verified case-insensitive content search matches on terms like "ollama" from actual synced markdown notes and YouTube transcripts.

---

## Phase 4 Completion
 
Phase 4 Concept Extraction and Governance completed. DeepCore can now build first-class ontology building blocks from memories with a robust governance lifecycle.
 
### Capabilities
 
- **Ontology Foundation Models**: First-class concept objects of `object_type = "concept"` stored in the registry, and enriched `registry_relationships` holding extraction evidence.
- **Enriched Relationships Table**: Programmatic migration safely adding `evidence_json` and `relationship_source` to support tracking how relationships were discovered.
- **Deterministic Concept Extraction**: `ConceptService` extracts candidates via headings, technical term matching (PascalCase, ALLCAPS, numeric), and frequency detection.
- **Unique Logical Identity Matching**: Normalizes and deduplicates concepts using `normalized_key` in `metadata_json` under strict `status = "active"` constraints.
- **Concepts CLI Commands**: `deepcore concepts extract` for bulk running, `deepcore concepts list` (hiding ignored and merged by default), and `deepcore concepts show <concept>` to inspect connected memories.
- **Concept Governance**: Allows lifecycle status management (`candidate`, `approved`, `ignored`) and type classification (`tool`, `technology`, `project`, `person`, `organization`, `unknown`) stored cleanly inside `metadata_json`.
- **CLI Governance Commands**: `deepcore concepts ignore`, `deepcore concepts approve [--type]`, and `deepcore concepts merge` to manage the ontology dynamically.
- **Merge and Duplicate Safety**: Automatically reroutes relationships during merges, combines duplicate relationships to avoid duplicate edges, sums occurrences, and records merge origin trails in `evidence_json`.
- **Self-Healing Metadata Migration**: Automatically updates legacy concepts created before governance to have default candidate status and unknown type on-the-fly when read.
- **Click 8.2+ Option Patching**: Resolves options compatibility bug between Click 8.2+ and Typer 0.12 by forcing `click.BOOL` type mapping on boolean flags to prevent string/None flag parsing issues.
 
### Validation
 
- Self-healing database migration safety tests confirming database upgrades preserve existing tables and contents.
- Robust test suite in [test_concepts.py](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/tests/test_concepts.py) verifying heading, technical term, repeated phrase extraction, duplicate resolution, active status limits, and CLI commands.
- Governance test suite in [test_concept_governance.py](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/tests/test_concept_governance.py) verifying type whitelist validation, ignore/approve/merge transitions, self-healing metadata migration on read, duplicate relationship merging, and listing filters.

---

## Active Capabilities

- **State-aware Syncing**: Automatically handles renames, copies, updates, and restores using content hashes.
- **Personal Knowledge Archiving**: Retains note metadata, relative/absolute directories, and size/creation info.
- **Registry stats calculations**: Breakdown of total objects by type and source system.
- **Deterministic Memory Retrieval**: Retrieve active memories by case-insensitive search queries, display detailed object properties by database ID or UUID, and list recent active memories.
- **Content Indexing and Search**: Build a derived content index of active markdown files, update indexed content on file modifications, and query raw text content deterministically.
- **Concept Extraction and Linking**: Extract candidate concepts deterministically from indexed raw text, resolve duplicates using a logical normalized key identity, and map mentions relationships holding confidence and detailed validation evidence.
- **Concept Governance**: Lifecycle status management (`candidate`, `approved`, `ignored`) and type classification (`tool`, `technology`, `project`, `person`, `organization`, `unknown`) stored inside `metadata_json` with safe merge mechanics.

---

## Technical Debt

- **Future Migration System**:
  - The current schema updates use programmatic inspection and running manual `ALTER TABLE` statements (in `models.py:run_migrations`).
  - As the database schemas expand, migrate this self-healing structure to a formal migration tool like **Alembic** (or equivalent) to track schema history robustly.


---

## Phase 4.5 Completion

DeepCore Product Foundation completed.

This phase freezes the product direction before UI development begins.

### Purpose

Transform DeepCore from a CLI-first memory engine into a user-facing personal intelligence product while preserving the existing architecture.

### Added Product Documents

- `.ai/PRODUCT_VISION.md`
  - Defines the long-term vision:
    - Local-first personal intelligence layer
    - Object-centric architecture
    - Assistant-first interaction
    - Future native application compatibility
    - Plugin/provider expansion model

- `.ai/UI_ARCHITECTURE.md`
  - Defines frontend engineering rules:
    - Mobile-first design
    - Component-first implementation
    - API-driven clients
    - Light/dark theme tokens
    - Native app compatibility
    - Separation between intelligence engine and UI

- `.ai/APP_SCREENS.md`
  - Defines application experience:
    - Home
    - Memory
    - Object Detail
    - Graph Explorer
    - Assistant
    - Capture
    - Plugins

### Product Architecture Principles

- **Engine First**
  - DeepCore backend remains the source of truth.
  - UI clients consume capabilities through APIs.

- **Native Ready**
  - Web/PWA is the first client.
  - Future iOS, Android, and desktop apps reuse the same backend contracts.

- **Object Universal Design**
  - Notes, videos, repositories, PDFs, concepts, and future sources render through common object components.

- **Assistant as Interface Layer**
  - AI is connected to memory, concepts, content, and relationships.
  - Assistant providers remain replaceable (local/cloud/hybrid).

- **Graph as Exploration**
  - Knowledge graph loads contextually.
  - Avoid full database visualization by default.

### Validation

Product direction reviewed before UI implementation.

Future UI agents must follow:

1. CURRENT_STATE.md
2. PRODUCT_VISION.md
3. UI_ARCHITECTURE.md
4. APP_SCREENS.md

before generating frontend code.

---
## Next Recommended Step

### Phase 5 — Interface Layer v0.1

Build the first DeepCore user interface.

Priority:

1. API readiness review
2. Design system foundation
3. Responsive application shell
4. Home screen
5. Memory explorer
6. Object detail screen

Do not implement graph visualization, plugins, or assistant UI before the foundation screens exist.

---

## Known Future Extensions

---

## CLI Packaging Validation

Whenever CLI/package configuration changes:

Required verification:

```bash
pip install -e .
cd /tmp
deepcore --help
```

Reason: Prevents hidden dependency on the current working directory.
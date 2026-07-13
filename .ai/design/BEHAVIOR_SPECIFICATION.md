---
Category: Design
Status: Stable
Dependencies: [architecture/INTELLIGENCE_PIPELINE.md, architecture/PLATFORM_ARCHITECTURE.md, design/CONTEXT.md]
Source-of-truth: True
---

# DeepCore Behavior Specification

This living document specifies the runtime behaviors, state transitions, and execution contracts of the DeepCore platform. 

> **Core Philosophy**  
> Behavior specifications define what DeepCore must do, not how it is implemented.

---

## Section 1: Knowledge Ingestion

### 1. Purpose
The Knowledge Ingestion behavior governs how raw digital content from external sources enters DeepCore, normalizes into canonical records, and propagates through the system to update active context and workspaces.

### 2. Trigger
Ingestion is initiated by:
*   A user command requesting a manual sync.
*   A scheduler event triggering a periodic background sync.
*   A directory-watcher event detecting modifications in tracked local folder sources.

### 3. Inputs
*   A configured module Provider instance.
*   Configuration parameters (directory paths, credentials, resource limits).
*   State tracking data (the timestamp of the last successful sync, historical content hashes).

### 4. Preconditions
*   The target provider module is enabled and its capability contracts are negotiated and approved.
*   Target hardware matches or exceeds the required **Capability Tier** baseline for the provider.
*   The database is initialized, and migration versions match.

### 5. Execution (Knowledge Entry Lifecycle)

Synchronization runs execute as a pipeline of sequential stages:

```
[Raw Source File]
       │
       ▼ (Ingest & Parse)
[Provider Stream]
       │
       ▼ (Identity Resolution & Hashing)
[Canonical Object]
       │
       ▼ (Extract & Index)
[Content Index] ──► [Relationship Evaluation]
                               │
                               ▼ (Trigger Rules)
                       [Signal Invalidation]
                               │
                               ▼ (grounding)
                       [Evidence Update]
                               │
                               ▼ (Thematic Synthesis)
                       [Discovery Refresh]
                               │
                               ▼ (Session Assembly)
                       [Context Refresh]
                               │
                               ▼ (Glow/Render)
                       [Workspace Update]
```

#### Step 5.1: Extraction & Normalization
1.  **Read Source**: The provider reads raw content streams (e.g., Markdown files, transaction APIs).
2.  **Schema Check**: The provider normalizes the data into standard `RegistryObject` fields (`title`, `source_system`, `external_id`, `location`, `description`).
3.  **Content Hash**: A SHA-256 hash is computed over the raw contents to track updates and support de-duplication.

#### Step 5.2: Object Identity Rules
To ensure zero duplicate records, the kernel resolves identity through strict matching rules:
*   **Unique Primary Key**: Resolved using a composite key: `source_system` + `external_id`.
*   **Fallback Key**: If `external_id` is missing, the canonical location URI (e.g., absolute file path) acts as the identity anchor.
*   **Duplicate Detection**:
    *   If the composite key matches an existing record:
        *   Compare the new `content_hash` with the database `content_hash`.
        *   If hashes match, skip creation and mark the record as `existing`.
        *   If hashes differ, update the object fields and mark it as `updated`.
    *   If no matching composite key exists:
        *   Create a new entry with a unique UUID, setting status to `active`.
*   **Provenance Preservation**: Every record must write and maintain its immutable `source_system` string and initial `created_at` timestamp.

#### Step 5.3: Incremental Sync States
The system must support the following synchronization states:
*   **First Import**: Ingests all available items, writes the initial sync watermark, and populates the cache.
*   **Repeated Sync**: Reads the last sync watermark. Only scans or fetches content modified since that timestamp.
*   **Deleted Content Handling**:
    *   If an item is missing from the source system:
        *   The Canonical Object's status transitions to `missing`.
        *   It is **never** hard-deleted from the database during sync. This preserves historical context and downstream links.
*   **Renamed Content Handling**:
    *   If a file path changes but its size and content hash match an existing `missing` or `archived` object:
        *   Update the `location` field of the existing object.
        *   Revert its status to `active`.
        *   Do not create a new object.
*   **Modified Content Handling**: Updates the `content_hash`, `updated_at`, and corresponding fields, triggering downstream recomputation.
*   **Failed & Resumed Sync**:
    *   If a sync run is interrupted (e.g. timeout, network crash):
        *   Save the current watermark for successfully processed items.
        *   Mark the sync run as `failed` with error logs in the database.
        *   Upon resumption, the provider queries from the last saved watermark.

#### Step 5.4: Event Propagation & Dirty Flags
When an object is registered or updated, the system invalidates downstream data layers incrementally:

```
┌──────────────────────┐      ┌─────────────────────────┐      ┌──────────────────────────┐
│  Object Registered/  │ ───► │  Mark Content Index     │ ───► │  Mark Relationships      │
│  Updated Event       │      │  as Dirty               │      │  as Dirty                │
└──────────────────────┘      └─────────────────────────┘      └──────────────────────────┘
                                                                            │
                                                                            ▼
┌──────────────────────┐      ┌─────────────────────────┐      ┌──────────────────────────┐
│  Flag active Context │ ◄─── │  Invalidate affected    │ ◄─── │  Re-evaluate Signals     │
│  as Out-of-date      │      │  Evidence & Discoveries │      │  on dirty paths          │
└──────────────────────┘      └─────────────────────────┘      └──────────────────────────┘
```

*   **Content Index**: Marked `dirty` if `content_hash` changes. Re-indexing is triggered.
*   **Relationships**: If an object is updated, the system re-evaluates relationship builders targeting the modified object ID. Unchanged parts of the graph remain clean.
*   **Signals**: Spikes and velocity anomalies are recalculated over the updated sliding window.
*   **Evidence & Discoveries**: Backing evidence packages are refreshed. Discoveries that depend on altered evidence are scheduled for re-synthesis.

### 6. Outputs
*   An updated database containing normalized `RegistryObject` records.
*   A populated `SyncRun` auditing entry (recording start/stop times and counts).
*   Staged downstream `dirty` events in the system's event broker.

### 7. Postconditions
*   The sync watermark is updated to the completion time of the sync run.
*   All active database sessions are committed.
*   No orphaned relationships point to missing IDs.

### 8. Failure Handling
*   **Database Constraints**: If a transaction fails (e.g., unique key violation), the sync run aborts, rolling back all uncommitted changes.
*   **Transient Source Failures**: If a network API fails mid-run, the sync run retries up to three times using exponential backoff before terminating.
*   **Corruption Recovery**: If an invalid schema is encountered, the specific record is skipped, logged in `errors_json`, and the sync continues.

### 9. Invariants
*   **Unique Identity Invariant**: There can never be more than one Canonical Object with the same `source_system` and `external_id` (or path).
*   **Provenance Invariant**: An object's `source_system` and `created_at` timestamp are immutable once written.
*   **Local Preservation Invariant**: A sync run must never delete objects from the local database; missing items must only change state to `missing` or `archived`.
*   **Minimal Execution Invariant**: Full re-indexing of the database is prohibited during sync; only changed or flagged items are processed.

### 10. Observability
Ingestion progress is exposed via standard system events and metrics:
*   **Lifecycle Events emitted**:
    *   `SyncStarted`: Fired when a provider sync commences.
    *   `ObjectDiscovered`: Fired when a raw item is parsed.
    *   `ObjectCreated` / `ObjectUpdated`: Fired on database commit of new or modified objects.
    *   `SyncCompleted`: Fired upon successful run.
    *   `SyncFailed`: Fired when a run aborts, containing error payloads.
*   **Performance Metrics Tracked**:
    *   `sync_duration_ms`: Total execution time of the sync.
    *   `errors_count`: Number of skipped corrupted items.
*   **Sync Counters**:
    *   `objects_scanned`, `objects_created`, `objects_existing`, `objects_updated`, `objects_missing`.

---

## Sections 2–9 (Reserved for Future Behavior Specifications)

### Section 2: Object Lifecycle
*Reserved for future behavioral specifications governing state transitions (active, missing, archived, merged) and database cleanup limits.*

### Section 3: Relationship Lifecycle
*Reserved for future behavioral specifications governing how relationships decay, reinforce over time, and evaluate source confidence.*

### Section 4: Signal Lifecycle
*Reserved for future behavioral specifications governing mathematical trend analysis, sliding window triggers, and alarm threshold behaviors.*

### Section 5: Discovery Lifecycle
*Reserved for future behavioral specifications governing LLM-driven thematic synthesis and semantic concept categorization.*

### Section 6: Context Assembly
*Reserved for future behavioral specifications governing how the Context Engine compiles context packages matching user focus.*

### Section 7: Conversation Behavior
*Reserved for future behavioral specifications governing cited context Q&A, user alignment loops, and Ollama inference context limits.*

### Section 8: Planner Behavior
*Reserved for future behavioral specifications governing DAG validation, condition checks, retry schedules, and resume states.*

### Section 9: Workspace Behavior
*Reserved for future behavioral specifications governing shell transitions, active surface synchronization, and graph node focus states.*

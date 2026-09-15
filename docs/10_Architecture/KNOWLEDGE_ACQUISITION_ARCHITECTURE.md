# Knowledge Acquisition Platform Architecture Specification

This document serves as the constitutional reference for every current and future source connector in DeepCore. It defines the architectural boundaries, contracts, invariants, and lifecycle states that protect the integrity of the DeepCore Kernel.

---

## 1. Purpose

The Knowledge Acquisition Platform is the boundary interface between the fragmented components of the user's **Knowledge Ecosystem** (filesystems, calendars, third-party APIs, communication channels, devices) and the unified **DeepCore Registry**. 

Its primary purposes are:
- **Kernel Decoupling**: To isolate external API complexities, credentials, pagination protocols, and data formats from DeepCore's database and intelligence systems.
- **Local-First Reliability**: To orchestrate synchronization runs with structured retries, rate limiting, and cursor persistence to prevent data loss or rate-limiting blockages.
- **Privacy and Data Sovereignty**: To process and normalize all data locally on the user's hardware before it is ingested, keeping credentials and intermediate raw payloads in-memory and out of long-term logs.

---

## 2. Knowledge Sources and Workspace Organization

To maintain organization, DeepCore distinguishes between the following three components:

- **Connector**: The installable extension package containing execution code (e.g., the Filesystem Connector). Connectors are registered in the Capability Registry.
- **Knowledge Source**: A configured instance of a connector bound to a specific location or account (e.g., configuring the Filesystem Connector twice: once for a "Personal Vault" and once for a "Work Vault").
- **Workspace**: The user's cognitive namespace that mounts one or more Knowledge Sources.

A single Connector package can back multiple independent Knowledge Sources. This distinction is a permanent architectural invariant.

---

## 3. Architectural Boundary

A permanent system invariant governs the ingestion flow:

```
[ Knowledge Ecosystem ]
         │
         ▼
 ┌───────────────┐
 │   Connector   │   ◄─── Everything above this line is pluggable, replaceable, and source-specific.
 └───────┬───────┘
         │
         ▼
 ┌───────────────┐
 │  Translator   │
 └───────┬───────┘
============================= ARCHITECTURAL BOUNDARY =============================
         │
         ▼
 ┌───────────────┐
 │  Acquisition  │
 │    Runtime    │   ◄─── Everything below this line is the immutable DeepCore Kernel.
 └───────┬───────┘
         │
         ▼
 ┌───────────────┐
 │   Ingestion   │
 │    Service    │
 └───────┬───────┘
         │
         ▼
 ┌───────────────┐
 │   Registry    │
 └───────┬───────┘
         │
         ▼
 ┌───────────────┐
 │ Relationship  │
 │    Engine     │
 └───────┬───────┘
         │
         ▼
 ┌───────────────┐
 │    Signals    │
 └───────┬───────┘
         │
         ▼
 ┌───────────────┐
 │    Context    │
 └───────────────┘
```

- **Pluggable Domain**: Connectors and Translators are treated as lightweight extensions. They are completely replaceable and can be added, updated, or removed without changing any core database schemas or logic.
- **Kernel Domain**: The Acquisition Runtime, Ingestion Service, and downstream layers belong strictly to the DeepCore Kernel. No external connector code is permitted to bypass these services to write directly to database tables, register objects, or write to file search indices.

---

## 4. Connector Architecture

To maintain separation of concerns, the platform splits ingestion responsibilities into four distinct layers:

```
              ┌───────────────────────────────┐
              │  Source in Knowledge Ecosystem │
              └───────────────┬───────────────┘
                              │ (Raw API / Local Disk)
                              ▼
              ┌───────────────────────────────┐
              │           Connector           │  ◄── Technical Contract: communicates with source
              └───────────────┬───────────────┘
                              │ (Raw Objects + Vocabulary)
                              ▼
              ┌───────────────────────────────┐
              │          Translator           │  ◄── Semantic Contract: pure data mapping
              └───────────────┬───────────────┘
                              │ (DeepCore Objects + Provenance)
                              ▼
              ┌───────────────────────────────┐
              │      Acquisition Runtime      │  ◄── Runtime Boundary: orchestration, retries, cursors
              └───────────────┬───────────────┘
                              │ (Execution Events)
                              ▼
              ┌───────────────────────────────┐
              │       Ingestion Service       │  ◄── Persistence Boundary: deduplication, validation
              └───────────────┬───────────────┘
                              │ (SQL Transactions)
                              ▼
              ┌───────────────────────────────┐
              │        Registry Store         │
              └───────────────────────────────┘
```

### Connector Responsibilities
The **Connector** owns communications with the source system in the Knowledge Ecosystem. It handles networking, API authentication protocols (OAuth2, API keys), local filesystem walking, API pagination, and event listening. It does not import or reference any internal DeepCore registry schemas or database helpers.

### Translator Responsibilities
The **Translator** handles semantic mapping. It takes raw payloads generated by the connector and maps them into inputs suitable for registry object creation (`RegistryObjectCreate`). Translators live inside DeepCore but are completely pure (no side effects).

### Acquisition Runtime Responsibilities
The **Acquisition Runtime** orchestrates execution. It coordinates sync runs, manages retry logic with backoff, saves high-watermark cursors on success, captures stack traces on failure, and updates connector state database records. To preserve the runtime/observability separation, the runtime does not persist telemetry. Instead, it emits execution events which are consumed and recorded by the Platform Observability subsystem.

### Ingestion Service Responsibilities
The **Ingestion Service** owns registry persistence. It enforces schema validation on incoming translated records, performs content hash deduplication to skip unchanged entries, inserts or updates objects within transactional database sessions, and writes content indexes for indexing.

---

## 5. Connector Contracts & Acquisition Modes

Every provider must satisfy two distinct contracts: a **Technical Contract** defining how the runtime executes the provider, and a **Semantic Contract** defining the vocabulary and structure of the data it returns.

### A. Technical Contract
The technical contract dictates execution methods implemented by the Connector class:

- `authenticate(credentials: dict) -> HealthStatus`
  - Verifies credentials and test connections before activating sync runs.
- `discover(ctx: SyncContext) -> Generator[dict, None, None]`
  - Scans the source repository for a full sync. Yields raw objects.
- `sync(ctx: SyncContext) -> Generator[dict, None, None]`
  - Performs an incremental sync run starting from the timestamp/index recorded in `ctx.cursor_state`. It updates the cursor in-place.
- `watch(ctx: SyncContext) -> Generator[dict, None, None]`
  - Runs a persistent listener (e.g. filesystem watcher or WebSocket subscriber) to stream live changes.
- `health(ctx: SyncContext) -> HealthStatus`
  - Validates latency, token expiration, and service accessibility.

### B. Acquisition Modes
Connectors declare which of the following acquisition modes they support inside their `ProviderDescriptor`:
- **Pull**: The connector periodically scans the source repository (e.g., GitHub issue scans, Gmail message sweeps, Calendar queries).
- **Push**: The connector receives events immediately via local webhooks, socket connections, or system notifications (e.g., native notifications, external webhook integrations).
- **Hybrid**: The connector runs an initial full scan on startup, followed by a persistent real-time event listener (e.g., Filesystem Connector scanning folders and then watching them via file event APIs).

### C. Semantic Contract
The semantic contract specifies the structural and vocabulary definitions the connector outputs, which the Translator then normalizes. It contains two parts:

#### 1. Object Model (Structural Framework)
Defines the primary schemas representing external units of data. For example:
- **Filesystem**: `File`, `Folder`.
- **Calendar**: `Event`, `Participant`, `Location`, `Reminder`.
- **GitHub**: `Repository`, `PullRequest`, `Commit`, `Issue`.

#### 2. Vocabulary (Semantic Meaning)
Standardizes terminology from external API keys to normalized values understood by DeepCore. This avoids hardcoding source status variables inside the core Registry:
- **Calendar Vocabulary**: Maps roles like Organizer/Attendee and statuses like Accepted/Declined/Tentative to internal constants.
- **GitHub Vocabulary**: Maps states like Open/Closed/Merged/Draft/Review to standard statuses.

---

## 6. Connector Classification & Reference Implementation Strategy

To make the platform extensible for multiple data types, connectors are classified into four distinct categories. To ensure predictability, each category is anchored by a single **Reference Implementation** that must be validated first before expanding to other systems.

1.  **Source Connectors**: 
    Integrations that ingest primary context objects (such as emails, tasks, issues, and notes).
    *Reference Source Connector*: **Filesystem**
2.  **Index Connectors**: 
    Background scanners that index local OS systems ambiently.
    *Reference Index Connector*: **Apple Spotlight**
3.  **Intelligence Connectors**: 
    Local enrichment engines (such as transcription or extraction) that post-process raw captured items.
    *Reference Intelligence Connector*: **OCR**
4.  **Export Connectors**: 
    Outward-facing connectors that serialize and export Registry components.
    *Reference Export Connector*: **Markdown Export**

---

## 7. Translation Invariants (Purity Guarantees)

To prevent code churn and side effects during data normalization, **Translators must be pure functions**. The translation layer must enforce the following strict guarantees:

- **No DB Access**: Translators cannot issue queries, updates, or checks against any database.
- **No Network Requests**: Translators must process inputs using local, in-memory logic only. No external HTTP or socket requests are allowed.
- **No Relationship Calculations**: Translators do not identify linkages, WikiLinks, or correlations. Those are handled downstream by the Relationship Engine.
- **No AI Invocation**: Translators cannot prompt LLMs, query embedding models, or use reranking algorithms.
- **No Registry Writes**: Translators only return Pydantic schemas or maps representing registry objects. Writing records is the responsibility of the Ingestion Service.

---

## 8. Provenance Model

Traceability is a fundamental cognitive commitment in DeepCore. The system must always be able to explain exactly where a memory originated. Thus, every object created via the Acquisition Platform must have an explicit, **immutable** `Provenance` model attached:

```python
class Provenance(BaseModel):
    connector_id: str          # Identifies the connector package (e.g. 'github')
    provider_id: str           # Identifies the connector type (e.g. 'github')
    source_system: str         # Identifies the source name (e.g. 'Work Obsidian Vault')
    external_id: str           # Stable, unique ID in the source system (e.g. email UUID)
    acquisition_timestamp: dt  # Ingestion UTC timestamp
    sync_run_id: str           # The UUID of the sync run that processed this object
```

### Why Provenance is Immutable
- **Registry Integrity**: Provenance metadata represents source truth. Allowing modifications would break the trace back to original source files or APIs.
- **Self-Healing Deduplication**: The system uses the immutable `(source_system, external_id)` key pair for incremental delta updates and deduplication.

---

## 9. Permission Model

DeepCore operates under a capability-based security model. Rather than classifying connectors under arbitrary categories, the platform requires connectors to declare a list of requested **Permission Capabilities**:

- `filesystem`: Access to read or write local directories or folders.
- `network`: Permission to establish socket connections to external services.
- `calendar`: Read access to native device calendar entries.
- `contacts`: Read access to native contact databases.
- `mail`: Access to device mailing accounts or system-level mail clients.
- `photos`: Access to native photo storage databases.
- `notifications`: Permission to post notifications or banners to the user.
- `clipboard`: Permission to monitor clipboard or pasteboard changes.

The Acquisition Manager intercepts and logs these permissions, preparing the environment or warning users during setup.

---

## 10. Future Evolution

This architecture allows future connectors to be added seamlessly without modifications to the DeepCore Kernel:

```
                            ┌───────────────────┐
                            │  DeepCore Kernel  │
                            └─────────▲─────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │ (Standard import of CONNECTOR_DESCRIPTOR)      │
              │                                               │
    ┌─────────┴─────────┐           ┌─────────┴─────────┐   ┌─┴─────────────────┐
    │  Gmail Connector  │           │ Calendar Connector│   │ GitHub Connector  │
    └───────────────────┘           └───────────────────┘   └───────────────────┘
```

When integrating a new system (such as Gmail, Calendar, Apple Ecosystem, GitHub, Outlook, Slack, or a local file scanner):
1.  **Package Creation**: Implement standard modules (`connector.py`, `translator.py`, `descriptor.py`, `schema.py`) under `deepcore/connectors/<connector_name>/`.
2.  **Contract Fulfillment**:
    - The Connector implements the technical contract (polling APIs, handling rate limits).
    - The Translator maps raw outputs (emails, events, pull requests) to standard registry object types using its semantic contracts.
3.  **Discovery**:
    - Expose the provider's capabilities and config parameters inside a single exported `CONNECTOR_DESCRIPTOR` (type `ProviderDescriptor`) variable in the package's `__init__.py`.
    - The `AcquisitionManager` dynamically discovers and registers this descriptor during startup capability scanning, making it instantly available in the platform config views.
4.  **No Core Changes**: The core Registry, Ingestion Service, Database, and Downstream relationship parsers remain untouched, allowing modular upgrades.

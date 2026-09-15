---
Category: Governance
Status: Experimental
Dependencies: [architecture/PRODUCT_VISION.md, governance/ROADMAP.md]
Source-of-truth: True
---

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

- Unit and CLI integration tests in [test_recall.py](./tests/test_recall.py) and [test_cli.py](./tests/test_cli.py).

---

## Phase 3 Completion

Phase 3 Content Index started. DeepCore can now inspect contents of memories.

### Capabilities

- **Content Database Model**: A dedicated `content_index` table using the SQLAlchemy `Text` type, linked to registry objects with cascade deletion.
- **Deduplicated Content Indexing**: `ContentService` reads markdown files, hashes contents to prevent duplicate index runs, and updates existing records on modification.
- **Deterministic Content Search**: Raw structured text search using SQLite `LIKE` matching.
- **Content CLI Subcommands**: `deepcore index` for scanning and indexing all active memories, `deepcore content search` with context snippet generation at CLI layer, and `deepcore content show` for previews.

### Validation

- Migration safety tests in [test_content_index.py](./tests/test_content_index.py) confirming existing databases upgrade safely without registry data loss.
- Comprehensive test suite in [test_content_index.py](./tests/test_content_index.py) covering indexing, deduplication, modified file re-indexing, missing file resilience, and search query precision.
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
- Robust test suite in [test_concepts.py](./tests/test_concepts.py) verifying heading, technical term, repeated phrase extraction, duplicate resolution, active status limits, and CLI commands.
- Governance test suite in [test_concept_governance.py](./tests/test_concept_governance.py) verifying type whitelist validation, ignore/approve/merge transitions, self-healing metadata migration on read, duplicate relationship merging, and listing filters.

---

## Active Capabilities

- **State-aware Syncing**: Automatically handles renames, copies, updates, and restores using content hashes.
- **Personal Knowledge Archiving**: Retains note metadata, relative/absolute directories, and size/creation info.
- **Registry stats calculations**: Breakdown of total objects by type and source system.
- **Deterministic Memory Retrieval**: Retrieve active memories by case-insensitive search queries, display detailed object properties by database ID or UUID, and list recent active memories.
- **Content Indexing and Search**: Build a derived content index of active markdown files, update indexed content on file modifications, and query raw text content deterministically.
- **Concept Extraction and Linking**: Extract candidate concepts deterministically from indexed raw text, resolve duplicates using a logical normalized key identity, and map mentions relationships holding confidence and detailed validation evidence.
- **Concept Governance**: Lifecycle status management (`candidate`, `approved`, `ignored`) and type classification (`tool`, `technology`, `project`, `person`, `organization`, `unknown`) stored inside `metadata_json` with safe merge mechanics.
- **Deterministic Relationship Processing**: Extends ingestion pipeline with Stage 2 (Relationship Engine) executing rules for WikiLinks, parent-child hierarchies, folders, shared project tags, duplicates, and versions.
- **Structured Evidence & Symmetrical Complements**: Stores structured JSON evidence (type, detail, location, producing stage), tracks provenance under `"relationship_engine"`, and commits relationships in both directions.
- **Product Experience Foundation**: Established a comprehensive Experience Architecture Specification defining cognitive commitments, experience principles, conceptual product objects, and focus-driven navigation paradigms.

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

- `.ai/architecture/PRODUCT_VISION.md`
  - Defines the long-term vision:
    - Local-first personal intelligence layer
    - Object-centric architecture
    - Assistant-first interaction
    - Future native application compatibility
    - Plugin/provider expansion model

- `.ai/architecture/UI_ARCHITECTURE.md`
  - Defines frontend engineering rules:
    - Mobile-first design
    - Component-first implementation
    - API-driven clients
    - Light/dark theme tokens
    - Native app compatibility
    - Separation between intelligence engine and UI

- `.ai/design/APP_SCREENS.md`
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




# Current UI Direction

Phase 6.1 produced a working navigable shell.

Decision:
Before adding more features, DeepCore moves from page navigation to Workspace Architecture.

Next:
Phase 6.3 — Intelligence Workspace Alignment

Goal:
Refactor composition only.
Do not rebuild backend.
Do not rebuild components unnecessarily.

---

# Phase 6.3 — Intelligence Workspace Alignment

The experimental 4-column workspace model (Phase 6.2) was rejected as it separated exploration from understanding.

Final workspace architecture:
- Memory Universe
- Conscious Workspace
- Context Intelligence

## Architectural Clarifications

### 1. Memory Universe
- The Memory Universe is not a file explorer clone.
- It represents knowledge spaces, sources, recent activity, saved objects, and extensions/providers.
- Tree navigation is only one possible presentation of this universe; we must avoid building a filesystem UI.

### 2. Context Intelligence
- The Assistant is not a reasoning log/debug panel.
- It provides conversation, contextual actions, insights, generated artifacts, and references to memory objects.
- It should feel like a personal intelligence partner.

### 3. Implementation Direction
- Preserve existing APIs.
- Preserve reusable components.
- Refactor composition only.
- Center workspace owns primary interaction.
- Assistant is contextual and resizable.
- Navigation is discovery, not the application itself.

Avoid returning to page-based dashboard patterns.

---

## Phase 6.4 Completion — Conscious Workspace Experience Layer

Evolved the three-column workspace layout into a premium, focused read-and-explore environment:

- **Conscious Workspace Home:** Replaced the generic metrics dashboard with a personalized greeting header (`"Welcome Back"`) and status badge (`"Private Memory Active"`). Simplified column hierarchy to center on "Continue Reading" (recent cards) and "Discover Connections" (concept chips), keeping statistics secondary.
- **Reading-Focused Document Viewer:** Pruned all technical database attributes (file paths, database metadata, etc.) from the center pane to prevent information duplication. Updated `MarkdownViewer.tsx` to handle blockquotes (`accent-memory` left border) and render custom language tags on scroll-contained code blocks.
- **Context Ownership:** Assigned all technical metadata (file path, provider version, date indexed) exclusively to the Context Intelligence panel (right sidebar).
- **Aesthetic Accents:** Introduced the Semantic Pastel Color System, mapping blue (`--accent-memory`) to markdown notes, violet (`--accent-concept`) to concepts/graphs, cyan (`--accent-assistant`) to AI state, red (`--accent-video`) to videos, and green (`--accent-action`) to actions/success.

---

## Phase 6.4.1 Completion — Workspace Experience Validation Fixes

Completed a validation pass resolving UI discrepancies and interaction behavior:

- **Explicit Home Sidebar Navigation:** Added a permanent `"Home / Awareness"` link inside the sidebar Knowledge group, highlighted dynamically on `/` routes.
- **Inline Search Palette:** Fixed the search input in `Home.tsx` to stay visible and active during user typing, query memories and concepts concurrently, display dynamic inline search result cards, and navigate only upon explicit result selection.
- **Draggable Assistant Resize Handle:** Implemented a mouse-driven draggable left handle for the Context Intelligence panel. Constrains widths within `280px` min and `600px` max, fallback to `360px`, and persists settings to `localStorage`. Fallbacks gracefully on mobile screen sizes.
- **Accents Visibility & Audit:** Color-coded list highlights, card category badges (`Note • Obsidian` vs `Video • YouTube`), and error indicator components to match their semantic pastel space, making colors informational rather than decorative.
- **Vite Cache Cleared:** Evicted stale dependency caches to ensure client builds serve the latest bundled code. Passes production compilation cleanly (`tsc -b && vite build`).

---

## Phase 7 Completion — Context Engine Core

Implemented and validated the DeepCore Context Engine, establishing the core framework of the Intelligence Layer:

- **Unified ContextRequest Model:** Introduced a reusable, platform-agnostic `ContextRequest` model consuming optional trigger object references (`trigger_object_uuid`) and/or text queries, preserving calling metadata and reserving options for future expansion policies.
- **Evidence-Based Packaging:** Designed `ContextPackage` as an immutable, stable public contract returning matching concepts and memories alongside structured `EvidenceItem` annotations (matched queries/concepts, relationship types, traversal distance, and direct flags) instead of arbitrary heuristics or scores.
- **Modular Retrieval Orchestration:** Decoupled Context Engine from the database by introducing reusable, generic traversal methods in `RegistryService` (`get_connected_concepts`, `get_referenced_memories`, `get_objects_mentioning_concepts`, `get_objects_referencing_objects`, and `get_concept_connection_count`).
- **REST API Delivery:** Replaced placeholder assistant context endpoints in `assistant.py` with fully functional `POST` and `GET /assistant/context` routes delivering context packages to clients.
- **Deterministic Validation:** Delivered unit tests in `tests/test_context_engine.py` validating trigger resolution, query searches, transitive expansion, deterministic sorting order (by connection count, relationship priority, creation date, and UUID), and API route responses.

---

## Phase 8 Proposal — Planner, Skills, and Tools Architecture Design

Registered the Planner, Skills, and Tools design specifications in the workspace files:

- **[PLANNER_DESIGN.md](./.ai/design/PLANNER_DESIGN.md)**: Establishes the philosophy, data models, public platform APIs, lifecycle engine, and mock-based validation strategy for the deterministic execution planner.
- **[SKILLS_DESIGN.md](./.ai/design/SKILLS_DESIGN.md)**: Establishes the philosophy, boundaries, contracts, execution lifecycle, registration framework, and recursion safety guidelines for Skills inside the DeepCore Intelligence Layer.
- **[TOOLS_DESIGN.md](./.ai/design/TOOLS_DESIGN.md)**: Establishes the philosophy, boundaries, taxonomy classification, contracts, safety metadata model, execution lifecycle, and registration framework for Tools inside the DeepCore Intelligence Layer.




## Context Engine — Definition of Done

Status: Complete ✅

Responsibilities:
- Build deterministic ContextPackages.
- Consume RegistryService only.
- Produce immutable context snapshots.
- Remain model agnostic.
- Preserve evidence and source metadata.
- Expose context through Assistant API.

Explicitly does NOT:
- Reason
- Plan
- Execute tools
- Compose prompts
- Call LLMs
- Maintain conversation state

Verified by:
- Unit Tests ✅
- API Tests ✅
- Integration Tests ✅

---

## Phase 8.1 Completion — Tool Runtime

Implemented and validated the deterministic Tool Runtime as the first executable layer of the Intelligence Stack:

### Capabilities

- **Strict Specification Contracts**: Built standard, architecture-conforming Pydantic models for `ToolStatus`, `ToolArtifact`, `ToolDiagnostics`, `ToolRequest`, `ToolResult`, `SafetyDeclaration`, and `ToolDescriptor`.
- **Execution Registry Integration**: Decoupled tool resolution by introducing `ExecutionRegistry` as a lightweight resolution abstraction on top of `ToolRegistry` to route executable handlers.
- **Robust ToolRuntime Engine**: Implemented `ToolRuntime` representing the execution core, supporting inputs schema validation, thread-based execution timeouts, diagnostics collection, exception mapping, and hooks.
- **Execution Lifecycle Hooks**: Reserved empty `before_execute()` and `after_execute()` hooks in `ToolRuntime` for future tracing, logging, metrics, permissions, and caching.
- **Deterministic Mock Verification**: Implemented standard mocks (`EchoTool`, `DelayTool`, `CalculatorTool`) and database-aware `RegistrySearchMockTool` validating platform interaction.

### Validation

- Clean execution passing all 8 tests in [test_tool_runtime.py](./tests/test_tool_runtime.py) verifying registration, lookup, validation, timeout enforcement, exception handling, and database integration.
- Standardized whole test suite integration with 82/82 tests passing.

---

## Phase 8.2 Completion — Skill Runtime

Implemented and validated the deterministic Skill Runtime layer coordinating Tool execution:

### Capabilities

- **Strict Specification Contracts**: Built standard, architecture-conforming Pydantic models for `SkillStatus`, `SkillCapability`, `ExecutionCharacteristics`, `SkillArtifact`, `SkillDiagnostics`, `SkillRequest`, `SkillResult`, and `SkillDescriptor`.
- **Decoupled Execution Interface**: Implemented `SkillRuntimeInterface` defining execution resolution. Skills depend on this abstract execution contract rather than the concrete `SkillRuntime`, keeping the runtime layer extensible.
- **Robust SkillRuntime Engine**: Implemented `SkillRuntime` coordinating skill execution, input schema validation, and tool runtime invocation via Dependency Injection.
- **Call Stack & Recursion Protection**: Enforced execution depth tracing and circular call checks, rejecting nested requests exceeding a max execution depth of 4 or exhibiting circular patterns prior to any downstream Tool execution.
- **Compound Orchestration Mocks**: Implemented platform-centric composition mock `RegistrySearchEchoSkill` orchestrating `RegistrySearchMockTool` search queries, loop execution of `EchoTool` calls, and result payload formatting.

### Validation

- Clean execution passing all 5 tests in [test_skill_runtime.py](./tests/test_skill_runtime.py) verifying registration, validation, nested tool invocation, call stack tracing, circular dependency detection, and max depth rejection.
- Unified project-wide validation with 87/87 tests passing cleanly.

---

## Phase 8.3 Completion — Execution Runtime

Implemented and validated the deterministic Execution Runtime acting as the universal gateway for DeepCore:

### Capabilities

- **Universal Execution Contracts**: Built standard, architecture-conforming Pydantic models for `ExecutionStatus`, `ExecutionArtifact`, `ExecutionDiagnostics`, `ExecutionRequest`, `ExecutionResult`, and `ExecutionDescriptor`.
- **Decoupled Executable Contract**: Designed a lightweight duck-typed contract for executables. Any class/target that exposes `get_descriptor()` and `execute(request)` is treated as an executable target, eliminating strict class inheritance hierarchies.
- **Universal Execution Registry**: Implemented `ExecutionRegistry` responsible for registering and resolving executable targets (Skills, Workflows, Macros, Composite Tools, and future Agents).
- **Execution Gateway Engine**: Implemented `ExecutionRuntime` acting as the single orchestration gateway for the Planner, receiving `SkillRuntime` via constructor injection, routing Skill executables to the `SkillRuntime` module, and running direct custom `Executable` targets.

### Validation

- Clean execution passing all 5 tests in [test_execution_runtime.py](./tests/test_execution_runtime.py) verifying registry lookup, direct custom `Executable` routing, `SkillRuntime` routing, data schema mapping, and diagnostics.
- Full integration verification with 87/87 tests passing.

---

## Phase 9 Completion — Planner Runtime

Implemented and validated the deterministic Planner Runtime coordinating and executing complex Execution Plans:

### Capabilities

- **Planner Contracts**: Built standard, architecture-conforming Pydantic models for `StepStatus`, `PlanStatus`, `RetryPolicy`, `StepCondition`, `TimelineEvent`, `ExecutionStep`, `ExecutionPlan`, `PlannerStatus`, `PlannerRequest`, `PlannerDiagnostics`, `PlannerResult`, and `VariableReference`.
- **Topological Sort Scheduling**: Created `PlannerScheduler` validating step dependencies and computing a deterministic execution order using Kahn's algorithm, raising `PlannerDependencyError` for circular dependencies.
- **Custom Deterministic Expression Evaluator**: Designed a safe, non-python `eval` condition evaluator supporting:
  - `<step_path>.completed` / `<step_path>.failed` (e.g. `steps.search.completed`)
  - `<step_path> <operator> <value>` (e.g. `steps.search.outputs.count > 0` with operators `==`, `!=`, `>`, `<`, `>=`, `<=`)
  - `exists(<step_path>)` (e.g. `exists(steps.search.outputs.results)`)
- **Variable Reference Normalization**: Automatically extracts public template references (e.g. `{{steps.search.outputs.count}}`) into internal structured `VariableReference` objects, resolving and binding them to the inputs right before step execution.
- **Step Retry and Cancellation**: Supports execution retry policies (with configurable max attempts, backoff, and exponential scaling) and handles asynchronous plan cancellation signals cleanly.
- **Audit Trails**: Records fine-grained `TimelineEvent` objects for execution lifecycle boundaries (queued, started, completed, failed, cancelled).

### Validation

- Clean execution passing all 10 tests in [test_planner_runtime.py](./tests/test_planner_runtime.py) validating variable normalization, condition evaluation, scheduling order, retry enforcement, plan failure handling, and cancellation routing.
- Complete integration verification with 97/97 tests passing cleanly.

---

## Phase 9.5 Completion — Kernel Integration Validation

Validated the complete deterministic execution kernel through end-to-end integration scenarios and developer diagnostics:

### Capabilities

- **Developer Diagnostics (Kernel Health Report)**: Implemented `KernelHealthReport` dynamically querying registries and runtimes to compile registered tools, skills, executables, capabilities, and statuses into a markdown report.
- **Dynamic Registry Schema Resolution**: Enhanced `ExecutionRegistry` normalized listing logic to cleanly parse model class schemas into serialized JSON schemas.
- **End-to-End Test Verification (Scenarios A - D)**: Created `test_kernel_integration.py` containing end-to-end verification tests:
  - **Scenario A**: End-to-end DB query-echo flow from Planner through Execution Runtime, `RegistrySearchEchoSkill`, and `RegistrySearchMockTool` back to output result formatting.
  - **Scenario B**: Execution retry policy backoff delays and final recovery status.
  - **Scenario C**: Multi-step conditional branch routing and skipping behavior.
  - **Scenario D**: Clean shutdown and intermediate cancellation signal propagation.
- **Kernel Determinism Verification (Scenario E)**: Iterates execution of identical multi-step plans 50 times in a loop, asserting that all outcomes, outputs, timelines, and event sequences (with the exception of execution times) are 100% identical and free of hidden side-effects.

### Validation

- Clean execution passing all 6 tests in [test_kernel_integration.py](./tests/test_kernel_integration.py).
- Entire project-wide test suite successfully verified with 103/103 tests passing cleanly.

---

## Phase 10 Completion — Conversation Runtime

Implemented and validated the deterministic Conversation Runtime acting as the main entry point to the DeepCore Intelligence Stack:

### Capabilities

- **Conversation Contracts**: Built standard, client-neutral Pydantic models for `ConversationMode`, `ConversationStatus`, `ConversationMessage`, `ConversationRequest`, `ConversationResponse`, `ConversationDiagnostics`, and `ConversationDescriptor`.
- **Reserved Compatibility Fields**: Extended requests with a `history` list (for future prompt composers) and responses with an `artifacts` list (for returning files, reports, and graphics).
- **Context Orchestration**: Integrated `ContextEngine` to compile relevant context packages dynamically when a trigger object or planning mode is requested.
- **Orchestration Routing & Delegation**: Implemented a routing boundary where `DIRECT` mode queries bypass the planner entirely, whereas `PLANNING` mode queries delegate plan compilation entirely to the `PlannerRuntime.build_plan_for_goal` API.
- **FastAPI Endpoints**: Exposed endpoints `POST /api/conversation` and `GET /api/conversation/capabilities` in the API gateway.
- **Health Report Registry**: Included `ConversationRuntime` in the developer diagnostics health summary.

### Validation

- Clean execution passing all 7 tests in [test_conversation_runtime.py](./tests/test_conversation_runtime.py) validating request schemas, descriptor generation, direct mode bypass, database-bound planning mode, context matching, and API endpoints.
- Entire project-wide test suite successfully verified with 110/110 tests passing cleanly.

---

## Phase 11 Completion — Descriptor Standardization Framework

Implemented and validated a unified, immutable, and typed descriptor framework across all executable capabilities (Tools, Skills, Providers, Conversations, Prompts, Models):

### Capabilities

- **Unified BaseDescriptor**: Implemented a shared metadata model `BaseDescriptor` using Pydantic-frozen configuration (`frozen=True`) to enforce metadata immutability at runtime. Gathers standard fields: `id`, `name`, `description`, `category` (using `DescriptorCategory` enum), versions, tags, and custom metadata.
- **DescriptorProvider Protocol**: Introduced structural Protocol `DescriptorProvider` verifying that capability components implement `get_descriptor() -> BaseDescriptor`.
- **DescriptorCategory Enum**: Implemented a strongly typed category enum replacing free-form strings (`TOOL`, `SKILL`, `PROVIDER`, `CONVERSATION`, `PROMPT`, `MODEL`).
- **Standardized Domain Descriptors**:
  - **ToolDescriptor**: Inherits from `BaseDescriptor`, mapping tool capability details and safety declarations.
  - **SkillDescriptor**: Inherits from `BaseDescriptor`, mapping skill capabilities and execution characteristics.
  - **ConversationDescriptor**: Inherits from `BaseDescriptor`, mapping modes, context, planning, and model options.
  - **ProviderDescriptor**: New, standard metadata schema for sync/ingestion providers.
  - **PromptDescriptor**: New, standard metadata schema describing prompt template identifier, strategy, and variables without leaking template content.
  - **ModelDescriptor**: New, standard metadata schema for LLM/embedding models describing publisher, type, and context length limits.

### Validation

- Clean execution passing all 7 tests in [test_descriptors.py](./tests/test_descriptors.py) verifying inheritance, protocol compliance, serialization, stable IDs, prompt metadata, and immutability.
- Entire project-wide test suite successfully verified with 117/117 tests passing cleanly.

---

## Phase 12 Completion — Capability Registry Architecture

Implemented and validated a unified, metadata-only Capability Registry that indexes, validates, and exposes capability descriptors:

### Capabilities

- **CapabilityRegistry Implementation**: Created a centralized metadata index class `CapabilityRegistry` keeping descriptor records cleanly separated from runtime execution components.
- **Robust Metadata Registration**: Exposes primary register API `register(descriptor)` alongside the convenient helper `register_provider(provider)`.
- **Pre-Registration Integrity Validation**: Validates descriptor integrity (ensuring unique ID, valid category, descriptor version, and implementation version are present) before inserting.
- **Deterministic Ordering Invariant**: Enforces alphabetical ordering sorted by descriptor `id` across all listing, category filtering, and search methods.
- **Search Capabilities**: Initialized query capabilities matching tags (e.g. `search(tags)`).
- **Immutability Assurances**: Relies on Pydantic-frozen descriptor models to prevent mutation of internal registry state.

### Validation

- Clean execution passing all 7 tests in [test_capability_registry.py](./tests/test_capability_registry.py) verifying successful registration, duplicate ID rejection, integrity validation rules, deterministic ordering, unregister behavior, retrieval immutability, and tag filtering.
- Entire project-wide test suite successfully verified with 124/124 tests passing cleanly.

---

## Phase 13 Completion — Capability Discovery Service

Implemented and validated the Capability Discovery Service translating metadata registry details into public, client-facing models:

### Capabilities

- **Discovery Model Isolation**: Implemented client-safe schemas (`CapabilitySummary` and `CapabilityDetail`) separating public API shapes from internal registry model definitions.
- **Generic CapabilityCatalog Grouping**: Automatically compiles categorizations dynamically (`CapabilityCategoryGroup` and `CapabilityCatalog`) grouped by registered descriptor categories, preventing any hardcoded list assumptions.
- **Stateless Composition**: Ensures that queries (such as listing, catalog compilation, or single lookup) compile on-demand without caching or modifying the underlying Capability Registry state.
- **Filtering Logic Consolidation**: Consolidates enabled, experimental, and configurable selectors using a private unified filter method.
- **Deterministic Ordering Invariant**: Preserves alphabetical sorting by capability ID across all query, list, and group capabilities.

### Validation

- Clean execution passing all 6 tests in [test_capability_discovery.py](./tests/test_capability_discovery.py) verifying summaries mapping, dynamic grouping (catalog updates), filters, ordering, and stateless calls.
- Entire project-wide test suite successfully verified with 130/130 tests passing cleanly.

---

## Phase 14 Completion — Capability Discovery HTTP API

Exposed and validated the Capability Discovery API endpoints in the FastAPI Gateway:

### Capabilities

- **Gateway Endpoint Integrations**: Integrated `GET /api/capabilities`, `GET /api/capabilities/filter`, `GET /api/capabilities/category/{category}`, and `GET /api/capabilities/{id}` routes into the FastAPI gateway routing registry.
- **Dynamic Capabilities Registry Resolution**: Injected Dependency `get_discovery_service` constructing registry bindings for active mock Tools, Skills, Conversation descriptors, sync Providers, Ollama LLM models, and default templates.
- **Standardized Client Response Mapping**: Maps all gateway endpoint responses to `CapabilitySummary`, `CapabilityDetail`, and `CapabilityCatalog` schemas, ensuring client-safe JSON response payloads.
- **Unified Error Handling**: Emits structured HTTP 404 responses for missing capability ID details and HTTP 422 responses for invalid category filter searches.
- **Registry Lifecycle (Bootstrap Note)**: Documented current request-scoped reconstruction of `CapabilityRegistry` as temporary bootstrap behavior to be replaced with application-level startup lifecycles in future milestones.

### Validation

- Clean execution passing all 4 tests in [test_capabilities_api.py](./tests/test_capabilities_api.py) verifying catalog structure, detailed view parameters, valid/invalid category filters, enabled/configurable selectors, and alphabetical sort checks.
- Entire project-wide test suite successfully verified with 156/156 tests passing cleanly.

---

## Capability 03 Completion — Deterministic Relationship Engine

Implemented and validated the deterministic Relationship Processing Stage (Stage 2) in DeepCore's Ingestion Pipeline:

### Capabilities

- **Relationship Model**: Parameterized the canonical database relationship model with unique UUID and updated_at timestamps.
- **Extensible Relationship Rules**: Implemented extensible rule-based relationship extractors for:
  - `REFERENCES` & `REFERENCED_BY`: Wikilinks (`[[Note]]`) and standard markdown links (`[link](path)`).
  - `SAME_FOLDER`: Matching parent directory paths.
  - `SAME_SOURCE`: Matching source systems/providers.
  - `SAME_PROJECT`: Matching shared project tags or hashtags.
  - `CHILD_OF` & `PARENT_OF`: Parent hierarchy resolved via frontmatter `parent`.
  - `DUPLICATE`: Shared content hashes.
  - `VERSION_OF`: Target original versions via frontmatter `version_of`.
- **Symmetrical Complements**: Automatically commits inverse complementary relationships (e.g. A REFERENCES B also creates B REFERENCED_BY A) to optimize graph lookups.
- **Provenance & Structured Evidence**: Records the creator/producing stage in the `relationship_source` column and structures evidence with type, detail, location, and producing stage.
- **Incremental Processing**: Deletes prior relationships created by the engine for updated objects, recalculates only for the sync targets, and purges relations for missing/archived files.
- **UI Details Inspection Table**: Renders related objects, types, confidence percentages, and structured evidence explanations inside a premium frontend table in `MemoryDetail.tsx`.

### Validation

- Clean execution passing all tests in `tests/test_relationship_engine.py` covering WikiLinks, folder matching, tag sharing, parent hierarchies, duplicates, incremental edits, and duplicate prevention.
- Project-wide test suite successfully verified with 159/159 tests passing cleanly.

---

## Phase 15 Completion — Experience Architecture Specification

Defined the foundational Product Experience Architecture governing all future user-facing, conversational, and interface decisions:

### Capabilities

- **Experiential Product Foundation**: Formulated the specification document [experience_architecture.md](./docs/00_Foundation/experience_architecture.md) at the product root foundation layer.
- **Human Cognitive Modeling**: Modeled the "Associative Web" to replace rigid physical folder systems, aligning with human memory and temporal patterns.
- **Cognitive Commitments**: Established 5 core immutable platform constraints protecting user attention, explainability, provenance, location independence, and context preservation.
- **Experience Invariants**: Outlined the five foundational UX principles: Calm over Density, Explain before Expose, Purpose before Implementation, Progressive Disclosure, and Context over Navigation.
- **Conceptual Primitives Definition**: Documented core system primitives (Artifacts, Themes, Connections, Observations) separate from implementation names or menu UI labels.
- **Contextual Onboarding & Self-Teaching**: Outlined evidence-based transparency flows where the system explains its own relationships and observations dynamically to the user.

### Validation

- Verified specification document creation and alignment with high-level product goals.

---

## Phase 16 Completion — Information Architecture Specification

Defined the foundational Product Information Architecture governing how attention, information, and understanding are structured and prioritized across the application:

### Capabilities

- **Information Architecture Specification**: Formulated the specification document [information_architecture.md](./docs/00_Foundation/information_architecture.md) at the product root foundation layer.
- **Attention Layering Model**: Developed a five-stage concentric attention model (Immediate Focus ➔ Current Focus ➔ Supporting Context ➔ Background Awareness ➔ Dormant Knowledge) to control visual and mental bandwidth.
- **Deterministic Information Priority Rules**: Established clear, system-wide rules for resolving attention conflicts between user intent, focus context, emergent connections, background signals, and system metadata.
- **Experience Spaces Mapping**: Conceptualized DeepCore into four core cognitive spaces (Awareness, Knowledge, Understanding, Administration) mapping current views (Home, Library, Themes, Platform) onto them to separate cognitive workspaces from administrative systems.
- **Cognitive Information Hierarchy**: Structured information into logical human-centric cognitive layers (Attention, Understanding, Evidence, Metadata, Implementation).
- **Context Lifetimes Engine**: Formulated distinct rules for Active context (from trusted attention signals), Transient context (search, session-only), Persistent context (user-pinned projects, overrides), and Dormant context (older unreferenced material).
- **Purpose-driven Navigation**: Defined navigation entirely around four user purposes: Navigating to what they are doing, what they know, what they are exploring, and how the platform works.

### Validation

- Verified specification document creation and alignment with the experience invariants.

---

## Milestone Complete — Knowledge Acquisition Platform Architecture

The Knowledge Acquisition Platform Architecture is completed, approved, and frozen. It establishes the foundational, pluggable boundary layer for external sources.

### Status Details
- **Architecture Approved**: Frozen specification document created at [KNOWLEDGE_ACQUISITION_ARCHITECTURE.md](./docs/10_Architecture/KNOWLEDGE_ACQUISITION_ARCHITECTURE.md).
- **Connector Platform Boundary Established**: Strict separation between pluggable connectors/translators and internal kernel components (Acquisition Runtime, Ingestion Service).
- **Knowledge Source Model Finalized**: Decoupled Connector (installable package code) from Knowledge Source (configured workspace instance, e.g. personal vs. work folders).
- **Connector Taxonomy Finalized**: Connectors classified into Source, Index, Intelligence, and Export connectors.
- **Translation Invariants Finalized**: Translators mandated as pure, deterministic transformation functions without DB, network, AI, or state modification access.
- **Acquisition Runtime Established**: Runtime orchestration manages sync loops, retry boundaries, cursor states, and emits events for platform observability.
- **Reference Connector Strategy Adopted**: Enforced reference connector policy (Filesystem for Source, Apple Spotlight for Index, OCR for Intelligence, Markdown Export for Export).

### Validation
- Validated core engine logic using in-memory mock connectors in [test_acquisition_platform.py](./tests/test_acquisition_platform.py) ensuring 100% test coverage for framework code.

---

## Milestone Complete — Connector Library Architecture

The Connector Library Architecture is completed, approved, and frozen. It establishes the administrative, packaging, and permission governance models for DeepCore plugins.

### Status Details
- **Architecture Approved**: Frozen specification document created at [CONNECTOR_LIBRARY_ARCHITECTURE.md](./docs/10_Architecture/CONNECTOR_LIBRARY_ARCHITECTURE.md).
- **Connector Packaging Model Finalized**: Defined hierarchy from Connector Package, ProviderDescriptor, Connector implementation, Translator function, down to DB-configured Knowledge Source.
- **Config Levels Separated**: Established clean separation between Connector Configuration (global package levels), Knowledge Source Configuration (specific instance levels), and Workspace Bindings (workspace-level isolation).
- **Extension Marketplace Philosophy**: Adopted the VS Code extension marketplace design for managing third-party extensions.
- **Permissions Architecture Finalized**: Formulated capability-based user-managed permissions mapping directly into ProviderDescriptors.
- **Reference Strategy Confirmed**: Locked Filesystem connector as the initial reference integration verifying the platform runtime, blocking other connector categories until validation succeeds.

### Validation
- Verified specification document creation and alignment with the Experience Architecture principles.

---

## Milestone Complete — Filesystem Reference Source Connector

The Filesystem Reference Source Connector is completed, approved, and frozen as the reference standard for all source connectors.

### Status Details
- **Legacy Migration Complete**: Fully migrated the legacy `MarkdownProvider` to the pluggable Connector platform.
- **Reference Connector Established**: The Filesystem Connector acts as the initial reference blueprint, yielding platform-agnostic file properties.
- **Translator Purity Validated**: `MarkdownTranslator` verified as a pure function, isolating file reads, content hashing, and registry mapping.
- **Acquisition Runtime Validated**: Runtime state machine tested against the production workflow, managing sync, progress, and cursors.
- **Knowledge Source Ownership Preserved**: Admin-level validation restricts sync execution to pre-configured database sources, raising errors on unconfigured paths.
- **Incremental Sync & Deletions Validated**: Fully handles modification scans and processes orphaned files by marking deleted files as `missing`.

### Validation
- Clean execution of all 180 automated tests (passing `test_filesystem_connector.py`, `test_cli.py`, and `test_sync_reliability.py`).

---

## Milestone Complete — Calendar Reference Source Connector

The Calendar Reference Source Connector is completed, approved, and frozen as the reference standard for Temporal Source Connectors.

### Status Details
- **Temporal Knowledge Domain Established**: Modeled standard entities (`Event`, `Time Interval`, `Participant`, `Location`, `Reminder`, `Recurrence`) in a reusable schema layer.
- **Calendar Provider Abstraction Validated**: Decoupled EventKit native access from the platform, enabling modular provider adapters (`EventKitProvider` and `MockCalendarProvider`).
- **Canonical Recurrence Model**: Mapped iCal recurrence rules to structured frequency, interval, and exception datetimes.
- **Extensible Participant Model**: Enabled support for both human attendees and non-human workspace resources.
- **Runtime-owned Registry Ingestion**: Decoupled translators from SQLite models by moving ingestion mapping inside `AcquisitionRuntime.run_sync()`.
- **Generic Knowledge Source Synchronization**: Integrated a generic CLI synchronization command operating on Knowledge Sources rather than connector-specific endpoints.

### Validation
- Clean execution of all 185 automated tests (passing `test_calendar_connector.py` alongside other test suites).

---

## Milestone Complete — Apple Spotlight Reference Index Connector

The Apple Spotlight Reference Index Connector is completed, approved, and frozen as the reference standard for Index Connectors.

### Status Details
- **Discovery Domain Established**: Implemented the canonical `DiscoveredArtifact` domain model for platform-independent resource queries.
- **Discovery Strategies Abstraction Validated**: Decoupled queries into high-level Workspace Scope, File Type, and Custom Tags filters.
- **Discovery Classification Introduced**: Isolated translation from classification via a dedicated ingestion classifier inside `AcquisitionRuntime`.
- **Index Connector Category Validated**: Established native query translation and non-macOS fallback scan mechanics.
- **Platform-independent Discovery Model**: Enabled consistent strategy execution across macOS (`mdfind`) and other platforms (glob walker).
- **190 Automated Tests Passing**: All tests validated and green.

---

## Platform Status — Knowledge Acquisition Platform (v1.0 Validation)

The first generation of the Knowledge Acquisition Platform is now fully validated through the following production-grade reference implementations:

1. **Source Connector (Filesystem)**: Standardized directory structure walking, checksum hashing, and legacy markdown migrations.
2. **Source Connector (Temporal)**: Standardized extensible workspace participant modeling and canonical recurrence parameters.
3. **Index Connector (Discovery)**: Standardized ambient filesystem resource search, file strategies, and decoupled mapping classification.

The Knowledge Acquisition Platform boundary is now considered complete and stable for future connector expansions.

---

## Milestone Complete — DeepCore Home Experience

The DeepCore Home Experience is completed and approved, establishing the cognitive center of gravity of the application.

### Status Details
- **Awareness Service & State**: Introduced `AwarenessService` in the backend composing the `AwarenessState` model as a first-class platform capability positioned between Context and Experience:
  ```
  Knowledge ➔ Relationships ➔ Signals ➔ Context ➔ Awareness ➔ Experience ➔ Assistant
  ```
- **Progressive Cognitive Flow**: Structured the Home UI to flow naturally through Recognition (context restoration), Orientation (explain changes), Understanding (observations), and Continuation (next guided steps).
- **Intent-Based Focus**: Introduced the `FocusIntent` abstraction to model the user's active focus state around intent rather than simple file recency.
- **Platform Separation**: Home no longer functions as a platform dashboard; all diagnostics, metrics, and administration are isolated in the Platform Center.
- **198 Automated Tests Passing**: Verified focus sorting, timeline runs logging, orphan notes detection, and next prompt mappings.

---

## Milestone Complete — Assistant Experience

The Assistant Experience is completed, approved, and frozen, establishing the collaborative thinking sessions and evidence-anchored citations.

### Status Details
- **Thinking Session Hierarchy**: Established the structural hierarchy `Thinking Session ➔ Conversation ➔ Messages`, modeling the Assistant as a participant in a broader cognitive session.
- **Conversation Abstraction**: Separated the interface container (conversation) from the user's cognitive session (thinking session).
- **Capability-Based Thinking Modes**: Modeled `ThinkingModeDescriptor` as a dynamic capability contributed by plugins, pre-loading 5 built-in modes: Continue Thinking, Recover Context, Explore Relationships, Challenge Assumptions, and Summarize Theme.
- **Platform-Level Evidence Model**: Extracted `Evidence` into a platform-level primitive schema reusable across all layers (Awareness, Relationships, Concepts, and Assistant).
- **Decoupled Persistence**: Structured `ConversationRepository` to isolate SQLAlchemy operations, ensuring orchestration is separated from storage dependencies.
- **Platform State Consumption**: The Assistant reasons over the composed `ConversationState` (comprising `FocusIntent`, `AwarenessState`, and `ContextPackages`) rather than constructing context in isolation.
- **Interactive Evidence Inspector**: Built a visual evidence inspector panel inside the React Assistant pane to expose provenance paths and justifications.
- **198 Automated Tests Passing**: Verified full repository CRUD, service session flows, and API endpoints.

> [!NOTE]
> **Future Refinement — Evidence Generation Pipeline**
> Evidence generation is currently orchestrated by the Assistant layer as an implementation convenience. Long-term ownership belongs to a dedicated platform Evidence Service so that Home, Relationships, Context, and Assistant all consume a common evidence pipeline.

---

## Phase Status — Constitutional Experience Architecture (FROZEN)

Incorporated final architectural refinements and froze the constitutional human-machine interface rules, spatial-temporal grammars, and experience invariants of DeepCore in [.ai/architecture/EXPERIENCE_ARCHITECTURE_V2.md](./.ai/architecture/EXPERIENCE_ARCHITECTURE_V2.md). All future layout, workspace, and interaction designs must conform to this specification. The next phase will build visual blueprints and interaction flows against this frozen architecture.

---

## Phase Status — Connector Experience Specification (COMPLETE)

Completed and froze the implementation-oriented UX specification blueprint in [docs/20_Specifications/CONNECTOR_EXPERIENCE_BLUEPRINT.md](./docs/20_Specifications/CONNECTOR_EXPERIENCE_BLUEPRINT.md). This specification maps the 8-stage Trust Lifecycle journey, detailed screen flows, transitions, and trust messaging. The next milestone transitions to Stitch prototyping and visual design.
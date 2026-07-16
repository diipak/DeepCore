---
Category: Governance
Status: Stable
Dependencies: [architecture/PRODUCT_VISION.md]
Source-of-truth: True
---

# DeepCore Development Roadmap

Milestone Development Roadmaps for the DeepCore personal intelligence engine.

---

## Completed Phases

### Phase 1: Registry
- Established database foundation (SQLite, SQLAlchemy).
- Created schemas for `RegistryObject`, `RegistryRelationship`, and `SyncRun`.
- Standardized object state tracking (`active`, `missing`, `archived`).

### Phase 2: Capture
- Implemented intake service layer.
- Added automatic metadata extraction for YouTube URLs and manual notes.

### Phase 3: Content Index
- Implemented `ContentIndex` and file watching for Markdown source files.
- Added content hash validation to avoid redundant parsing.

### Phase 4: Concepts
- Created heuristics-based concept extraction.
- Developed relationship matching based on text mentions.
- Built a governance API for approving, ignoring, and merging concepts.

### Phase 5: API Gateway
- Reorganized single routes configuration into a modular routes package.
- Exposed registry, content, and concept capabilities via FastAPI.

### Phase 5.1: Experience APIs
- Refined `/api/concepts` default sorting order to prioritize approved status.
- Added `/api/memories/recent` filtering human-created notes, videos, and documents.
- Created `/api/dashboard` returning dashboard stats, top concepts, and recent memories.

### Phase 6: DeepCore Shell v0.1
- Developed mobile-first responsive web client (React/TypeScript) consuming registry and knowledge endpoints.

### Phase 7: Context Engine
- Built context query resolution querying objects, contents, and relationships.
- Compiles deterministic context packages with content hashes for LLM reasoning windows.

### Phase 8.1 - 8.3: Tool, Skill, & Execution Runtimes
- **Tool Runtime**: Validation, isolated execution, resources tracking, and timeout hooks.
- **Skill Runtime**: Recursive composite tool chains with recursive check limits.
- **Execution Runtime**: Duck-typed execution gateway resolving executables by descriptor.

### Phase 9: Planner Runtime
- Kahn's algorithm scheduler processing plans into execution order.
- Replaced Python expressions with a secure, custom condition expression evaluator.
- Normalizes and binds dynamic variable references before step execution.

### Phase 9.5: Kernel Integration & Diagnostics
- Compiled full kernel e2ee pipeline testing (Retry recovery, skipped branches, cancellations).
- Verified 100% determinism running identical plans 50 times in a loop with zero variance.
- Implemented `KernelHealthReport` compiling runtimes, tools, skills, and executables status.

### Phase 10: Conversation Runtime
- Established client-neutral conversation schemas (`history` and `artifacts` reserved fields).
- Implemented Conversation gateway coordinator, direct command routing, and planner delegation.
- Integrated `/api/conversation` and `/api/conversation/capabilities` API routes.

### Phase 11: Descriptor Standardization Framework
- Standardized metadata contract inheritance from frozen `BaseDescriptor`.
- Implemented `DescriptorProvider` protocol ensuring self-describing components.
- Introduced `ProviderDescriptor`, `PromptDescriptor` (variables metadata), and `ModelDescriptor`.

### Phase 12: Capability Registry Architecture
- Developed a metadata-only `CapabilityRegistry` storing capability descriptors.
- Enforced ID uniqueness, category checks, and pre-registration integrity validations.
- Guarantees alphabetical ID sorting for all lookups.

### Phase 13: Capability Discovery Service
- Created stateless composition layer mapping internal descriptors to `CapabilitySummary` and `CapabilityDetail`.
- Compiles `CapabilityCatalog` dynamically grouped by category.

### Phase 14: Capability Discovery HTTP API
- Integrated dynamic capabilities lookup and dynamic catalog grouping endpoints (`GET /api/capabilities`).
- Standardized gateway mapping to client-safe summaries and category listings.

### Capability 03: Deterministic Relationship Engine
- Implemented relationship rules (references, folder, source, tags, duplicate, version) in ingestion pipeline.
- Added symmetrical complements, provenance tracking, and structured evidence.

### Phase 15: Experience Architecture Specification
- Created `docs/00_Foundation/experience_architecture.md` defining cognitive commitments, invariants, and conceptual workflow mappings.

### Phase 16: Information Architecture Specification
- Created `docs/00_Foundation/information_architecture.md` defining the attention layers, priority rules, experience spaces, and context lifetimes.

---

## Next Milestone: Phase 17 — UI Alignment with Experience & Information Architecture

Align the DeepCore React/TypeScript frontend workspace with the newly defined Experience and Information Architecture Specifications.

### Core Goals
- **Cognitive Space Separation**: Map the user interface into distinct spaces (Awareness, Knowledge, Understanding, Administration) and enforce strict Platform Isolation for background systems.
- **Attention Layering**: Adjust layouts to respect the 5 layers of attention, keeping focus clean and observations secondary.
- **Workspace Navigation Refactoring**: Transition sidebar elements from DB-centric terms to dynamic, purpose-driven navigation.
- **Context Preservation**: Align the frontend state to preserve active context, transient searches, and dormant states.


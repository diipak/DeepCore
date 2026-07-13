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

---

## Next Milestone: Phase 14 — Capability Discovery HTTP API

Introduce the HTTP API endpoints in the FastAPI Gateway allowing client interfaces to discover available capabilities dynamically.

### Core Goals
- **API Integration**: Create `/api/capabilities` routes.
- **Dynamic Frontend Integration**: Enable clients to query and filter available tools, skills, prompts, and models directly from the capability discovery service.

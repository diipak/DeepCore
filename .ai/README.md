# DeepCore Technical Documentation Universe

Welcome to the DeepCore design and engineering documentation repository. This directory serves as the single source of truth for the product architecture, system invariants, extension mechanisms, and implementation specifications.

---

## Directory Structure

The documentation is organized into four distinct folders based on architectural responsibility:

```
.ai/
├── README.md               # Navigation guide and role-based reading paths
├── governance/             # Development protocols, roadmaps, and project health
├── architecture/           # Core platform boundaries, pipelines, and UX philosophy
├── design/                 # Low-level component specifications and contracts
└── agents/                 # Instructions and parameters for AI coding assistants
```

### 1. Governance (`governance/`)
Governs the project lifecycle, developer rules, and roadmap alignment.
*   [DeepCore_Development_Protocol.md](./.ai/governance/DeepCore_Development_Protocol.md) `[Stable]`: Mandatory rules for pair programming, commit strategies, and codebase maintenance.
*   [ROADMAP.md](./.ai/governance/ROADMAP.md) `[Stable]`: The planned sequence of phases from the core kernel to UI and intelligence.
*   [CURRENT_STATE.md](./.ai/governance/CURRENT_STATE.md) `[Experimental]`: Running index of completed, active, and pending project items.

### 2. Architecture (`architecture/`)
Establishes the high-level boundaries, structural layers, pipelines, and product visions of DeepCore.
*   [PRODUCT_VISION.md](./.ai/architecture/PRODUCT_VISION.md) `[Stable]`: The core philosophy (privacy-first, local fintech and memory universe) defining why DeepCore exists.
*   [ARCHITECTURE.md](./.ai/architecture/ARCHITECTURE.md) `[Stable]`: The system-wide layering, port maps, and structural registries of the platform.
*   [INTELLIGENCE_PIPELINE.md](./.ai/architecture/INTELLIGENCE_PIPELINE.md) `[Stable]`: Explains data flow from raw content into objects, relationships, signals, and evidence.
*   [PLATFORM_ARCHITECTURE.md](./.ai/architecture/PLATFORM_ARCHITECTURE.md) `[Stable]`: Governs extensibility, capability-based sandboxing, and module registration.
*   [INTELLIGENCE_WORKSPACE_VISION.md](./.ai/architecture/INTELLIGENCE_WORKSPACE_VISION.md) `[Stable]`: Product rules guiding how personal context is presented to the user.
*   [EXPERIENCE_DESIGN.md](./.ai/architecture/EXPERIENCE_DESIGN.md) `[Stable]`: Visual guidelines, token-based color models, and Calm Intelligence patterns.
*   [UI_ARCHITECTURE.md](./.ai/architecture/UI_ARCHITECTURE.md) `[Stable]`: Interactive shell structure, responsive desktop/mobile navigation, and state sync.

### 3. Design (`design/`)
Low-level component design specifications detailing models, schemas, execution trees, and API endpoints.
*   [DESCRIPTOR_DESIGN.md](./.ai/design/DESCRIPTOR_DESIGN.md) `[Stable]`: Immutable schema templates representing capabilities.
*   [CAPABILITY_REGISTRY_DESIGN.md](./.ai/design/CAPABILITY_REGISTRY_DESIGN.md) `[Stable]`: Storage and indexing of capability descriptors.
*   [CAPABILITY_DISCOVERY_DESIGN.md](./.ai/design/CAPABILITY_DISCOVERY_DESIGN.md) `[Stable]`: stateless querying and translation of descriptors to client models.
*   [PLANNER_DESIGN.md](./.ai/design/PLANNER_DESIGN.md) `[Stable]`: Topologically-sorted DAG schedules and the execution state machine.
*   [SKILLS_DESIGN.md](./.ai/design/SKILLS_DESIGN.md) `[Stable]`: Orchestration of composite workflows.
*   [TOOLS_DESIGN.md](./.ai/design/TOOLS_DESIGN.md) `[Stable]`: Specification for isolated, single-step operations.
*   [PHASE_5_API_GATEWAY.md](./.ai/design/PHASE_5_API_GATEWAY.md) `[Stable]`: Endpoint schemas and CORS configurations.
*   [CONTEXT.md](./.ai/design/CONTEXT.md) `[Stable]`: Relational database schemas for objects and metadata.
*   [APP_SCREENS.md](./.ai/design/APP_SCREENS.md) `[Stable]`: Presentation logic and API endpoints backing user screens.

### 4. Agents (`agents/`)
*   [project_steward.md](./.ai/agents/project_steward.md) `[Stable]`: The instructions and compliance goals for AI coding assistants working in the repository.

---

## Role-Based Navigation & Reading Paths

To help you get oriented quickly, follow the path tailored to your specific engineering role:

### Path A: New Contributor (Orientation)
Get aligned with the overall project philosophy, development workflow, and state before writing code.
1.  [architecture/PRODUCT_VISION.md](./.ai/architecture/PRODUCT_VISION.md): Start here to understand the core fintech and personal memory goals.
2.  [governance/DeepCore_Development_Protocol.md](./.ai/governance/DeepCore_Development_Protocol.md): Review the coding constraints, commit styling, and file rules.
3.  [architecture/ARCHITECTURE.md](./.ai/architecture/ARCHITECTURE.md): Review the physical layer structure and port maps.
4.  [governance/CURRENT_STATE.md](./.ai/governance/CURRENT_STATE.md): Inspect what is currently built and verify your dev environment.

### Path B: Backend & Engine Engineer
For engineers working on registries, schedulers, databases, and runtime environments.
1.  [architecture/ARCHITECTURE.md](./.ai/architecture/ARCHITECTURE.md): Align on execution layer boundaries.
2.  [design/CONTEXT.md](./.ai/design/CONTEXT.md): Study the local database structures.
3.  [design/DESCRIPTOR_DESIGN.md](./.ai/design/DESCRIPTOR_DESIGN.md) & [design/CAPABILITY_REGISTRY_DESIGN.md](./.ai/design/CAPABILITY_REGISTRY_DESIGN.md): Study how capabilities are defined and indexed.
4.  [design/PLANNER_DESIGN.md](./.ai/design/PLANNER_DESIGN.md) & [design/SKILLS_DESIGN.md](./.ai/design/SKILLS_DESIGN.md): Align on how the topological execution loop runs.

### Path C: UI & Frontend Engineer
For developers building components in the core shell, managing application states, and calling the gateway.
1.  [architecture/INTELLIGENCE_WORKSPACE_VISION.md](./.ai/architecture/INTELLIGENCE_WORKSPACE_VISION.md) & [architecture/EXPERIENCE_DESIGN.md](./.ai/architecture/EXPERIENCE_DESIGN.md): Internalize the visual principles and token-based color constraints.
2.  [architecture/UI_ARCHITECTURE.md](./.ai/architecture/UI_ARCHITECTURE.md): Review the Shell component tree and layout surfaces.
3.  [design/APP_SCREENS.md](./.ai/design/APP_SCREENS.md): Align screen states with backend API endpoints.
4.  [design/PHASE_5_API_GATEWAY.md](./.ai/design/PHASE_5_API_GATEWAY.md): Study response and request schemas.

### Path D: Provider & Extension Author
For third-party or team developers creating connectors, data sync engines, custom tools, or custom signal rules.
1.  [architecture/PLATFORM_ARCHITECTURE.md](./.ai/architecture/PLATFORM_ARCHITECTURE.md): Essential reading to understand capability contracts, versioning boundaries, and sandboxing.
2.  [architecture/INTELLIGENCE_PIPELINE.md](./.ai/architecture/INTELLIGENCE_PIPELINE.md): Understand the propagation sequence from canonical object to thematic discovery.
3.  [design/DESCRIPTOR_DESIGN.md](./.ai/design/DESCRIPTOR_DESIGN.md): Align on writing the yaml manifests defining your tools or providers.
4.  [design/TOOLS_DESIGN.md](./.ai/design/TOOLS_DESIGN.md): Check contracts and bounds for isolated execution.
5.  [design/CONTEXT.md](./.ai/design/CONTEXT.md): Align with standard ObjectType values and registry schemas.

# DeepCore Technical Documentation Universe

Welcome to the DeepCore intelligence ecosystem design repository. This directory contains the complete technical specifications, governance files, architectural constraints, and behavior definitions that guide the development of DeepCore.

---

## Directory Hierarchy

The documentation is organized into four logical areas of responsibility:

```
.ai/
├── README.md               # Directory guide and reading order
├── governance/             # Product vision, protocols, roadmap, and state
├── architecture/           # Core platform, pipeline, and UI/UX architecture
├── specifications/         # Low-level component designs and contracts
└── agents/                 # Custom instructions and behavioral parameters for agents
```

### 1. Governance (`governance/`)
Files in this category define the product boundaries, developer compliance policies, system goals, and active development state.
*   [PRODUCT_VISION.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/governance/PRODUCT_VISION.md): The core philosophy of DeepCore (private personal intelligence workspace).
*   [ROADMAP.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/governance/ROADMAP.md): Evolutionary phases of the system.
*   [DeepCore_Development_Protocol.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/governance/DeepCore_Development_Protocol.md): Mandatory rules and patterns for pair programming and agent-driven edits.
*   [CURRENT_STATE.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/governance/CURRENT_STATE.md): Running status of active modules and libraries.
*   [INTELLIGENCE_WORKSPACE_VISION.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/governance/INTELLIGENCE_WORKSPACE_VISION.md): High-level experience layout reasoning for personal memories.

### 2. Architecture (`architecture/`)
Files here define high-level system layers, boundaries, pipelines, and extensibility contracts.
*   [ARCHITECTURE.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/architecture/ARCHITECTURE.md): System layering diagram, port allocation, and structural registries.
*   [INTELLIGENCE_PIPELINE.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/architecture/INTELLIGENCE_PIPELINE.md): Data flow transforming raw information into actionable context.
*   [PLATFORM_ARCHITECTURE.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/architecture/PLATFORM_ARCHITECTURE.md): Security sandboxes, module specifications, and capability contracts.
*   [UI_ARCHITECTURE.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/architecture/UI_ARCHITECTURE.md): Shell layouts, screen state synchronization, and component hierarchy.
*   [EXPERIENCE_DESIGN.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/architecture/EXPERIENCE_DESIGN.md): The core visual and semantic system rules.

### 3. Specifications (`specifications/`)
Component specifications detailing exact database models, execution transitions, and API endpoints.
*   [DESCRIPTOR_DESIGN.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/specifications/DESCRIPTOR_DESIGN.md): Schema blueprints representing system capabilities.
*   [CAPABILITY_REGISTRY_DESIGN.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/specifications/CAPABILITY_REGISTRY_DESIGN.md): Internal indexing mechanics for descriptors.
*   [CAPABILITY_DISCOVERY_DESIGN.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/specifications/CAPABILITY_DISCOVERY_DESIGN.md): How runtimes query and fetch registered capabilities.
*   [PLANNER_DESIGN.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/specifications/PLANNER_DESIGN.md): Topological DAG schedules and deterministic orchestration.
*   [SKILLS_DESIGN.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/specifications/SKILLS_DESIGN.md): Composite execution workflows.
*   [TOOLS_DESIGN.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/specifications/TOOLS_DESIGN.md): Isolated basic runtime operations.
*   [PHASE_5_API_GATEWAY.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/specifications/PHASE_5_API_GATEWAY.md): Routing structures and CORS handling.
*   [APP_SCREENS.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/specifications/APP_SCREENS.md): UX state mappings and client endpoints.
*   [CONTEXT.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/specifications/CONTEXT.md): Relational SQLite tables and model structures.

### 4. Agents (`agents/`)
Specialized system instructions and behaviors.
*   [project_steward.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/agents/project_steward.md): Guidelines and roles for agents managing the development lifecycle.

---

## Recommended Reading Order

For a new engineer or agent joining the DeepCore project, it is recommended to read the specifications in the following logical sequence:

1.  **Product Vision & Philosophy**
    *   Read [governance/PRODUCT_VISION.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/governance/PRODUCT_VISION.md) to understand *why* DeepCore exists and its core identity as a private intelligence layer.
    *   Read [governance/DeepCore_Development_Protocol.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/governance/DeepCore_Development_Protocol.md) to align on coding standards and invariants.
2.  **Core Technical Architecture**
    *   Read [architecture/ARCHITECTURE.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/architecture/ARCHITECTURE.md) to view the system layer diagrams and reserved port mapping.
3.  **Data & Intelligence Flow**
    *   Read [architecture/INTELLIGENCE_PIPELINE.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/architecture/INTELLIGENCE_PIPELINE.md) to study how data moves from Information to Canonical Objects, Relationships, Signals, and Evidence.
4.  **Extensibility & Security**
    *   Read [architecture/PLATFORM_ARCHITECTURE.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/architecture/PLATFORM_ARCHITECTURE.md) to understand capability-based permissions, the Module lifecycle, and compatibility contracts.
5.  **User Experience Integration**
    *   Read [architecture/EXPERIENCE_DESIGN.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/architecture/EXPERIENCE_DESIGN.md) followed by [specifications/APP_SCREENS.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/specifications/APP_SCREENS.md) to see how technical APIs drive the User Experience.
6.  **Low-Level Component Specifications**
    *   Study individual design docs like [specifications/PLANNER_DESIGN.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/specifications/PLANNER_DESIGN.md) and [specifications/DESCRIPTOR_DESIGN.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/specifications/DESCRIPTOR_DESIGN.md) before writing implementation code for those sub-modules.

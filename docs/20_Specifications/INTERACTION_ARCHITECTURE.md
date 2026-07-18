# Interaction Architecture Specification
## DeepCore Human Interface Specification

This specification defines the runtime interaction semantics, cognitive state progression, and ownership boundaries governing the DeepCore user experience. It bridges the platform's deterministic intelligence kernel with the Experience Layer. 

It defines behavior, state transitions, and information flow. It does not define visual components, CSS, layouts, or platform-specific design primitives.

---

## 1. Interaction Invariants

All user interactions and workspace behaviors must conform to the following non-negotiable invariants:

*   **No Action Without Provenance**: Every user action (such as modifying an object, merging concepts, or querying the assistant) must write to or reference a traceable entity or transaction audit log. The user must always be able to inspect *why* and *how* an action is performed.
*   **Silence Contract Enforcement**: The interface must remain passive. It is forbidden from displaying unsolicited alerts, engagement banners, gamification badges, or high-frequency animations. Status indicators (e.g., sync progress) must remain ambient and non-blocking.
*   **Stateless Capability Discovery**: The client application must dynamically query and discover system capabilities, tools, skills, and sync providers using the API gateway (`GET /api/capabilities`). The UI must never hardcode capabilities or assume specific backend capabilities exist.
*   **Deterministic Event Propagation**: Any write action (such as ingestion, editing, or concept approval) must follow the deterministic pipeline stages. It must invalidate downstream context packages and dirty flags, ensuring the user's focus is immediately updated with consistent state.

---

## 2. Cognitive State Model (Attention Layering)

To protect the user's mental focus, the interface structures interaction according to five concentric attention layers:

```
                  ┌───────────────────────────────┐
                  │       Dormant Knowledge       │
                  │  ┌─────────────────────────┐  │
                  │  │  Background Awareness   │  │
                  │  │  ┌───────────────────┐  │  │
                  │  │  │Supporting Context │  │  │
                  │  │  │  ┌─────────────┐  │  │  │
                  │  │  │  │Current Focus│  │  │  │
                  │  │  │  │  ┌───────┐  │  │  │  │
                  │  │  │  │  │ Immed │  │  │  │  │
                  │  │  │  │  └───────┘  │  │  │  │
                  │  │  │  └─────────────┘  │  │  │
                  │  │  └───────────────────┘  │  │
                  │  └─────────────────────────┘  │
                  └───────────────────────────────┘
```

1.  **Immediate Focus (Active Input)**:
    *   *Interaction Boundary*: The active text input field, cursor focus, or direct conversation query.
    *   *Constraint*: Typing, reading, or text selection must block peripheral updates. Background sync updates or concept extraction alerts must never steal cursor focus or trigger visual reflows during active input.
2.  **Current Focus (Workspace Anchor)**:
    *   *Interaction Boundary*: The active Focus Node (selected note, video, or concept).
    *   *Constraint*: Displays the primary content body on the center canvas. Tapping or double-clicking the title centers this object.
3.  **Supporting Context (Proximity Field)**:
    *   *Interaction Boundary*: Directly connected nodes (WikiLinks, concepts, related files).
    *   *Constraint*: Displayed as surrounding margins, badges, or overlays. Hovering over a reference discloses relationship types (e.g., `SAME_FOLDER`, `REFERENCES`) and confidence percentages without navigating away.
4.  **Background Awareness (Peripheral Signals)**:
    *   *Interaction Boundary*: Passive status badges, sync notifications, or cognitive observations.
    *   *Constraint*: Rendered on the outer borders of the workspace. Must not flash, slide, or interrupt active workflows unless explicitly clicked.
5.  **Dormant Knowledge (The Vault)**:
    *   *Interaction Boundary*: The non-indexed, unretrieved registry.
    *   *Constraint*: Remains silent. Accessible only via explicit user action: typing in the inline search palette or expanding a transitive graph connection path.

---

## 3. Interaction Primitives

The following primitives are the core elements of user action in the workspace:

*   **Focus Node**: The single selected Registry Object that currently defines the center of gravity for the canvas.
*   **Proximity Hub**: The dynamically updated set of Registry Objects and Concepts linked directly to the Focus Node via database relationships.
*   **Workspace Actions Bar**: A contextual overlay that appears when multiple Registry Objects are selected, exposing actions: `Compare`, `Synthesize`, `Absorb`, `Reference`, `Forget`.
*   **Context Package**: The immutable context snapshot compiled by the `ContextEngine` that binds active Focus Intents, recent observations, and conversational history.
*   **Thinking Session**: An interactive workspace state tracking a user's current goal, linking one or more Conversations with active Context Packages.
*   **Evidence Inspector**: An interactive overlay displaying the exact relationship path, traversal distance, and confidence explanation for any connection or assistant citation.

---

## 4. State Transitions

The human journey through a thinking session transitions through a 10-phase state machine. The table below defines the triggers, inputs, and behaviors for each state change:

| Source Phase | Target Phase | Trigger | Inputs | System Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Arrival** | **Recognition** | Client App Mounts | Saved session token, local DB query | Fetches and restores the last active `FocusIntent` and workspace coordinates. |
| **Recognition** | **Orientation** | Mounting Completes | `SyncRuns` delta, recent memory list | Renders the passive activity timeline and observation checklist showing what changed in the background. |
| **Orientation** | **Exploration** | User focuses Search or navigates sidebar | User query string or navigation click | Sets the transient context state, searching memories and concepts concurrently. |
| **Exploration** | **Investigation** | User clicks an object card or graph node | selected `object_uuid` | Updates the Focus Node. Re-centers the workspace, updating Column 2 and pulling related metadata into Column 3. |
| **Investigation** | **Comparison** | User selects multiple cards and clicks "Compare" | Array of `object_uuid`s | Pulls objects into a side-by-side matrix, displaying intersecting concepts and metadata divergences. |
| **Comparison** | **Reflection** | User clicks "Ask Assistant" on comparison | Selected objects, active focus | Pre-populates the Assistant's message prompt with the comparison context package. |
| **Reflection** | **Continuation** | Assistant returns response with evidence | `EvidenceItem` annotations | Highlights cited concepts in the text and exposes citation anchors. Displays suggested connection follow-ups. |
| **Continuation** | **Completion** | User executes a modification or governance action | Merge target, status updates | Commits the new state (`approved`, `ignored`, `merged`) to the Registry database, invalidating cache hashes. |
| **Completion** | **Departure** | User closes the application or switches workspace | Active workspace state | Saves active session coordinates, open panes, and conversation histories to the local repository. |

---

## 5. Navigation Semantics

DeepCore rejects traditional page-based hierarchical navigation. Instead, it relies on focus shifts across the three-column layout:

```
┌─────────────────┬─────────────────────────────────┬─────────────────┐
│                 │                                 │                 │
│    COLUMN 1     │            COLUMN 2             │    COLUMN 3     │
│                 │                                 │                 │
│  Memory Universe│       Conscious Workspace       │Context Intel    │
│  (Navigation)   │         (Canvas Focus)          │  (Assistant)    │
│   (240px max)   │           (Flex-1)              │  (280px-600px)  │
│                 │                                 │                 │
└─────────────────┴─────────────────────────────────┴─────────────────┘
```

### Column 1: Memory Universe (Persistent Scope)
*   **Purpose**: Stable anchor for discovery, spaces, and platform settings.
*   **Behavior**: Contains a collapsible tree listing knowledge categories, sources, and active plugins. Selecting an item updates the canvas view state in Column 2.

### Column 2: Conscious Workspace (Flexible Canvas)
*   **Purpose**: The primary reasoning workspace.
*   **Behavior**: Renders the active layout (Home, Document Viewer, Comparison Matrix, or Graph Explorer) based on the active Focus Node. Switching layouts preserves user selections.

### Column 3: Context Intelligence (Assistant Pane)
*   **Purpose**: Contextual assistance and evidence inspection.
*   **Behavior**: Resizable left drag-handle (280px min to 600px max, persisting width to `localStorage`). Receives the current workspace context. On mobile screens, it collapses into a slide-over view.

### The Inline Search Palette
*   **Purpose**: Non-disruptive gateway to Dormant Knowledge.
*   **Behavior**: Stays visible and active during typing. It queries memories and concepts concurrently. Selecting a search result updates the Focus Node in Column 2 and shifts the workspace focus. Navigating away preserves the active search query.

---

## 6. Ownership Boundaries

To guarantee deterministic behavior and local privacy, ownership boundaries are enforced across all architectural layers:

```
┌────────────────────────────────────────────────────────┐
│                        USER INTERFACE                  │
│  (Manages focus states, input buffers, window sizes)   │
└───────────────────────────┬────────────────────────────┘
                            │ (API Requests)
                            ▼
┌────────────────────────────────────────────────────────┐
│                        API GATEWAY                     │
│  (Stateless endpoints, route mapping, validation)       │
└───────────────────────────┬────────────────────────────┘
                            │ (Ingress / Egress)
                            ▼
┌────────────────────────────────────────────────────────┐
│                     CORE RUNTIMES LAYER                │
│  (Planner runtime, skill/tool timeouts, context engine)│
└───────────────────────────┬────────────────────────────┘
                            │ (Persistence / Rules)
                            ▼
┌────────────────────────────────────────────────────────┐
│                     REGISTRY & ENGINE                  │
│  (DB transactions, content hashing, relationship rules)│
└────────────────────────────────────────────────────────┘
```

*   **User Interface (UI) Layer**: Owns user focus (selected states), local panel sizes, transient view states, and input buffers. Strictly forbidden from resolving relationship rules, merging data, or calling LLMs directly.
*   **API Gateway Layer**: Owns serialization, request validation, rate limiting, and route mapping. Binds stateless requests to the correct services.
*   **Core Kernel & Runtimes Layer**: Owns planning, execution scheduling, skill/tool execution timeouts, and context package assembly.
*   **Registry Layer**: Owns transaction consistency, content hashing, data migrations, relationship engine execution, and persistence.

---

## 7. Interaction Event Model

DeepCore UI emits canonical interaction events to track session state, synchronize views, and maintain audit logs:

*   **`FocusShifted`**: Emitted when a new object becomes the focal node.
    *   *Payload*: `{ object_uuid: UUID, previous_uuid: UUID, source_interaction: String }`
*   **`SelectionCaptured`**: Emitted when an object is added to the active comparison or synthesis list.
    *   *Payload*: `{ object_uuid: UUID, active_selection_count: Integer }`
*   **`ContextTriggered`**: Emitted when the Context Engine compiles a new snapshot for the Assistant.
    *   *Payload*: `{ session_uuid: UUID, trigger_object_uuid: UUID, query: String }`
*   **`SessionBoundary`**: Emitted when a Thinking Session starts or stops.
    *   *Payload*: `{ session_uuid: UUID, action: "start" | "close" }`
*   **`ObservationInteracted`**: Emitted when a user approves, ignores, or resolves a system observation.
    *   *Payload*: `{ observation_id: String, resolution: "approve" | "ignore" | "resolve" }`
*   **`SyncRequested`**: Emitted when a user initiates manual synchronization.
    *   *Payload*: `{ source_id: String, sync_mode: "full" | "incremental" }`

---

## 8. Context Lifecycle

Context packages transition through a deterministic lifecycle matching user activity:

```
[ Dormant ] ──(User Selects)──► [ Active ] ──(Pin Object)──► [ Persistent ]
    ▲                              │                              │
    │                              ▼                              │
(Timeout / Inactive)       [ Transient ] ◄──(Temporary Query)─────┘
```

*   **Dormant**: The registry objects reside in the local database. They are not loaded into memory and are ignored by the Assistant.
*   **Active**: Loaded when the user selects a Focus Node or opens a workspace. Primed in the retrieval window.
*   **Transient**: Temp session-specific queries (such as active search strings or one-turn assistant queries). Extinguishes immediately when the user changes views.
*   **Persistent**: Created when the user explicitly checks "Pin to Workspace". Survives workspace unmounts and app restarts.
*   **Active ➔ Dormant Transition**: Evaluated by the system after 30 minutes of workspace inactivity or when the focus shifts to a separate project.

---

## 9. Assistant Interaction Model

The boundary between human authority and assistant autonomy is strictly defined to prevent "black box" decisions:

### User Ownership (Absolute Authority)
*   **Goal Definition**: The user defines the active Thinking Session goal.
*   **Document Commits**: The assistant cannot write, edit, or delete notes without explicit user approval.
*   **Concept Governance**: The user remains the sole authority for final concept approval, ignore, or merge operations.
*   **Conversational Control**: The user can delete, reset, or archive conversations.

### Assistant Authority (System-level Capabilities)
*   **Prompt Formulation**: The assistant translates context packages and user queries into prompt structures.
*   **Plan Scheduling**: The assistant compiles tool execution DAGs (via the Planner Runtime) and executes them within timeout boundaries.
*   **Context Traversal**: The assistant navigates the proximity graph to assemble citations and evidence items.
*   **Evidence Formatting**: The assistant must package every assertion with verified evidence paths. It is forbidden from returning unprovenanced claims.

---

## 10. Failure & Recovery Semantics

DeepCore handles workspace interruptions, capacity limits, and pipeline failures gracefully:

*   **Provider Synchronization Failures**:
    *   *Behavior*: If a source connector sync fails, the system rolls back database transactions. The UI indicates a warning icon next to the source in Column 1. Active workspace activities continue uninterrupted. Detailed error logs are routed exclusively to the Administration Space.
*   **Context Window Overflow**:
    *   *Behavior*: When compiled context packages exceed context limits, the engine executes deterministic truncation:
        1.  Prune metadata and implementation-level details.
        2.  Prune distant transit links (relationship distance > 2).
        3.  Prune oldest unreferenced active objects.
    *   *UX Indication*: Column 3 renders a passive warning badge: "Context Truncated (Limit Exceeded)". Clicking the badge displays the count of excluded objects.
*   **Interrupted Operations**:
    *   *Behavior*: Clicking "Cancel" during a running tool/skill execution sends a cancellation signal to the Planner Runtime. The system halts the execution DAG, rolls back uncommitted registry transactions, and returns the workspace to its pre-execution state.

---

## 11. Extensibility Rules

To ensure future interaction modalities (such as voice interface widgets, ambient menu bar utilities, or AR overlays) integrate cleanly:

*   **FastAPI Gateway Access**: All future interaction clients must interface exclusively via the FastAPI Gateway. Direct database writes or filesystem accesses are prohibited.
*   **Silence Contract Adherence**: New interaction modalities must respect the Silence Contract. Unsolicited alerts, push notifications, and high-frequency animations remain prohibited.
*   **Attention Layer Mapping**: Modalities must align with the 5 Attention Layers. For example, a voice assistant widget must only read from `Active Context` and must not disclose `Dormant Knowledge` unless explicitly requested.
*   **Descriptor-Driven Interface**: Any extension or new tool module must describe itself using standard `BaseDescriptor` models. The UI client must dynamically render actions based on returned descriptors.

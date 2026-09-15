# Constitutional Experience Architecture (v2.0)
## DeepCore Human Interface Specification

This document establishes the governing constitutional rules for every user interface, transition, and interaction within DeepCore. It serves as the experiential source of truth, equivalent in authority to `PLATFORM_ARCHITECTURE.md`. All future views, plugins, connectors, and capabilities must conform to the principles and grammar defined herein.

No implementation details, styling codes, component hierarchies, or database structures may be introduced into this specification.

---

## 1. Constitutional Layer Hierarchy

The following diagram illustrates the relationship between the governing documents of the DeepCore platform:

```
                  ┌───────────────────────────────┐
                  │      PRODUCT CONSTITUTION     │
                  │  (Core Identity & Trust vows) │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                  ┌───────────────────────────────┐
                  │     PLATFORM ARCHITECTURE     │
                  │  (Kernel & Core Services Spec)│
                  └──────┬─────────────────┬──────┘
                         │                 │
            ┌────────────┘                 └────────────┐
            ▼                                           ▼
┌───────────────────────────────┐           ┌───────────────────────────────┐
│     KNOWLEDGE ACQUISITION     │           │     EXPERIENCE ARCHITECTURE    │
│    (Connectors & Translators) │           │    (Cognitive Grammars Spec)  │
└───────────────────────────────┘           └───────────────┬───────────────┘
                                                            │
                                                            ▼
                                            ┌───────────────────────────────┐
                                            │        IMPLEMENTATION         │
                                            │   (React Shell & Python APIs) │
                                            └───────────────────────────────┘
```

---

## 2. Design Philosophy

### Product Identity
DeepCore is a **quiet, local-first cognitive partner** that extends human memory and correlation. It is not an application, a database manager, or a search tool. It is a private cognitive layer running locally on the user's hardware. It operates under the premise that the user should focus on reasoning, deciding, and creating, while the system quietly handles the cognitive tax of preserving provenance, mapping relationships, and maintaining continuity.

### Calm Computing & The Silence Contract
Technology must recede into the periphery of human attention. DeepCore binds itself to an absolute **Silence Contract** documenting behaviors the platform will never perform:
-   **No Engagement Loops**: The system will never track streaks, award badges, calculate gamified levels, or use metrics to incentivize application usage.
-   **No Unsolicited Notifications**: The platform is forbidden from issuing push notifications, desktop alerts, system-tray badges, or unsolicited popups.
-   **No Decorative Animations**: Motion is used strictly to establish physical spatial presence (transitions). Decorative animations, high-frequency spinning indicators, and attention-seeking UI movements are prohibited.
-   **No Attention Competition**: The application remains entirely inactive until the user chooses to focus on it. It will never flash, bounce, or prompt for focus.
-   **No Dark Patterns**: Ingestion, synchronization, and database management are entirely transparent. Opaque configurations, forced user flows, and hidden background activities are forbidden.

---

## 3. Experience Invariants

Every view and workflow in DeepCore must respect and enforce these core invariants:
-   **Restore Orientation**: Upon entering any space, the interface must instantly orient the user, restoring their mental context and detailing what changed in the background.
-   **Preserve Provenance**: The raw source and origin of any memory, concept, or relationship must always be visible and accessible in a single interaction.
-   **Maintain Trust**: The platform must prioritize local privacy and user authority. Opaque or black-box operations are prohibited.
-   **Minimize Interruption**: The platform must never interrupt the user's attention. The user remains the sole initiator of actions.
-   **Avoid Hidden State**: System states, workspace contexts, and connector activities must be inspectable. The user should never wonder if the system is scanning, processing, or idle.
-   **Ensure Reversibility**: Destructive actions, structural merges, or configuration changes must support Undo/Reversion capabilities wherever practical.
-   **Ensure Explainability**: Every emergent connection, observation, or assistant statement must be accompanied by an explainable reason and path.

---

## 4. Object Grammar

To prevent the platform from collapsing into general-purpose CRUD layouts, **every first-class platform object**—including Registry Entities, Connectors, Conversations, Thinking Sessions, Evidence, Observations, and Workspaces—must conform to this Object Grammar.

```
┌────────────────────────────────────────────────────────┐
│                    OBJECT CONTRACT                     │
├────────────────────────────────────────────────────────┤
│  - Identity: Unique semantic representation            │
│  - Purpose: Cognitive role in the registry             │
│  - Lifecycle: Transition stages of the primitive       │
│  - Capabilities: What operations it exposes            │
│  - Evidence: Verified provenance records               │
│  - Relationships: Connections to other workspace items │
│  - Actions: Human intents allowed                      │
│  - Presentation: Visual representation constraints     │
└────────────────────────────────────────────────────────┘
```

1.  **Registry Entities (Notes, Concepts, Events, Videos)**:
    -   *Identity*: Normalized UUID and type.
    -   *Purpose*: Houses user-specific thoughts, files, or semantic nodes.
    -   *Lifecycle*: Captured ➔ Ingested ➔ Linked ➔ Active/Dormant.
    -   *Capabilities*: Text search, relationship extraction, semantic mapping.
    -   *Evidence*: Original file paths, timestamps, and indexing runs.
    -   *Relationships*: Bound to Concepts, Themes, or temporal intervals.
    -   *Actions*: Absorb, Reference, Synthesize, Explore, Forget.
    -   *Presentation*: Standardized cards, list badges, and detail context panes.

2.  **Connectors**:
    -   *Identity*: Unique provider ID and physical source location.
    -   *Purpose*: Ambiently monitors external structures (filesystem, calendar).
    -   *Lifecycle*: Discovered ➔ Configured ➔ Scanning ➔ Synchronized.
    -   *Capabilities*: Ingress walking, checksum hashing, strategy querying.
    -   *Evidence*: Configuration parameters, health status logs, and run credentials.
    -   *Relationships*: Maps discovered artifacts into Registry Entities.
    -   *Actions*: Register, Configure, Trigger Sync, Pause, Review.
    -   *Presentation*: Configuration setups and sync run reports.

3.  **Conversations**:
    -   *Identity*: Conversation UUID associated with a parent session.
    -   *Purpose*: Captures dialogue interfaces within a specific thinking track.
    -   *Lifecycle*: Active ➔ Suspended ➔ Restored ➔ Archived.
    -   *Capabilities*: Message sorting, transcript compilation.
    -   *Evidence*: Raw user inputs and assistant response logs.
    -   *Relationships*: Belongs to a Thinking Session; references Registry Entities.
    -   *Actions*: Post Message, Reset, Restore.
    -   *Presentation*: Message bubble threads and input boxes.

4.  **Thinking Sessions**:
    -   *Identity*: Unique session UUID.
    -   *Purpose*: Represents the user's ongoing cognitive effort.
    -   *Lifecycle*: Open ➔ Active ➔ Closed.
    -   *Capabilities*: Context tracking, thinking mode execution.
    -   *Evidence*: The active `FocusIntent` and awareness states.
    -   *Relationships*: Owns one or more Conversations and Context Packages.
    -   *Actions*: Start Session, Evolve Session, Conclude Session.
    -   *Presentation*: Visual header banners and active context stats.

5.  **Evidence**:
    -   *Identity*: Evidence metadata footprint.
    -   *Purpose*: Formulates the justification for platform assertions or connections.
    -   *Lifecycle*: Created ➔ Evaluated ➔ Bound.
    -   *Capabilities*: Validation parsing, confidence calculation.
    -   *Evidence*: Traversed relationship paths and reason descriptions.
    -   *Relationships*: Connects two or more Registry Entities.
    -   *Actions*: Inspect, Expose, Dismiss.
    -   *Presentation*: Explanatory panels and expandable badge tooltips.

6.  **Observations**:
    -   *Identity*: Observation ID.
    -   *Purpose*: Flags anomalies or patterns in the workspace (orphans, duplicates).
    -   *Lifecycle*: Detected ➔ Resolved/Dismissed.
    -   *Capabilities*: Conflict matching, connectivity evaluation.
    -   *Evidence*: The isolated registry entities triggering the rule.
    -   *Relationships*: References target artifacts and concepts.
    -   *Actions*: Resolve, Dismiss, Ask Assistant.
    -   *Presentation*: High-visibility alert cards and action triggers.

7.  **Workspaces**:
    -   *Identity*: Workspace UUID.
    -   *Purpose*: Encapsulates the user's isolated reasoning boundary.
    -   *Lifecycle*: Active.
    -   *Capabilities*: Entity search, batch selection, multi-artifact operations.
    -   *Evidence*: Configured sources and diagnostic metrics.
    -   *Relationships*: Encapsulates all Registry Entities and Connectors.
    -   *Actions*: Explore, Compare, Synthesize, Batch Focus.
    -   *Presentation*: The multi-column canvas.

---

## 5. Cognitive Grammar

The Cognitive Grammar defines the mental states and attention structures through which the user interacts with their knowledge web.

### The Four Cognitive Questions
Every view in DeepCore must answer one or more of the following questions for the user:
1.  **Where am I?** (Context Restoration): Restore the user's mental focus and working memory immediately upon entry.
2.  **What has changed?** (Delta Awareness): Explain what background ingestions, syncs, or signal changes occurred while the user was away.
3.  **Why is this here?** (Provenance & Association): Explain the semantic relationships, evidence paths, and confidence scores behind connections.
4.  **What should I think about next?** (Continuation): Provide clear, guided avenues to extend, synthesize, or query the active thoughts.

### Attention Hierarchy
The interface is structured to prioritize cognitive focus:
-   **Primary Focus (The Focal Point)**: Occupies the central canvas. Displays the active artifact, theme, or comparison matrix currently under investigation.
-   **Secondary Context (The Proximity Field)**: Occupies the left column. Displays structural navigation, current scopes, and associative boundaries.
-   **Ambient Support (The Reasoning Field)**: Occupies the right column. Displays active thinking modes, conversation histories, and evidence justifications.

---

## 6. Temporal Grammar

Time in DeepCore represents the relevance, active status, and history of the user's thoughts. Runtime policy determines actual temporal thresholds:

-   **Current**: The active mental context forming the user's immediate working memory.
-   **Recent**: Active projects and ongoing workflows currently in the user's cognitive horizon.
-   **Historical**: Deep memory context stored outside the active working window, retrieved via semantic associations or timelines.
-   **Dormant**: Contexts that have had no user interaction or sync signals for an extended period, suggesting they may need cleanup or re-integration.
-   **Recovered**: Past cognitive sessions restored into the active workspace, letting the user pick up where they left off.
-   **Projected**: Future events, deadlines, and schedule markers imported from temporal connectors (e.g. calendars) that represent upcoming focus requirements.

---

## 7. Spatial Grammar

The visual interface is organized into distinct functional spaces, each with its own cognitive responsibilities:

-   **Persistent Space**: The left navigation column. It provides a stable, unmoving anchor for switching scopes (Home, Workspace, Platform).
-   **Workspace Space**: The central canvas. This is the primary thinking area where the user performs exploration, side-by-side comparison, and synthesis.
-   **Assistant Space**: The right-side panel. It acts as the home for the collaborative participant in the current thinking session.
-   **Overlay Space**: Contextual, hover-based cards and tooltips. Used to display instant metadata, evidence details, and paths without forcing the user to navigate away.
-   **Modal Space**: High-focus, single-purpose sheets (such as synthesis configuration or source connections) that temporarily pause workspace interactions to prevent visual confusion.
-   **Transient Space**: Short-lived elements (e.g., capture confirmations or sync completion messages) that slide away automatically without demanding action.

---

## 8. Experience State Machine

The human journey through a DeepCore thinking session is governed by a ten-phase state machine:

```
[ Arrival ] ➔ [ Recognition ] ➔ [ Orientation ] ➔ [ Exploration ] ➔ [ Investigation ]
                                                                             │
[ Departure ] ➔ [ Completion ] ➔ [ Continuation ] ➔ [ Reflection ] ➔ [ Comparison ]
```

1.  **Arrival**: The user opens the platform. The system remains silent.
2.  **Recognition**: The interface displays the active focus cards, restoring the user's mental context.
3.  **Orientation**: The narrative timeline explains what changed (synchronized files, events) while the user was away.
4.  **Exploration**: The user navigates the concepts, searching for connections or structural insights.
5.  **Investigation**: The user selects a specific concept or note, making it the central focal node.
6.  **Comparison**: The user selects multiple items to analyze their shared concepts and property differences.
7.  **Reflection**: The user engages the Assistant inside a guided thinking session to ask questions.
8.  **Continuation**: The user identifies the next logical step in their reasoning.
9.  **Completion**: The user writes down their decision or captures a synthesized note, committing it to the registry.
10. **Departure**: The user closes the workspace. The active session state is saved to the repository.

---

## 9. Screen Grammar

Every screen in DeepCore must conform to this grammar.

### 9.1 Home Screen
-   **Purpose**: Restore mental context, orient the user on recent background changes, and guide the next thinking step.
-   **Primary Cognitive Question**: *"Where was my focus, what changed while away, and how do I continue?"*
-   **Entry Conditions**: Mounted at startup or via global Home navigation. Fetches the compiled `AwarenessState` from the backend.
-   **Exit Conditions**: Focus states saved; search or capture input states cleared.
-   **Primary Objects**: `FocusIntent` list (Where you left off), recent `SyncRuns` (What changed recently), and `CognitiveObservations` (Orphaned thoughts or unapproved concepts).
-   **Supporting Objects**: Summary statistics (total memories, concepts, and relationships).
-   **Primary Actions**: Capture thought (intake portal), search web, select focus item, and trigger guided thinking prompts.
-   **Never Show**: Complex system configuration tables, database migration states, raw sync logs, or connector statistics.
-   **Progressive Disclosure**: Show the quiet four-phase flow (Recognition, Orientation, Understanding, Continuation). Expose detailed observation logs or sync diagnostics only upon clicking dedicated detail links.
-   **Success Criteria**: The user is oriented and continues a thinking session within 10 seconds of opening the screen.

### 9.2 Conscious Workspace Screen
-   **Purpose**: Enable human reasoning through exploring semantic connections, comparing artifacts, and synthesizing new concepts.
-   **Primary Cognitive Question**: *"How do my ideas relate, how do they compare, and what is the synthesis?"*
-   **Entry Conditions**: Triggered by navigating to Workspace/Library or selecting a Concept/Note node. Loads the workspace explorer or selected node state.
-   **Exit Conditions**: Multi-selection state cleared; active comparison views collapsed.
-   **Primary Objects**: Artifacts (notes, documents, events, videos) and Themes (concepts, entities).
-   **Supporting Objects**: Relationship links, property values, and evidence paths.
-   **Primary Actions**: Compare selected items, synthesize multiple items, add/remove from focus, and navigate semantic connections.
-   **Never Show**: Disconnected file trees, generic spreadsheet grids, or standalone delete/edit buttons without context.
-   **Progressive Disclosure**: Show the grid of artifacts first. Upon multi-select, slide up the Workspace Action Bar. Upon clicking "Compare", transition into a side-by-side Comparison Matrix. Upon clicking "Synthesize", present the Synthesis Modal.
-   **Success Criteria**: The user maps a connection, identifies a contradiction, or synthesizes notes into a concept with traceable provenance.

### 9.3 Assistant Pane
-   **Purpose**: Participate in platform-managed thinking sessions to answer queries, trace associations, and explain observations.
-   **Primary Cognitive Question**: *"What does my knowledge web say about this question, and what is the supporting evidence?"*
-   **Entry Conditions**: Triggered by opening the right pane or launching a Thinking Mode capability. Loads the active `ConversationState`.
-   **Exit Conditions**: Conversation history saved; message text input cleared.
-   **Primary Objects**: Conversation messages, active Thinking Mode, and the Context Package.
-   **Supporting Objects**: The Evidence Inspector panel.
-   **Primary Actions**: Select thinking mode, send message, and inspect citation evidence.
-   **Never Show**: Standalone conversational prompts without context packages, general-purpose chatbot UI templates, or unprovenanced claims.
-   **Progressive Disclosure**: Show the thinking mode selector when idle. When active, show the message thread. Disclose detailed evidence (traversed paths, reasoning, confidence) only when the user expands the "Evidence Inspector" badge.
-   **Success Criteria**: The user receives answers anchored entirely in their private knowledge web, accompanied by verified evidence paths.

### 9.4 Platform Center
-   **Purpose**: Oversee system health, configure knowledge sources, and manage background synchronization.
-   **Primary Cognitive Question**: *"Is the cognitive OS healthy, and what sources are connected?"*
-   **Entry Conditions**: Triggered by navigating to Platform Settings. Loads health diagnostics and connector statuses.
-   **Exit Conditions**: Saved configuration states.
-   **Primary Objects**: `KnowledgeSource` descriptors, `SyncHistory` runs, and hierarchical health domains (Kernel, Registry, Providers, Models).
-   **Supporting Objects**: System parameters and connector configuration schemas.
-   **Primary Actions**: Add knowledge source, configure connector credentials, trigger manual sync, and review system diagnostics.
-   **Never Show**: User knowledge content (notes, concepts, conversations) or AI reasoning interfaces.
-   **Progressive Disclosure**: Show overall status indicators (Ready/Healthy). Disclose advanced parameters and raw error logs only when a specific health domain or sync run is expanded.
-   **Success Criteria**: The user configures a connector or diagnoses a synchronization issue without exposing personal knowledge content.

---

## 10. Interaction Grammar

The Interaction Grammar defines how users navigate and manipulate objects within the associative web.

### Selection
-   **Rule**: Selecting any object (artifact or concept) centers the workspace around it.
-   **Behavior**: The selected item becomes the focal node, and the surrounding proximity fields immediately adapt to show temporally and semantically adjacent items. The right panel is updated with the active object's context.

### Navigation
-   **Rule**: Navigation is a transition in focus, not a file-system traversal.
-   **Behavior**: The user moves by clicking related links, traversing association lines, or jumping via global command menus. Directory-tree walking is prohibited.

### Context Switching
-   **Rule**: The active mental state of a workflow must be recoverable.
-   **Behavior**: When the user switches between Thinking Sessions, the platform saves the active context and conversation history so the mental context can be restored with a single click.

### Multi-Selection & Comparison Experience
-   **Rule**: Comparing artifacts must compute intersections and divergences.
-   **Behavior**: Selecting multiple items activates the floating Workspace Actions Bar. Clicking "Compare" overlays a side-by-side matrix detailing shared concepts (intersection), metadata variations (divergence), and contradictory statements.

### Synthesis Experience
-   **Rule**: Consolidating artifacts must preserve provenance.
-   **Behavior**: Selecting multiple notes and choosing "Synthesize" generates a new concept or note. The platform automatically attaches the source notes' UUIDs to the new object's `Evidence` properties, ensuring the chain of provenance remains unbroken.

### Reflection Experience
-   **Rule**: Querying must be guided by active thinking sessions.
-   **Behavior**: Users consult the Assistant to explore observations, trace connections, and analyze contradictions. The system updates the thinking state dynamically, exposing raw evidence under citation links.

---

## 11. Visual Grammar

The Visual Grammar enforces low-stimulation, high-focus aesthetics.

### Information Density & White Space
-   **Rule**: White space is a functional layout tool, not empty real estate.
-   **Behavior**: Layouts must preserve generous margins and line heights (1.6x minimum for reading). Avoid cramped columns and wall-to-wall cards. Each screen must have a clear visual anchor.

### Typography Hierarchy
-   **Rule**: Emphasize readability and calm editorial presentation.
-   **Behavior**:
    -   **Titles**: Geometric, track-tight sans-serifs (e.g. Outfit, system defaults) at generous scale.
    -   **Body Text**: Highly readable, humanist sans-serifs (e.g. Inter) or elegant serifs for long-form reading.
    -   **Monospace**: Reserved strictly for file paths, timestamps, and confidence percentages.

### Icon Usage
-   **Rule**: Icons are functional glyphs, not decorative elements.
-   **Behavior**: Use a consistent, minimal library (e.g., Lucide). Icons must maintain a 1-to-1 relationship with object types:
    -   `Brain` = Concepts
    -   `FileText` = Notes/Documents
    -   `Video` = Videos
    -   `Calendar` = Events
    -   `Clock` = Time/History
    -   `Compass` = Thinking Sessions

### Motion & Transitions
-   **Rule**: Motion must reinforce spatial relationships, never distract.
-   **Behavior**: Use subtle, short-duration (150ms-250ms) ease-out transitions. Focus shifts use horizontal slides; panel expansions use spring-like unfolds. Flashing animations, high-frequency spinning loaders, and abrupt layout jumps are forbidden.

### Color Philosophy
-   **Rule**: Low-stimulation, high-contrast palettes that protect focus.
-   **Behavior**:
    -   **Base**: Deep charcoal/slate dark modes or soft linen light modes.
    -   **Accent**: Curated, low-saturation hues tailored to specific spaces (e.g. muted slate for notes, soft indigo for concepts, soft purple for assistant). High-saturation primary reds and neon yellows are prohibited.

---

## 12. Navigation Grammar

The Navigation Grammar governs the layout architecture of DeepCore.

### The Three-Column Architecture
All primary workspace screens are divided into three functional columns:

```
┌─────────────────┬─────────────────────────────────┬─────────────────┐
│                 │                                 │                 │
│                 │                                 │                 │
│    COLUMN 1     │            COLUMN 2             │    COLUMN 3     │
│                 │                                 │                 │
│  Navigation &   │        Workspace Focus          │    Assistant    │
│  Scope Column   │         Canvas Column           │  Context Pane   │
│   (240px max)   │           (Flex-1)              │   (360px-600px) │
│                 │                                 │                 │
│                 │                                 │                 │
└─────────────────┴─────────────────────────────────┴─────────────────┘
```

1.  **Column 1: Navigation & Scope (Persistent Space)**: Left sidebar containing global links (Home, Conscious Workspace, Platform Center) and active workspace boundaries.
2.  **Column 2: Workspace Focus Canvas (Workspace Space)**: The central workspace where notes, concept trees, comparison matrices, or diagnostic panels are displayed.
3.  **Column 3: Assistant Context Pane (Assistant Space)**: The right panel hosting the active thinking session and evidence inspector. The user can expand/collapse this pane to reclaim canvas space.

---

## 13. Connector Experience

Connectors are never implicitly trusted. Trust is established through verification, provenance, and repeatable synchronization. Ingestion is governed by the principles of explanation, preview, and progressive trust:

```
[ Discover ] ➔ [ Understand ] ➔ [ Connect ] ➔ [ Preview ] ➔ [ Sync ] ➔ [ Verify ] ➔ [ Trust ]
```

1.  **Discover**: The user views available source connectors in the Platform Center.
2.  **Understand**: Before authorization, the system displays a clear, plain-language description of exactly what fields, files, or meta-properties will be accessed (e.g. *"Apple Calendar connector will read event titles, participants, and times. It will not read location details or calendar notes"*).
3.  **Connect**: The user authorizes the connector locally.
4.  **Preview**: The system scans the source and displays a structural preview of identified artifacts. Ingestion does not begin until the user confirms.
5.  **Synchronize**: The ingestion runner executes in the background. The user sees a quiet, non-obtrusive progress indicator.
6.  **Verify**: The synchronization run completes. The user is presented with a clear report of scanning totals (new, updated, and missing/deleted files).
7.  **Trust**: The source is frozen and joins the regular background synchronization cycle.

---

## 14. Workspace Experience

The Conscious Workspace is the primary cognitive studio of DeepCore. It is composed of five core interactive experiences:
-   **Exploration Experience**: Traversing semantic branches and exploring concept graphs. The system dynamically updates active focus contexts based on selection.
-   **Comparison Experience**: Evaluating multiple notes, files, or concepts side-by-side. The workspace highlights shared connections and flag anomalies.
-   **Synthesis Experience**: Merging and consolidating notes into higher-level themes. Provenance links are automatically generated.
-   **Continuation Experience**: Pre-populating prompts and dragging context packages from the workspace directly into reasoning steps in the Assistant panel.
-   **Decision Experience**: Translating analysis into committed actions, notes, or concept states, while permanently binding the associated evidence.

---

## 15. Assistant Experience

The Assistant is not a standalone chatbot. It is a collaborative participant in a platform-managed **Thinking Session**:
-   **Session Ownership**: Conversations cannot exist in a vacuum; they belong to a `ThinkingSession` that tracks the user's active goals.
-   **State Consumption**: The Assistant reasons over the active platform state (comprising focus intents, awareness summaries, and context packages) rather than being coupled to specific conversation implementations.
-   **Evidence-First Invariants**: The Assistant does not provide state-free predictions. Every conceptual claim must be supported by a platform-level `Evidence` object, enabling the visual **Evidence Inspector** to render relationship paths and reasons under each citation link.

---

## 16. Evolution Rules

To maintain the architectural integrity of DeepCore as it grows:
1.  **Screen Conformity**: Any new screen added to the platform must define its Screen Grammar (Purpose, Primary Question, Entry/Exit Conditions, Primary/Supporting Objects, Never Show, and Success Criteria) before development begins.
2.  **Connector Purity**: Connectors must only discover and translate provider data into canonical domain objects. They must never map directly to registry types, communicate with database layers, or define classification logic.
3.  **Aesthetic Invariance**: All new components must use the tokens, typography, and spacing defined in the visual grammar. Default browser alert dialogs, high-saturation colors, and engagement loops are strictly forbidden.
4.  **Experience Evolution Criteria**: Any proposed change to the user experience must:
    -   *Reduce Cognitive Load*: Decrease the mental steps required to capture, find, or relate information.
    -   *Improve User Trust*: Maintain absolute visibility of data provenance and evidence rationale.
    -   *Preserve Orientation*: Ensure the user always understands where they are and what has changed.
    -   *Uphold the Silence Contract*: Avoid introducing gamification, unsolicited notifications, or attention-seeking animations.

# DeepCore Experience Design Workshop — Journey 1
## First Knowledge Source: Connector Onboarding

This document captures the collaborative design exploration for the first knowledge source onboarding experience. The goal is to design an interface and flow that feels calm, trustworthy, and aligned with DeepCore's core principles before any implementation specification is written.

---

## The Journey Map (Onboarding Steps)

```
[ Step 0: Intent ] ➔ [ Step 1: Discovery ] ➔ [ Step 2: Understanding ] ➔ [ Step 3: Configuration ] ➔ [ Step 4: Authorization ]
                                                                                                                │
[ Step 8: Active Trust ] ◄── [ Step 7: Verification ] ◄── [ Step 6: Ingestion ] ◄── [ Step 5: Preview ] ────────┘
```

---

## Step 0: Intent (Establishing Context)

### Cognitive Checkpoint
*   **The User's Core Question**: *"Why should I connect my knowledge sources to DeepCore, and what will it help me achieve?"*

### User Journey
*   **Human Intent**: The user enters the platform for the first time. They want to understand the value of creating a local-first memory vault. They are prompted by a quiet welcome space that encourages them to connect their first knowledge repository.
*   **Interaction**: The user clicks a quiet trigger card in the center canvas: "Bring Your Knowledge."

### Cognitive Journey
*   **Cognitive Transition (Orientation)**: Moves from passive awareness of a new empty platform to understanding the core value proposition of local-first cognitive augmentation. Resolves uncertainty about the platform's utility.

### System Journey
*   **Backend & Platform Activity**: The system boots into its initial clean state. The local SQLite database is active and verified, but contains no active repository paths or external sync runs.
*   **Awareness & Registry Updates**: The Awareness Layer compiles a default empty state payload indicating that no source connections are configured, generating a suggestion card prompting the user to initialize a repository.

### Collaborative Notes
*   **Rationale**: Let's the user orient themselves (Cognitive Question 1: *Where am I?*). It sets the expectations of a local-first second brain rather than jumping immediately to technical configuration grids.
*   **Design Alternatives & Trade-offs**:
    *   *Alternative A: Skip Step 0 and open directly into the Discovery grid at launch.*
        *   *Trade-off*: Feels abrupt and dashboard-like. The user doesn't have a moment of orientation.
    *   *Alternative B: Display a welcome message inside a blocking modal overlay.*
        *   *Trade-off*: Modal overlays interrupt attention. A quiet workspace card is non-intrusive and leaves the user in control.

---

## Step 1: Discovery (The Integration Gateway)

### Cognitive Checkpoint
*   **The User's Core Question**: *"What sources of knowledge can I connect, and are they safe?"*

### User Journey
*   **Human Intent**: The user wishes to see which integrations are supported locally (e.g., local markdown folder, YouTube transcripts) and select the filesystem connector.
*   **Interaction**: The user hovers over and clicks on the "Local Filesystem" card in the connector list.

### Cognitive Journey
*   **Cognitive Transition (Capability Discovery)**: Discovers the options for knowledge sources. Transitions from a passive welcome state to active awareness of local sync capability domains.

### System Journey
*   **Backend & Platform Activity**: The API gateway serves `GET /api/capabilities`, retrieving active sync provider descriptors from the Execution Registry.
*   **Capability Resolution**: The registry resolves registered sync capabilities, determining which providers are installed. It delivers provider descriptors containing human-readable descriptions, scopes, and supported file types to the client.
*   **Awareness & Registry Updates**: System is idle; no active scans or files are locked.

### Collaborative Notes
*   **Rationale**: Promotes capability discovery. The client dynamically queries capabilities rather than hardcoding integrations, ensuring frontend decoupling.
*   **Design Alternatives & Trade-offs**:
    *   *Alternative A: Automatically launch a native folder picker right after clicking "Bring Your Knowledge".*
        *   *Trade-off*: Confusing. The user does not know what file types are supported or what permissions will be read.

---

## Step 2: Understanding (The Explanatory Gateway)

### Cognitive Checkpoint
*   **The User's Core Question**: *"What exactly will this connector do with my files, and what does it ignore?"*

### User Journey
*   **Human Intent**: The user wants to check the read/write scope of the filesystem scanner before giving the application access to their personal Obsidian directory.
*   **Interaction**: The user reviews the access disclosure and clicks "Continue to Configuration."

### Cognitive Journey
*   **Cognitive Transition (Boundary Understanding)**: Understands the clear perimeter of read/write access. Resolves the security boundary, establishing the baseline trust that personal data is protected locally.

### System Journey
*   **Backend & Platform Activity**: The API gateway serves the selected connector's specific `ProviderDescriptor` metadata.
*   **Provider Lifecycle**: The provider state remains "Discovered" but unconfigured.
*   **Registry Updates**: No database changes occur.

### Collaborative Notes
*   **Rationale**: This represents the *Explain before Access* principle. Users need to know exactly what is read (file titles, body text, subdirectories) and what is ignored (ownership metadata, binary files) to establish trust.
*   **Design Alternatives & Trade-offs**:
    *   *Alternative A: Render the configuration inputs immediately, showing the privacy details in a small tool-tip/info icon next to the inputs.*
        *   *Trade-off*: Low cognitive friction but low trust. Most users ignore small icons, leading to accidental configuration of private directories. A dedicated "understanding gateway" makes the action deliberate.

---

## Step 3: Configuration (Parameters Form)

### Cognitive Checkpoint
*   **The User's Core Question**: *"Where on my computer is my folder, and what should be excluded?"*

### User Journey
*   **Human Intent**: The user wants to point the filesystem connector to their active markdown vault and confirm that temporary directories are excluded.
*   **Interaction**: The user clicks "Browse" to select their folder and optionally expands the exclusions accordion to check default glob rules (`.git`, `node_modules`).

### Cognitive Journey
*   **Cognitive Transition (Commitment)**: Expresses intent by declaring the specific folder on disk. Converts passive understanding into active workspace alignment.

### System Journey
*   **Backend & Platform Activity**: The system handles directory picker calls. When a path is selected, the backend verifies folder readability.
*   **Provider Lifecycle**: Transitions to "Configuring".
*   **Registry Updates**: The system validates path formatting.

### Collaborative Notes
*   **Rationale**: Reduces input errors through folder pickers. Exposing exclusions under a collapsed accordion respects *Progressive Disclosure*, keeping the default path clean.
*   **Design Alternatives & Trade-offs**:
    *   *Alternative A: Require users to write exclusions in JSON or YAML format.*
        *   *Trade-off*: Too technical. Simple glob strings are preferred.

---

## Step 4: Authorization (OS Access Verification)

### Cognitive Checkpoint
*   **The User's Core Question**: *"How do I grant local permission for DeepCore to access this folder?"*

### User Journey
*   **Human Intent**: The user wants to approve the operating system's security prompt to allow DeepCore to read the filesystem directory.
*   **Interaction**: The user approves the macOS permission dialog popup.

### Cognitive Journey
*   **Cognitive Transition (Expectation Validation)**: Validates system permissions. Understands that DeepCore respects system-level constraints and will not bypass OS security sandboxes.

### System Journey
*   **Backend & Platform Activity**: The backend executes local path validation checks, ensuring read permissions are active.
*   **Provider Lifecycle**: Transitions from "Configuring" to "Authorized".
*   **Registry Updates**: The workspace configuration updates, adding the path and exclusions as a pending registry metadata source.

### Collaborative Notes
*   **Rationale**: DeepCore must operate within OS sandboxes. Clear UI recovery instructions are necessary if the user denies the OS dialog.

---

## Step 5: Preview (Discoverable Artifacts)

### Cognitive Checkpoint
*   **The User's Core Question**: *"What files did the system find in my folder, and are they correct?"*

### User Journey
*   **Human Intent**: The user wants to scan the files DeepCore found and verify it isn't indexing unwanted files.
*   **Interaction**: The user reviews the list of detected file paths and sizes, then clicks "Confirm & Ingest."

### Cognitive Journey
*   **Cognitive Transition (Confidence Formation)**: Reviews the in-memory scan. Sees exactly which files will be written before committing, building direct confidence in the scanner's accuracy.

### System Journey
*   **Backend & Platform Activity**: The backend initiates a stateless directory scan (`AcquisitionRuntime` scanning stage) using the configuration. It compiles a preview list of files, sizes, and extensions.
*   **Provider Lifecycle**: Transitions to "Previewing".
*   **Registry Updates**: No database writes occur; results are held in-memory.

### Collaborative Notes
*   **Rationale**: Verifies content scope before database commit.
*   **Design Alternatives & Trade-offs**:
    *   *Alternative A: Ingest files immediately without a preview.*
        *   *Trade-off*: The user has no check to ensure they didn't configure the wrong folder root.

---

## Step 6: Ingestion (Active Progress)

### Cognitive Checkpoint
*   **The User's Core Question**: *"Is the initial import happening, and can I continue working?"*

### User Journey
*   **Human Intent**: The user wants to see that the scanner is active and processing their notes, but doesn't want to feel locked to the configuration panel.
*   **Interaction**: The user monitors progress and clicks "Run in Background."

### Cognitive Journey
*   **Cognitive Transition (Cooperative Progress)**: Observes the processing without being blocked. Learns that the engine runs asynchronously in the background, validating the Calm Computing principle.

### System Journey
*   **Backend & Platform Activity**: The Ingestion Service launches the acquisition sync task. It loops through files, parses markdown content, and extracts metadata.
*   **Provider Lifecycle**: Transitions to "Syncing".
*   **Registry Updates**: Registry writes canonical `RegistryObject` entries, maps content indexes, and calculates SHA-256 hashes.
*   **Awareness Updates**: The Home screen shows a passive background progress indicator, leaving the workspace interactive.

### Collaborative Notes
*   **Rationale**: Meets the *No Hidden State* requirement. The background exit button preserves user attention.

---

## Step 7: Verification (Ingestion Summary)

### Cognitive Checkpoint
*   **The User's Core Question**: *"Did the synchronization finish successfully, and what changed in my vault?"*

### User Journey
*   **Human Intent**: The user wants to see the final tally of newly imported notes, ignored items, or errors, confirming the sync completed cleanly.
*   **Interaction**: The user reviews the summary and clicks "Enter Workspace."

### Cognitive Journey
*   **Cognitive Transition (Outcome Integration)**: Reviews the completed sync metrics. Resolves all initial uncertainty regarding file counts, ignored items, and errors.

### System Journey
*   **Backend & Platform Activity**: The sync task terminates. The `sync_runs` database log records execution start/stop times and final file counts.
*   **Provider Lifecycle**: Transitions to "Synchronized".
*   **Registry Updates**: Commits final transactional changes.
*   **Awareness Updates**: Refreshes recent memory lists and triggers initial concept extraction checks over the new imports.

### Collaborative Notes
*   **Rationale**: Closes the ingestion feedback loop, orienting the user to the changes before they enter the workspace.

---

## Step 8: Active Trust (Active Monitoring & Management)

### Cognitive Checkpoint
*   **The User's Core Question**: *"Is the connector healthy, and how do I manage it over time?"*

### User Journey
*   **Human Intent**: The user wants to monitor source health, run manual syncs, or disconnect the folder.
*   **Interaction**: The user reviews active status logs or clicks "Disconnect Source."

### Cognitive Journey
*   **Cognitive Transition (Long-term Trust)**: Transitions to a maintenance state. Assumes the folder is monitored, knows how to self-heal broken paths, and maintains complete control of memory preservation.

### System Journey
*   **Backend & Platform Activity**: Monitors directory readability. If the directory becomes missing (renamed/removed), it reports a warnings state.
*   **Provider Lifecycle**: Active background monitoring loop.
*   **Registry & Awareness Updates**: Upon disconnection, the system handles memory persistence:
    *   *Purge choice*: Recursively deletes associated objects and relationships.
    *   *Freeze choice*: Retains records in database but sets provider references to manual.

### Collaborative Notes
*   **Rationale**: Grants the user absolute authority over memory ownership. Preventing automatic deletions on broken directory paths respects the *Memory Preservation* principle.

---

## Workshop Outcome

### Design Principles Validated
1.  **Silence Contract**: Ambient status indicators and background progress execution work effectively to keep the interface non-intrusive.
2.  **Explain before Expose**: The Explanatory Gateway successfully establishes clear safety boundaries before inputs or permissions are triggered.
3.  **Memory Preservation**: Marking folders as "missing" instead of auto-deleting records during path breaks preserves historical context and relationships.

### Assumptions Rejected
1.  **Rejected Checkbox Agreements**: A checkbox compliance flow in Step 2 was rejected as it induces consent fatigue. Clean dual disclosures ("read" vs. "ignore") are used instead.
2.  **Rejected Active Exclusions Management**: Drag-and-drop file exclusion in the Preview step was rejected in favor of directory parameters and glob configurations, preventing fragile database override states.

### Decisions Frozen
1.  **Decoupled Capability Retrieval**: The client must query installed providers dynamically via `GET /api/capabilities`.
2.  **Incremental Sync Anchoring**: Directory renames are resolved via the "Re-locate" path action, linking active objects back using SHA-256 hashes.
3.  **Quarantined Error Reporting**: Sync warning diagnostics are stored in the Administration Space and never broadcast to the center workspace.

### Open Questions
None. The design is unified and aligned with the constitutional experience invariants.

### Readiness for Implementation Specification
This workshop is considered **APPROVED** and **COMPLETE**. The journey is frozen and ready to be compiled into `CONNECTOR_EXPERIENCE_SPECIFICATION.md`.

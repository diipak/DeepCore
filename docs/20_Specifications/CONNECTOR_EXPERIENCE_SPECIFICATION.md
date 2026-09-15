# Connector Onboarding Experience Specification
## Journey 1: First Knowledge Source Implementation Contract

This document defines the implementation-ready behavior, state transitions, and interaction grammar for onboarding a data source in DeepCore. It serves as the official frontend and backend integration contract.

---

## The Onboarding Lifecycle

```
[ Step 0: Intent ] ➔ [ Step 1: Discovery ] ➔ [ Step 2: Understanding ] ➔ [ Step 3: Configuration ] ➔ [ Step 4: Authorization ]
                                                                                                                │
[ Step 8: Active Trust ] ◄── [ Step 7: Verification ] ◄── [ Step 6: Ingestion ] ◄── [ Step 5: Preview ] ────────┘
```

---

## Step 0: Intent (Establishing Context)

*   **Cognitive Checkpoint**: *"Why should I connect my knowledge sources to DeepCore, and what will it help me achieve?"*

### 1. User Journey
*   **Trigger**: User navigates to Platform settings for the first time or enters the empty state workspace.
*   **Interaction**: User clicks the onboarding card: "Bring Your Knowledge."

### 2. System Journey
*   **API / Capability Resolution**: The client queries `/api/dashboard` to verify active memory counts. Finding counts are zero, it compiles an `AwarenessState` suggestion payload.
*   **Provider State**: All provider configurations are uninitialized.
*   **Registry & Cache Changes**: None.

---

## Step 1: Discovery (The Integration Gateway)

*   **Cognitive Checkpoint**: *"What sources of knowledge can I connect, and are they safe?"*

### 1. User Journey
*   **Trigger**: Click action on "Bring Your Knowledge" card.
*   **Interaction**: User reviews the list of connectors displayed on the screen and clicks on the "Local Filesystem" connector card.

### 2. System Journey
*   **API / Capability Resolution**: Client requests `GET /api/capabilities`. Backend queries `ExecutionRegistry` and returns registered `ProviderDescriptor` items (including name, description, file filters).
*   **Provider State**: Target provider is resolved as "Available/Installed" but remains unconfigured.
*   **Registry & Cache Changes**: None.

---

## Step 2: Understanding (The Explanatory Gateway)

*   **Cognitive Checkpoint**: *"What exactly will this connector do with my files, and what does it ignore?"*

### 1. User Journey
*   **Trigger**: Selection of a connector card.
*   **Interaction**: User reviews the access scope disclosure ("What we read" vs. "What we ignore") and clicks "Continue to Configuration."

### 2. System Journey
*   **API / Capability Resolution**: Client displays metadata from the connector's `ProviderDescriptor`.
*   **Provider State**: Provider is set to "Discovered".
*   **Registry & Cache Changes**: None.

---

## Step 3: Configuration (Parameters Form)

*   **Cognitive Checkpoint**: *"Where on my computer is my folder, and what should be excluded?"*

### 1. User Journey
*   **Trigger**: Click on "Continue to Configuration".
*   **Interaction**: User clicks "Choose Folder" to launch the native directory browser, selects the directory path, and optionally modifies default exclusion globs under the "Advanced Settings" accordion.

### 2. System Journey
*   **API / Capability Resolution**: Client invokes native folder picker. Upon selection, a stateless validation request checks if the path is readable.
*   **Provider State**: Transitions to "Configuring".
*   **Registry & Cache Changes**: Form values (path and globs) are captured in the client's temporary config state.

---

## Step 4: Authorization (OS Access Verification)

*   **Cognitive Checkpoint**: *"How do I grant local permission for DeepCore to access this folder?"*

### 1. User Journey
*   **Trigger**: Click on the configuration form submission button.
*   **Interaction**: User approves the OS directory access permission prompt. If denied, the user follows the instruction card to enable permissions in System Settings.

### 2. System Journey
*   **API / Capability Resolution**: The backend tests directory read access. If read fails, it emits an HTTP 403.
*   **Provider State**: Transitions to "Authorized" upon read verification.
*   **Registry & Cache Changes**: Path and configurations are committed as a source entity in the local configuration database.

---

## Step 5: Preview (Discoverable Artifacts)

*   **Cognitive Checkpoint**: *"What files did the system find in my folder, and are they correct?"*

### 1. User Journey
*   **Trigger**: Successful authorization confirmation.
*   **Interaction**: User scans the list showing the first 10 detected files, relative paths, and sizes, and clicks "Confirm & Ingest."

### 2. System Journey
*   **API / Capability Resolution**: Client requests `POST /api/connectors/preview` passing the source ID. Backend scans the directory, matching path filters, and returns a JSON payload containing the total files count and a list of the first 10 file objects.
*   **Provider State**: Transitions to "Previewing".
*   **Registry & Cache Changes**: None.

---

## Step 6: Ingestion (Active Progress)

*   **Cognitive Checkpoint**: *"Is the initial import happening, and can I continue working?"*

### 1. User Journey
*   **Trigger**: Click on "Confirm & Ingest".
*   **Interaction**: User monitors progress via the status bar and clicks "Run in Background" to continue using the workspace.

### 2. System Journey
*   **API / Capability Resolution**: Client requests `POST /api/connectors/sync` to trigger the sync run. The sync run runs as an asynchronous background worker task. Client polls progress via `GET /api/connectors/sync/status`.
*   **Provider State**: Transitions to "Syncing".
*   **Registry & Cache Changes**: The Acquisition Runtime reads files, registers `RegistryObject` entries, writes the content index, computes SHA-256 hashes, and maps initial folder relationships. Marks the active context as dirty, triggering updates in the Awareness space.

---

## Step 7: Verification (Ingestion Summary)

*   **Cognitive Checkpoint**: *"Did the synchronization finish successfully, and what changed in my vault?"*

### 1. User Journey
*   **Trigger**: Completion of the synchronization run (progress reaches 100%).
*   **Interaction**: User reviews the synchronization counts (new, ignored, errors) and clicks "Enter Workspace."

### 2. System Journey
*   **API / Capability Resolution**: Sync thread finishes. Backend writes execution statistics to the `sync_runs` table, updates the watermark timestamp, and resolves the status.
*   **Provider State**: Transitions to "Synchronized".
*   **Registry & Cache Changes**: Saves final transactions. Triggers the Stage 2 Relationship Engine and Concept Extraction Service over the newly committed IDs, updating the workspace concepts cache.

---

## Step 8: Active Trust (Active Monitoring & Management)

*   **Cognitive Checkpoint**: *"Is the connector healthy, and how do I manage it over time?"*

### 1. User Journey
*   **Trigger**: Navigation to Platform Settings > Connected Sources.
*   **Interaction**: User monitors connector health stats, triggers manual scans ("Sync Now"), or clicks "Disconnect Source."

### 2. System Journey
*   **API / Capability Resolution**:
    *   *Manual Sync*: Triggers an incremental sync worker loop.
    *   *Disconnection*: Client requests `POST /api/connectors/disconnect` passing source ID and the choice parameter:
        *   `purge`: Backend deletes all registry objects and relationships tied to this source's UUID.
        *   `freeze`: Backend keeps database records but strips provider metadata fields, converting them to manual read-only items.
*   **Provider State**: Monitors readability; if the path is missing, it sets state to "Stale/Warning" (`warning` badge).
*   **Registry & Cache Changes**: Purges or locks records based on the user's disconnection choice.

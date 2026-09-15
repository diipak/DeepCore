# Connector Experience Blueprint
## UX/UI Implementation Specification

This document defines the user journey, screen-by-screen flow, state transitions, trust messaging, and interaction rules for onboarding and managing data sources in DeepCore. It serves as the functional blueprint for prototyping and frontend implementation.

---

## 1. The Onboarding Journey (Trust Lifecycle)

Connecting a new data source follows an eight-stage sequence that progressively builds user trust:

```
[ Discovery ] ➔ [ Understanding ] ➔ [ Configuration ] ➔ [ Authorization ]
                                                                 │
[ Trust ] ➔ [ Verification ] ➔ [ Synchronization ] ➔ [ Preview ] ┘
```

---

## 2. Screen-by-Screen Flow & States

### Stage 1: Discovery (Connector Library)
-   **Purpose**: Present available integration connectors grouped by domain.
-   **Screen Layout**:
    -   Header: "Connect Knowledge Sources". Description: "DeepCore runs entirely offline. Data is scanned locally and never leaves your machine."
    -   Grid of Connector Cards: Each card lists the provider name, provider icon, description, and status badge (e.g. *Not Configured, Active, Syncing, Error*).
-   **State Transitions**:
    -   Selecting a non-configured connector card slides in the Explanatory Gateway.
-   **Empty State**: If no connectors are registered by backend plugins, show a centered layout explaining: "No Connector Capabilities Registered. Check plugin installations."
-   **Interaction Rules**: Hovering over cards triggers a subtle border transition. Cards are focusable via keyboard tab navigation.

### Stage 2: Understanding (Explanatory Gateway)
-   **Purpose**: Deliver a plain-language disclosure of what the connector will read, modify, or ignore.
-   **Screen Layout**:
    -   Title: "Understanding [Connector Name]"
    -   Access Scope Columns:
        -   *What we access*: Bullet points of properties read (e.g. File paths, titles, content text, creation date).
        -   *What we ignore*: Bullet points of details ignored (e.g. System metadata, external accounts, file attributes).
    -   Calm Privacy Message: "Local Scan: The file content is read and indexed locally. No network connections are initiated."
-   **State Transitions**:
    -   Clicking "Continue to Settings" advances to Stage 3 (Configuration).
    -   Clicking "Cancel" returns to Stage 1.
-   **Interaction Rules**: The "Continue to Settings" button remains disabled for 2 seconds to encourage reading the disclosure.

### Stage 3: Configuration (Parameters Form)
-   **Purpose**: Capture target folder paths, credential keys, or connection parameters.
-   **Screen Layout**:
    -   Fields tailored to connector type (e.g., Filesystem Connector requests a directory path; Calendar Connector requests calendar selection).
    -   Form Validation Indicators: Inline warnings under inputs.
-   **State Transitions**:
    -   Submitting valid parameters transitions to Stage 4 (Authorization) or Stage 5 (Preview) depending on connector requirements.
-   **Error States**: Path not found, insufficient read permissions, or empty fields display descriptive error text directly below the offending input field.
-   **Interaction Rules**: File explorer buttons open native folder picker overlays.

### Stage 4: Authorization (Permission Request)
-   **Purpose**: Prompt for local system privileges (e.g., macOS Contacts/Calendar access, directory read access).
-   **Screen Layout**:
    -   Informational Panel: "Authorization Required". Explains that DeepCore needs permissions to continue.
    -   CTA Button: "Request System Access".
-   **State Transitions**:
    -   Accepting OS prompt moves to Stage 5 (Preview).
    -   Denying OS prompt displays an instruction card explaining how to grant permissions manually in System Settings.
-   **Error State**: Denied permissions state renders an alert block showing the steps to enable permission in System Preferences.

### Stage 5: Preview (Discoverable Artifacts)
-   **Purpose**: Display identified files or events *before* writing them to the registry database, establishing control.
-   **Screen Layout**:
    -   Heading: "Discovered Artifacts Preview"
    -   Discovery Count Banner: "35 memories found, ready to absorb."
    -   Scrollable List: Top 20 discovered paths/events showing title, type badge (Note, Event), and size.
-   **Loading State**: Display a calm progress text: "Scanning target directory..." with no rapid spinning animations.
-   **State Transitions**:
    -   Clicking "Confirm & Synchronize" launches the initial import, advancing to Stage 6.
    -   Clicking "Back" returns to Stage 3.
-   **Interaction Rules**: Scrollable area features smooth, custom scrollbars. Hovering over list items highlights the path name.

### Stage 6: Synchronization (Active Progress)
-   **Purpose**: Quiet progress reporting during the initial data import.
-   **Screen Layout**:
    -   Status Header: "Absorbing Memories..."
    -   Progress Bar: Quiet horizontal bar showing percentage completed.
    -   Text Details: Path name of the current file being analyzed (e.g., `absorbing: project_plan.md`).
-   **State Transitions**:
    -   Completing synchronization transitions to Stage 7 (Verification).
    -   Clicking "Pause Ingestion" pauses the import state; the progress bar color transitions to amber.
-   **Interaction Rules**: The user can navigate away from this screen; the sync runs in the background. A quiet progress indicator continues in the left Navigation Column.

### Stage 7: Verification (Ingestion Summary)
-   **Purpose**: Deliver a transparent breakdown of imported data, updates, and anomalies.
-   **Screen Layout**:
    -   Header: "Synchronization Completed"
    -   Summary Statistics Cards:
        -   *New Memories Ingested*: Count of newly created objects.
        -   *Memories Updated*: Count of modifications merged.
        -   *Existing (Unchanged)*: Count of identical files skipped.
        -   *Stale Objects Marked*: Count of items marked as missing/deleted.
-   **State Transitions**:
    -   Clicking "Close & Manage" saves configurations and transitions to Stage 8 (Trust).
-   **Interaction Rules**: Hovering over statistics cards displays detail overlays with sample paths.

### Stage 8: Trust (Source Management)
-   **Purpose**: Permanent source monitoring, health diagnostics, and manual syncing actions.
-   **Screen Layout**:
    -   Connection Details: Provider name, local path, last successful sync timestamp.
    -   Health Badge: Shows *Healthy* (Green), *Syncing* (Blue), or *Warning* (Amber).
    -   Action Panel: "Trigger Sync Now" (Manual re-verification) and "Disconnect Source".
-   **State Transitions**:
    -   Clicking "Trigger Sync Now" starts an incremental sync run.
    -   Clicking "Disconnect Source" opens the Disconnection Modal.
-   **Interaction Rules**: Disconnect requires a two-step confirmation to prevent accidental loss of provenance.

---

## 3. Experience Invariants & Rules

### Explain Before Access
-   No parameter forms (Stage 3) or authorization buttons (Stage 4) may be displayed until the user has passed through the Explanatory Gateway (Stage 2) and confirmed understanding.

### Reversibility & Disconnection
-   **Rule**: Disconnecting a connector must prompt the user with a choice regarding memory ownership.
-   **Modal Choices**:
    1.  *Purge Memories*: Delete all registry objects and extracted concepts created by this connector.
    2.  *Retain Memories*: Keep the registered artifacts but strip their connection references, converting them to manual archived nodes.
-   **Verification**: The user must explicitly type "DISCONNECT" to confirm the action.

### Progressive Disclosure
-   Detailed ingestion configuration settings (e.g. glob exclusion filters, content parsing limits) and historical sync run lists must remain collapsed under an "Advanced Connector Configuration" accordion.

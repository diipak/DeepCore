# Connector Library Architecture Specification

This document defines the platform architecture for DeepCore's **Connector Library**. It serves as the authoritative reference governing how external integrations are packaged, discovered, installed, configured, authorized, and managed as platform capabilities.

---

## 1. Purpose

The Connector Library exists to **decouple connector management from connector execution**. 

While the *Knowledge Acquisition Platform* is responsible for runtime sync execution, translation, and data flow, the *Connector Library* is the administrative control layer. Its primary goals are:
- **Modular Autonomy**: Ensuring that connectors can be listed, installed, configured, and uninstalled dynamically without interrupting the execution of other connectors or the core DeepCore kernel.
- **Security Bounding**: Acting as the platform gatekeeper that inspects connector descriptors, validates capability-based permissions, and isolates configuration schemas.
- **Administrative Clarity**: Providing a unified interface for the user to manage their connected apps, track licensing or versions, and monitor integration health.

---

## 2. Connector Lifecycle

Every connector exists within a platform-governed lifecycle, tracing its state from package discovery to removal:

```
    [ Discovery ]         ◄── Scanning capability registry and packages
          │
          ▼
     [ Install ]          ◄── Package added to local platform path
          │
          ▼
    [ Configure ]         ◄── Global/Instance options validated against JSON schema
          │
          ▼
     [ Authorize ]        ◄── Credentials validated and encrypted in secure vault
          │
          ▼
[ Create Knowledge Source ]◄── Configuring a source instance bound to a workspace
          │
          ▼
     [ Healthy ]          ◄── Initial connection test successful
          │
          ▼
      [ Sync ]            ◄── Processing active sync cycles (Pull / Push / Hybrid)
          │
          ▼
     [ Update ]           ◄── Safe version migration / upgrade check
          │
          ▼
     [ Disable ]          ◄── Execution suspended; credentials retained
          │
          ▼
    [ Uninstall ]         ◄── Package code and credentials deleted
```

- **Discovery**: The platform scans system entry points, registered paths, and repositories to list available connectors.
- **Installation**: The connector package is fetched and extracted to the local plugin directory (`~/.deepcore/connectors/`).
- **Configuration & Authorization**: The user provides details and completes OAuth or API token validation.
- **Source Creation**: A configured instance is bound to the active workspace as a **Knowledge Source**.
- **Syncing & Upgrades**: The source operates ambiently, updating its cursors, and receives automatic package upgrades.
- **Disabling & Uninstallation**: Temporarily pausing sync cycles, or permanently removing the connector and purging its stored credentials.

---

## 3. Connector Package Model

The package model structures connectors into hierarchical layers of metadata, logic, and instance configuration:

```
┌────────────────────────────────────────────────────────┐
│                        Package                         │
│ (The physical distribution folder containing assets)   │
├────────────────────────────────────────────────────────┤
│                   ProviderDescriptor                   │
│ (The metadata manifest: permissions, schemas, ID)     │
├────────────────────────────────────────────────────────┤
│                       Connector                        │
│ (The execution logic: Technical Contract methods)      │
├────────────────────────────────────────────────────────┤
│                       Translator                       │
│ (The data translation logic: Pure normalization map)   │
├────────────────────────────────────────────────────────┤
│                    Knowledge Source                    │
│ (The configured, workspace-bound instance in DB)       │
└────────────────────────────────────────────────────────┘
```

### Responsibilities
- **Package**: The zip archive or python package containing the files, tests, and documentation.
- **ProviderDescriptor**: Exposes identity, packaging version, required permission capabilities, configuration schemas, and supported semantic types to the Capability Registry.
- **Connector**: Handles communication with the source (Technical Contract).
- **Translator**: Normalizes raw data to standard DeepCore Objects (Semantic Contract).
- **Knowledge Source**: A database-recorded instance of a Connector containing the configuration parameters and cursor state for a specific workspace.

---

## 4. Installation Architecture

The platform supports both bundled integrations and third-party extensions.

- **Built-in Connectors**: Ships directly inside the DeepCore distribution (e.g. Filesystem Connector). They are registered automatically during database migrations.
- **Third-party Connectors**: User-installed packages downloaded from external sources. They are loaded dynamically from `~/.deepcore/connectors/` or python namespace entry points.
- **Versioning & Upgrades**: Connectors declare a `descriptor_version` (defining schema compatibility) and an `implementation_version`. The platform checks version ranges before upgrading, preventing code-breaking updates from corrupting cursors.
- **Compatibility & Dependency Validation**: The Acquisition Manager verifies that the connector's required platform API version matches the host environment. Optional dependencies (e.g., specific libraries) are verified at import time, falling back gracefully if missing.

---

## 5. Configuration Architecture

The platform enforces a strict separation of configuration levels to ensure multi-tenancy and data isolation:

1.  **Connector Configuration (Global)**: 
    Applies globally to the connector package across all workspaces. This includes installation properties, global client credentials (e.g., a shared OAuth Client ID), and licensing flags.
2.  **Knowledge Source Configuration (Instance)**: 
    Applies to a single configured instance of a connector (e.g. path to a specific folder, username, or specific OAuth access tokens). 
3.  **Workspace Binding (Scope)**: 
    Associates a configured Knowledge Source instance with one or more Workspaces. This defines who and what has visibility into the ingested objects, preventing data leaks.

---

## 6. Permission Architecture

DeepCore operates a capability-based permission model. Rather than providing full system access, connectors must explicitly request capabilities.

```
                  ┌───────────────────────────────┐
                  │      ProviderDescriptor       │
                  │   (Declares permissions req.) │
                  └───────────────┬───────────────┘
                                  │ (Scan)
                                  ▼
                  ┌───────────────────────────────┐
                  │       AcquisitionManager      │
                  │ (Validates & Prompts User)    │
                  └───────────────┬───────────────┘
                                  │ (Approval)
                                  ▼
                  ┌───────────────────────────────┐
                  │        Security Boundary      │
                  │  (Monitors I/O & revokes)     │
                  └───────────────────────────────┘
```

- **Declaration**: Connectors list requested permissions (e.g., `filesystem`, `network`, `calendar`) in their exported `CONNECTOR_DESCRIPTOR`.
- **Review & Approval**: When installing or configuring a Knowledge Source, the system prompts the user to review the requested permission list. Sync execution is blocked until permission is explicitly approved.
- **Revocation**: The user can revoke individual permissions inside the Administration Space. If a revoked permission is called during execution, the Acquisition Runtime intercepts the call and puts the source in a `Degraded` or `Error` state.

---

## 7. Platform Health

Platform health is monitored at the package and configured instance level:

- **Installation Status**: Tracks whether the package files are valid, descriptors match schemas, and dependencies are met.
- **Authorization State**: Standardizes the credential status (`Valid`, `Expiring`, `Expired`, `Revoked`), flagging sources that require user action.
- **Health Indicators**: Dynamic health ratings (`Healthy`, `Degraded`, `Critical`) containing detailed logs.
- **Update Checks**: Flags whether a newer version of the connector is available.

---

## 8. Connector Marketplace Philosophy

DeepCore treats connectors as **first-class extension assets**, mimicking the extensibility model of modern IDEs like VS Code.

- **Dynamic Extension Model**: The platform is open-ended. Anyone can author, package, and distribute a DeepCore connector.
- **Decoupled Development**: The kernel API is stable. Connectors can be developed independently of the core product team.
- **Visual Extensions Registry**: The GUI's Platform Center displays available plugins, allowing users to browse, install, and update integrations with one click.

---

## 9. Reference Connector Strategy

To ensure platform reliability before expanding the marketplace, the development sequence prioritizes reference implementations:

- **Reference Source Connector (Filesystem)**:
  - Validates the local, file-based ingestion pipeline.
  - Serves as the blueprint for local directory walking, hashing, file watching, and pure text translation.
  - No database or complex APIs are required, allowing the team to validate core runtime interfaces first.
- **Strategy Invariant**:
  - No subsequent connector categories (Index, Intelligence, Export) or provider packages (Calendar, Spotlight, OCR) should be implemented until the Filesystem connector has verified the stability of the Acquisition Runtime and Ingestion Service.

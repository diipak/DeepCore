---
Category: Architecture
Status: Stable
Dependencies: [architecture/ARCHITECTURE.md, architecture/INTELLIGENCE_PIPELINE.md]
Source-of-truth: True
---

# DeepCore Platform Architecture Specification

Version: v1.0  
Status: Approved Architectural Specification  
Role: Governing Design Document for Extensibility and Platform Evolution  

---

## 1. Platform Philosophy

DeepCore is designed as an extensible, local-first intelligence platform. To ensure long-term stability, maintainability, and security, the evolution of the platform is governed by six permanent principles of extensibility:

1.  **Everything is Replaceable**: No single component is monolithic or permanently bound. Any provider, tool, skill, or intelligence module can be completely swapped out without breaking the kernel.
2.  **Everything is Discoverable**: Runtimes, tools, and extensions must declare their identity, configuration requirements, and execution bindings through immutable descriptors. The system can inspect and query all capabilities dynamically.
3.  **Everything is Versioned**: All modules, descriptor schemas, database models, and kernel APIs must utilize semantic versioning (SemVer) to govern compatibility, updates, and deprecation.
4.  **Everything is Declarative**: The capabilities, permissions, and settings of an extension are declared in a manifest file. Runtimes must read and validate this manifest prior to execution.
5.  **Nothing Bypasses the Kernel**: Extensions cannot communicate directly with one another or write directly to shared databases outside the kernel's interfaces. The kernel mediates all resource allocation, execution routing, and data flow.
6.  **Composition Over Modification**: Modules extend the system by registering new capabilities and composing existing ones. They never modify the kernel's source code, runtime state, or internal database schemas.

---

## 2. Platform Layers

The platform architecture is divided into four distinct layers. Each layer has an explicit responsibility, separated by strict communication boundaries:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        USER EXPERIENCE (UX)                            │
│    (Memory Universe  •  Conscious Workspace  •  Context Intelligence)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Exposes Descriptors & Context
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   INTELLIGENCE PIPELINE LAYER                          │
│   (Relationships  •  Signals  •  Evidence  •  Discoveries  •  Context)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Mediates Execution & Storage
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          DEEPCORE KERNEL                               │
│     (Runtimes  •  Descriptor Registries  •  SQLite  •  Permissions)    │
└───────────────────────────────────▲────────────────────────────────────┘
                                    │ Loads, Validates, and Orchestrates
                                    │
                        ┌───────────┴───────────┐
                        │                       │
                        ▼                       ▼
            ┌───────────────────────┐ ┌───────────────────────┐
            │    CORE MODULES       │ │   EXTENDED MODULES    │
            │ (Obsidian, YouTube)   │ │  (Finance, Calendar)  │
            └───────────────────────┘ └───────────────────────┘
```

### Layer Responsibilities

1.  **DeepCore Kernel**: The foundational runtime coordinator. The kernel owns the Capability Registry, the Execution Engines (Tool/Skill/Planner Runtimes), the local SQLite database, and the capability-based security boundaries.
2.  **Intelligence Pipeline Layer**: The analytical middleware. It reads canonical records from the kernel's storage, builds relationships, evaluates signals, generates evidence, and synthesizes discoveries.
3.  **Modules (Core & Extended)**: Pluggable execution units. They supply specific connectors (Providers), functional commands (Tools), multi-step tasks (Skills), and analytical rules (Signal/Discovery packs).
4.  **User Experience (UX)**: The presentation layer. The UX layer consumes capability descriptors to dynamically build interfaces and renders context packages compiled by the Context Engine. It cannot call modules directly; all actions flow through the kernel API.

---

## 3. Module Lifecycle

A **Module** is the primary architectural unit of extensibility. Every module goes through a linear lifecycle managed by the kernel:

```
 [Package] ──► [Install] ──► [Validate] ──► [Register] ──► [Configure]
                                                                 │
                                                                 ▼
   [Remove] ◄── [Disable] ◄── [Upgrade] ◄── [Execute] ◄── [Enable]
```

### Lifecycle Phases & Responsibilities

1.  **Package**: The module is compiled into a standardized archive containing the manifest, descriptor definitions, executable code (e.g., Python/JavaScript), and optional static assets.
2.  **Install**: The kernel unpacks the archive into an isolated local directory reserved for extensions.
3.  **Validate**: The kernel inspects the manifest to verify the module's signature, check SemVer compatibility with the current kernel, and validate that the declared descriptor schemas are well-formed.
4.  **Register**: The kernel inserts the module's descriptors into the Capability Registry. At this point, the module's capabilities are discoverable, but its execution is inactive.
5.  **Configure**: The user or system supplies configuration parameters declared as required by the manifest (e.g., target directory paths, API tokens).
6.  **Enable**: The kernel executes any setup routines, activates background workers, and authorizes the module's requested capabilities.
7.  **Execute**: Runtimes invoke the module's tools or skills. The execution engine monitors resource usage, latency, and permission boundaries.
8.  **Upgrade**: When a newer version of a module is available, the kernel pauses execution, backs up configuration, validates the new package, migrates data schemas, and resumes execution.
9.  **Disable**: The kernel terminates the module's running tasks, releases locked resources, and hides its descriptors from the Discovery Service.
10. **Remove**: The kernel deletes the module's directory, unregisters its descriptors, and purges its local cache.

---

## 4. Package Types

Modules are classified into specific categories based on the capability descriptors they export. A single module can pack multiple capability types:

*   **Providers**: Sync engines that ingest data from external systems (e.g., local filesystems, APIs) and normalize them into Canonical Objects.
*   **Tools**: Isolated functional blocks that execute basic operations (e.g., writing a file, checking a system setting, calculating a transaction sum).
*   **Skills**: Composed workflows that coordinate multiple tools using deterministic condition trees.
*   **Prompt Packs**: Declarative instruction sets, context guidelines, and system prompts that calibrate local LLMs for conversation or structured extraction.
*   **Signal Packs**: Mathematical rules and time-series patterns that evaluate anomalies, velocity, and state changes in the knowledge graph.
*   **Discovery Packs**: Ontological configurations and semantic grouping rules that guide the synthesis of thematic discoveries.
*   **Knowledge Packs**: Specialized vocabulary matchers, synonyms, and dictionaries to improve concept promotion.
*   **Themes**: Styling systems defining semantic design tokens, colors, and fonts matching the Calm Intelligence aesthetics.
*   **UI Extensions**: Declarative layout templates and interactive cards loaded dynamically by the Core Shell to render custom data types.

The architecture remains open-ended, allowing the registration of new package categories as descriptor schemas evolve.

---

## 5. Capability Contracts

To prevent untrusted or broken execution, modules interact with the kernel and other modules through explicit **Capability Contracts**. 

```
┌──────────────────────────────────────────────────────────┐
│                    CAPABILITY CONTRACT                   │
├────────────────────────────┬─────────────────────────────┤
│   PROVIDED CAPABILITIES    │    REQUIRED CAPABILITIES    │
├────────────────────────────┼─────────────────────────────┤
│ - Sync finance accounts    │ - filesystem (read only)    │
│ - Fetch merchant icons     │ - network (api.domain.com)  │
│ - Parse PDF statements     │ - model (embedding/text)    │
└────────────────────────────┴─────────────────────────────┘
```

### Capability Negotiation

Before a module is enabled, the kernel performs capability negotiation:
1.  **Manifest Declaration**: The module's manifest lists all required capabilities (e.g., `network.allow = ["api.github.com"]`, `filesystem.read = ["~/Documents/Vault"]`).
2.  **Constraint Validation**: The kernel verifies if the host system can satisfy the requirements (e.g., checking if local models are available, or network access is offline-only).
3.  **User Authorization Gate**: The kernel prompts the user to grant the declared permissions.
4.  **Enforcement**: Runtimes wrap execution in sandboxes that enforce the negotiated permissions. If a module attempts to access an undeclared resource, execution is terminated immediately.

### Contract Versioning

*   Capability APIs are versioned independently of the kernel.
*   Modules define capability contracts using standard version markers:
    ```yaml
    capabilities:
      kernel_api: "^1.0.0"
      context_engine: ">=1.2.0 <2.0.0"
    ```
*   If a contract mismatch is detected, the kernel prevents the module from loading to protect system stability.

---

## 6. Compatibility Model

DeepCore ensures that kernel updates do not break installed modules, and module upgrades do not corrupt local data.

### Kernel & Descriptor Compatibility

*   **Backward Compatibility**: The kernel API maintains strict backward compatibility within major versions.
*   **Descriptor Evolution**: Descriptor models subclass Pydantic schemas. If a descriptor model adds fields, default values are provided to ensure older module manifests parse successfully.
*   **Feature Flags**: Runtimes use feature flag checks rather than hard version limits to verify if an execution environment supports a requested parameter.

### Dependency Management

*   **Capability Requirements**: Modules declare what kernel features they depend on (e.g., database, vector index, planner).
*   **Optional Dependencies**: A module can declare optional bindings. For example, a Calendar module can function independently, but will automatically link to a Finance module if both are enabled.
*   **Migration Requirements**: If a module update modifies its custom database table structures, it must supply a declarative migration scheme (e.g., schema diffs or data migration paths) validated by the kernel.

---

## 7. Security & Capability Boundaries

DeepCore operates under a local-first paradigm where user privacy is absolute. The kernel isolates modules within restricted capability boundaries:

| Permission | Description | Trust Boundary Enforcement |
|---|---|---|
| **Filesystem** | Reading or writing files on the user's computer. | Throttled to explicitly declared directory scopes. Sandboxed processes cannot traverse outside declared paths. |
| **Network** | Connecting to external servers or fetching HTTP endpoints. | Restructured via domain whitelisting. By default, network access is blocked unless specified in the manifest and approved by the user. |
| **Database** | Executing queries or reading tables. | Restricted to custom module namespaces. Modules cannot access or write to tables owned by the kernel or other modules. |
| **Models** | Accessing LLM and embedding generation interfaces. | Intercepted by the kernel's Model gateway. Modules request text generation or embeddings using context limits enforced by the kernel. |
| **Providers** | Ingesting and syncing external records. | Normalization checked by the Registry Layer before records are persisted. |
| **Background Execution**| Running processes when the shell is closed or idle. | Regulated by the kernel's scheduler. The kernel throttles background tasks based on the detected hardware **Capability Tier**. |

---

## 8. Data Ownership Matrix

To prevent data corruption, only designated platform layers are authorized to perform operations on specific artifacts:

```
┌─────────────────┬─────────────┬─────────────┬─────────────┬─────────────┐
│    Artifact     │   Kernel    │ Ingestion / │  Relations /│     UX /    │
│                 │   Registry  │  Providers  │  Analytics  │  Assistant  │
├─────────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│ Source Data     │   Read      │ Read/Write  │   Read      │    Read     │
│ Canonical Obj   │ Read/Write  │ Read/Write  │   Read      │    Read     │
│ Relationships   │ Read/Write  │    None     │ Read/Write  │    Read     │
│ Signals         │ Read/Write  │    None     │ Read/Write  │    Read     │
│ Evidence        │ Read/Write  │    None     │ Read/Write  │    Read     │
│ Discoveries     │ Read/Write  │    None     │ Read/Write  │    Read     │
│ Chat Context    │ Read/Write  │    None     │   Read      │ Read/Write  │
└─────────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
```

*   **Source Data**: Owned by the importing module. Other layers can only read it via registry interfaces.
*   **Canonical Objects**: The Registry Layer manages lifecycle and schemas. Providers can create or update them, but cannot delete them without kernel mediation.
*   **Relationships & Signals**: Created and managed by the Knowledge and Analytics engines. Other layers treat them as read-only references.
*   **Evidence & Discoveries**: Written by the Intelligence Pipeline. The UX layer consumes them to present explainable summaries.
*   **Chat Context**: Managed dynamically by the Conversation Runtime based on user interaction.

---

## 9. Upgrade, Migration, and Safe Removal Lifecycle

As modules evolve, the kernel guarantees data integrity during transitions:

### Version Upgrades & Descriptor Evolution
1.  **State Paused**: The kernel pauses background tasks related to the module.
2.  **Backup**: A snapshot of the module's settings and custom database entries is cached.
3.  **Upgrade Execution**: The module code is updated. If the descriptor schema changes, the Capability Registry validates the new descriptor format.
4.  **Schema Migration**: The kernel executes the module’s data migration script to update local tables.
5.  **Resume**: Runtimes re-enable the module.

### Cache Invalidation & Incremental Recomputation
*   When a module is upgraded or updated:
    *   Content hashes of affected objects are checked.
    *   Associated relationships, signals, and evidence are flagged as `dirty`.
    *   The Intelligence Pipeline runs incremental recomputation only on the dirty paths, protecting system resources from full-graph rebuilds.

### Safe Removal
*   When a module is removed:
    *   Its executable code and descriptors are deleted from the local directory.
    *   The kernel cascades deletion to remove all relations, signals, and evidence generated by that module.
    *   Canonical Objects created by the module are marked as `orphaned` or `archived` rather than abruptly deleted, preserving historical references in the user's graph.

---

## 10. Module Distribution Architecture

The distribution of modules is built on a decentralized architecture. While a centralized marketplace is a possible implementation, the underlying architecture relies on open, decoupled contracts:

```
┌──────────────────┐
│  Developer Keys  │
└────────┬─────────┘
         │ Signs
         ▼
┌──────────────────┐     Verifies     ┌──────────────────┐
│  Signed Module   │ ───────────────► │   Local Kernel   │
│     Archive      │                  │  Security Engine │
└──────────────────┘                  └──────────────────┘
         ▲                                     ▲
         │ Fetches                             │ Queries
┌────────┴─────────┐                  ┌────────┴─────────┐
│ Module Registry  │ ◄─────────────── │  Discovery API   │
│   (CDN / IPFS)   │                  │  (Metadata Index)│
└──────────────────┘                  └──────────────────┘
```

### Architectural Contracts

1.  **Cryptographic Registry**:
    *   Modules are signed using developer keys. The local kernel verifies the signature and cryptographic hashes before installation to prevent code injection.
2.  **Metadata Index**:
    *   Module registries expose metadata indexes in a standard format (e.g., signed JSON files). The Discovery API queries these indexes to retrieve available module descriptors, categories, and updates.
3.  **Transport Independence**:
    *   The kernel can fetch module archives from local directories, standard HTTPS CDNs, or decentralized storage systems. The distribution layers are independent of the network protocol.

---

## 11. Platform Invariants

The DeepCore platform guarantees the following system invariants:

1.  **Kernel Isolation**: Extensions never modify the kernel's memory space, internal runtimes, or database schemas directly.
2.  **Descriptor Governance**: All module capabilities must be declared statically in descriptors. Undocumented features or dynamically injected tools cannot execute.
3.  **Execution Determinism**: The kernel’s planner and execution schedulers remain 100% deterministic and reproducible.
4.  **Grounding Invariant**: All AI interpretations, conversation responses, and synthesized discoveries must trace back to deterministic evidence and objects.
5.  **Module Independence**: All modules are independently installed, configured, upgraded, disabled, or removed.
6.  **Platform Forward-Compatibility**: The core platform layers can evolve without requiring updates to individual module codebases, provided capability contracts are maintained.

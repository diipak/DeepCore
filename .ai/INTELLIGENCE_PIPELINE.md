# DeepCore Intelligence Pipeline Architecture

Version: v1.0  
Status: Approved Architectural Specification  
Role: Governing Design Document for Enrichment, Discovery, and Intelligence  

---

DeepCore does not attempt to think instead of the user. It continuously compiles the user's digital reality into trustworthy understanding, allowing the user to think with greater clarity.

## 1. Executive Summary & Philosophy

The DeepCore Intelligence Pipeline governs how raw digital information is processed, structured, validated, and translated into human understanding and action. Operating under a local-first, privacy-ensured paradigm, this architecture prioritizes explainability, reproducibility, and resource efficiency.

### Memory vs. Intelligence

A foundational architectural law of DeepCore is the absolute division between Memory and Intelligence:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                 DEEPCORE                                │
├────────────────────────────────────────┬────────────────────────────────┤
│            MEMORY LAYER                │      INTELLIGENCE LAYER        │
├────────────────────────────────────────┼────────────────────────────────┤
│ - Records reality.                     │ - Interprets reality.          │
│ - Deterministic, immutable facts.      │ - Probabilistic or rule-based. │
│ - Provenance, hashes, and sync state.   │ - Abstractions, relationships. │
│ - What happened.                       │ - Why it matters & means.      │
└────────────────────────────────────────┴────────────────────────────────┘
```

1. **Memory (Reality)**: The ingestion and preservation layer. Memory is responsible for tracking files, transactions, history, and messages exactly as they occur in external source systems. It is immutable, versioned, hashed, and deterministic. Memory has no opinion and performs no semantic interpretation.
2. **Intelligence (Interpretation)**: The analytical and synthesis layer. Intelligence reads the facts stored in Memory, infers connections, detects temporal anomalies, synthesizes thematic topics, and presents explanations. Intelligence can be probabilistic, context-dependent, and adaptive.

---

## 2. What is Intelligence?

Intelligence in DeepCore is defined as a progressive hierarchy of stages, moving from unstructured information to human action. Each stage has a singular responsibility and builds upon the stage below it:

```
   Information   [Raw external content & logs]
        ↓
     Objects     [Normalized canonical database entities]
        ↓
   Relationships [Inferred or explicit links between objects]
        ↓
     Signals     [Mathematical anomalies & temporal events]
        ↓
    Evidence     [Provenance & verification bundles]
        ↓
   Discoveries   [High-level thematic & semantic synthesis]
        ↓
     Context     [Active subset of workspace attention]
        ↓
  Understanding  [Conversational alignment & explanations]
        ↓
     Action      [Deterministic task execution & goals]
```

### The Stage Hierarchy

*   **Information**: Raw digital content. Unprocessed Markdown files, JSON payloads from external financial APIs, raw YouTube transcript text, and repository commits.
*   **Objects (Canonical Objects)**: Uniquely identified, schema-validated database records. This layer maps unstructured Information to standard types (`document`, `project`, `video`, `note`, `repository`, `transaction`, `merchant`, `idea`, `concept`) with universal IDs, metadata payloads, and content hashes.
*   **Relationships**: Semantic and structural links connecting two or more Canonical Objects. These denote associations like a transaction *at* a merchant, a note *referencing* an idea, or a project *using* a repository.
*   **Signals**: Time-sensitive anomalies, frequency spikes, velocity changes, or logical events derived mathematically from Objects and Relationships (e.g., spending drift, idle project warnings, topic emergence).
*   **Evidence**: The first-class collection of deterministic facts, provenance links, and temporal states that back any analytical claim. Evidence bridges the gap between deterministic data and probabilistic interpretation.
*   **Discoveries**: High-level thematic syntheses or realizations. A Discovery group-analyzes related signals and relationships to represent deep insights (e.g., shift in developer tools usage, convergence of personal interest areas).
*   **Context**: The dynamic assembly of Objects, Relationships, Signals, and Discoveries relevant to the user’s current focus or task window.
*   **Understanding**: The collaborative reasoning space. It allows the user to query, critique, and align with the synthesized context via conversation, receiving explainable, cited answers.
*   **Action**: The execution boundary. It translates the user's intent or the assistant's plans into deterministic operations (e.g., initiating a sync run, updating an object status, or scheduling tasks).

---

## 3. Intelligence Invariants

Every component in the DeepCore Intelligence Pipeline must satisfy these platform-wide invariants without exception:

1.  **Object Provenance**: Every Object registered in the system must possess verifiable provenance (a known source system, ingestion path, and original timestamp).
2.  **Explainable Relationships**: Every Relationship must map to explicit, documented criteria or matching metadata that justifies its creation.
3.  **Deterministic Signals**: Every Signal must be computed using pure mathematical or rule-based logic. No probabilistic AI models may generate Signals.
4.  **Evidence Grounding**: No Discovery can exist without referencing a concrete, immutable bundle of Evidence containing specific Objects, Relationships, or Signals.
5.  **Bounded AI Context**: Every AI-driven interpretation or conversation response must be explicitly bound to, and cite, deterministic inputs and Evidence retrieved from the storage layer.
6.  **Incremental Execution**: Every pipeline stage must support incremental execution using watermarks or dirty flags, processing only changed inputs since the last execution.

---

## 4. Foundational Dimensions: Time & Confidence

### Time as a Foundational Dimension

Time is not merely metadata in DeepCore; it is an active dimension across all stages:
*   **Temporal Decay**: Relationships decay in confidence over time if not reinforced by recurring sync runs, user interactions, or updated references.
*   **Signal Velocity**: Signals evaluate trends over sliding windows (e.g., changes in frequency, activity rates, or transaction volumes).
*   **Discovery Resurgence & Abandonment**: Discoveries track their own state lifecycle. A theme may transition to "dormant" if its backing Signals subside, and return to "active" upon resurgence of activity.

### Confidence as a Platform-Wide Concept

Every output generated by the pipeline must supply a confidence valuation:
*   **Confidence Vector**: Composed of a numeric confidence index (0.0 to 1.0) and a qualitative metadata descriptor containing:
    *   *Source Integrity*: How reliable is the provider (e.g., signed API data vs. OCR text).
    *   *Path Derivation*: Deterministic match (1.0) vs. heuristic inference (0.5).
    *   *Temporal Decay Factor*: Adjustment based on age.
*   **Traceability**: Downstream stages compile and weigh confidence vectors from their upstream dependencies to compute their own confidence score.

---

## 5. Pipeline Stage Contracts

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Information   │ ──► │     Objects     │ ──► │  Relationships  │ ──► │     Signals     │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
                                                                                 │
                                                                                 ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Action      │ ◄── │  Understanding  │ ◄── │     Context     │ ◄── │    Evidence     │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
                               ▲                                                 │
                               │                                                 ▼
                               └──────────────────────────────────────────  Discoveries
```

### 1. Objects (Normalization)
*   **Purpose**: Translate raw information from providers into canonical, uniquely identified registry entities.
*   **Inputs**: Raw files, data streams, API payloads, metadata.
*   **Outputs**: `RegistryObject` entries with UUIDs, status fields, and content hashes.
*   **Ownership**: Registry Layer.
*   **Persistence**: Database (`registry_objects` table).
*   **Incremental Strategy**: Verify source identifiers and compare content SHA-256 hashes before creating or updating.
*   **Failure Modes**: Duplicate external IDs, hash mismatches, missing title/provenance metadata.
*   **Testability**: Ingest simulated corrupted or duplicated payloads and assert deduplication and schema adherence.
*   **Future AI Role**: Dynamic schema matching for unsupported provider formats.

### 2. Relationships (Linkage)
*   **Purpose**: Form typed connections and associations between canonical objects.
*   **Inputs**: Canonical Objects, Content Indices, metadata fields.
*   **Outputs**: `RegistryRelationship` entries with type, confidence, and source fields.
*   **Ownership**: Knowledge Layer.
*   **Persistence**: Database (`registry_relationships` table).
*   **Incremental Strategy**: Process only newly registered or updated objects using their modification timestamps.
*   **Failure Modes**: Circular dependencies, reference orphaned IDs, relationship explosion (over-linking).
*   **Testability**: Assert that specific object relationships are created or removed based on changes in content files.
*   **Future AI Role**: Cross-lingual semantic link suggestions.

### 3. Signals (Anomalies & Triggers)
*   **Purpose**: Identify mathematical patterns, velocity spikes, and temporal events across objects and relationships.
*   **Inputs**: Timelines of objects, updated relationships, transaction metrics.
*   **Outputs**: Numeric and boolean signal markers with computed values (e.g., velocity, acceleration).
*   **Ownership**: Metadata & Analytics Layer.
*   **Persistence**: Persistent Cache / Timeseries Store.
*   **Incremental Strategy**: Run sliding window aggregations using a watermarked event log.
*   **Failure Modes**: Alarm fatigue (excessive signals), stale window parameters.
*   **Testability**: Feed simulated time-series events and assert signal activation at exact thresholds.
*   **Future AI Role**: Dynamic anomaly baseline calibration.

### 4. Evidence (Grounding)
*   **Purpose**: Assemble the deterministic backing facts supporting high-level discoveries.
*   **Inputs**: Matching Signals, Relationships, Objects, and source files.
*   **Outputs**: Immutable Evidence Bundles containing explicit node and edge arrays, and hash snapshots.
*   **Ownership**: Context & Provenance Layer.
*   **Persistence**: Database / Embedded JSON.
*   **Incremental Strategy**: Created or modified whenever a backing Signal is triggered or updated.
*   **Failure Modes**: Disconnected provenance, stale hash tracking.
*   **Testability**: Assert that deleting a backing object invalidates or marks the corresponding evidence bundle as incomplete.
*   **Future AI Role**: None. Evidence must remain strictly deterministic.

### 5. Discoveries (Synthesis)
*   **Purpose**: Thematically organize and synthesize multiple signals and evidence bundles into high-level realizations.
*   **Inputs**: Evidence Bundles, Active Relationships, Concepts.
*   **Outputs**: Thematic Discoveries (e.g., "Software Tools Expense Surge").
*   **Ownership**: Intelligence Layer.
*   **Persistence**: Database.
*   **Incremental Strategy**: Triggered by changes to backing evidence bundles. Recomputes only the impacted themes.
*   **Failure Modes**: Irrelevant syntheses, conflicting discovery statements.
*   **Testability**: Inject known mock evidence bundles and verify that the correct Discovery is synthesized with correct confidence.
*   **Future AI Role**: Thematic labeling, grouping of disparate concepts, and synthesis summaries.

### 6. Context (Attention Assembly)
*   **Purpose**: Assemble the relevant subset of objects, relationships, and discoveries matching the user's active attention window.
*   **Inputs**: User interaction signals (current active screen, open files, active chat).
*   **Outputs**: Bounded Context Package containing active entities and connections.
*   **Ownership**: Context Engine.
*   **Persistence**: In-memory session store.
*   **Incremental Strategy**: Updates dynamically as user focus shifts, appending and removing items from the package.
*   **Failure Modes**: Context bloat, omission of key related objects.
*   **Testability**: Verify context package properties when navigating through a mock user flow.
*   **Future AI Role**: Context pruning and similarity ranking.

### 7. Understanding (Co-Reasoning)
*   **Purpose**: Conversational space where the user aligns with the synthesized Context and inspects explanations.
*   **Inputs**: Context Package, User Prompts, Evidence Bundles.
*   **Outputs**: Natural language responses with strict citations pointing back to Objects.
*   **Ownership**: Conversation Runtime.
*   **Persistence**: Chat History / Conversation Log.
*   **Incremental Strategy**: Message-by-message appending in active conversation sessions.
*   **Failure Modes**: AI Hallucinations, citation mismatches, context leakage.
*   **Testability**: Assert that all returned messages contain valid citations and do not reference objects outside the context package.
*   **Future AI Role**: Context-guided response formulation, query translation.

### 8. Action (Execution)
*   **Purpose**: Execute deterministic capabilities or planner tasks resulting from conversation or user commands.
*   **Inputs**: Validated goals, task parameters, commands.
*   **Outputs**: Task execution states, newly written files, external API executions.
*   **Ownership**: Execution & Runtime Layer.
*   **Persistence**: Planner state, task logs.
*   **Incremental Strategy**: Topological DAG step execution.
*   **Failure Modes**: Execution timeouts, unauthorized side effects, dependency cycle locks.
*   **Testability**: Test with Mock executors and verify state machine transitions and retry loops.
*   **Future AI Role**: Formulation of execution plan steps based on goals.

---

## 6. Computational Architecture: Capability Tiers

To remain practical for local-first deployment on consumer hardware, DeepCore categorizes execution environments into three **Capability Tiers**. Rather than requiring specific hardware specifications, the pipeline adjusts its operations based on the detected tier:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            CAPABILITY TIERS                             │
├───────────────────┬─────────────────────────────┬───────────────────────┤
│      TIER 1       │           TIER 2            │        TIER 3         │
│   (Low-Power)     │         (Standard)          │      (Expanded)       │
├───────────────────┼─────────────────────────────┼───────────────────────┤
│ - CPU-only local  │ - Unified Memory or         │ - High-end local PC   │
│ - Rules, Regex    │   Integrated GPU / NPU      │   Dedicated GPU / NPU │
│ - Min. background │ - Fast local embeddings     │ - Multi-modal models  │
│ - No local LLM    │ - Small local LLM (3B-8B)   │ - Continuous execution│
└───────────────────┴─────────────────────────────┴───────────────────────┘
```

### Stage Resource Allocation Profile

| Stage | CPU Characteristics | Memory Characteristics | Storage Impact | Streaming | Cache Strategy |
|---|---|---|---|---|---|
| **Objects** | Low. Standard text parsing. | Minimal. In-memory buffers. | Low. Row inserts in DB. | Yes | Cache schemas and file metadata. |
| **Relationships** | Low to Medium. In-memory graph traversal. | Medium. Graph nodes loaded in memory. | Low. Row inserts in relationship DB. | No | Cache relationship matrix. |
| **Signals** | Low. Simple time-series math. | Low. Sliding window values. | Low. Timeseries cache. | Yes | Keep sliding window cache in memory. |
| **Evidence** | Low. Bundling and hash checking. | Low. Temp serialization. | Medium. Structured JSON bundles. | No | Read-through cache of objects. |
| **Discoveries** | High. Semantic clustering. Tier 1 bypasses AI. | Medium to High. Vector indexes. | Medium. DB writes of themes. | No | Cache until backing evidence changes. |
| **Context** | Low. Query assembly. | Low. Bounded collection. | None. In-memory. | Yes | None. Discarded on session end. |
| **Understanding** | High. Local inference. Tier 1 delegates to API. | High. Model weights. | High. Model weights (Tier 2/3). | Yes | Cache chat history; clear on session end. |
| **Action** | Low. Orchestration. | Low. State machines. | Low. Audit log entries. | Yes | None. Execution state must remain fresh. |

### Tier-Specific Execution Rules

1.  **Tier 1 Execution (Fallback)**:
    *   *AI Interpretation Layer*: Disabled or delegated to secure, user-configured remote APIs.
    *   *Discoveries*: Restricted to rule-based thematic aggregation.
    *   *Incremental Execution*: Aggressive. Background processing is throttled or runs only during idle states.
2.  **Tier 2 Execution (Standard)**:
    *   *AI Interpretation Layer*: Active using quantized small models (3B to 8B parameter size).
    *   *Discoveries*: Periodic batch recomputes using local model features.
    *   *Incremental Execution*: Runs periodically in the background when the system is awake.
3.  **Tier 3 Execution (Expanded)**:
    *   *AI Interpretation Layer*: Active using full local models.
    *   *Discoveries*: Real-time background compilation.
    *   *Incremental Execution*: Continuous execution triggered by sync events.

---

## 7. The Deterministic Boundary

A strict architectural boundary divides deterministic processing and AI interpretation. This boundary is designed to maximize trust, safety, and performance.

```
                  DETERMINISTIC BOUNDARY
                            │
   DETERMINISTIC PROCESSING │ AI INTERPRETATION
   (100% Reproducible)       │ (Probabilistic / Contextual)
                            │
   Information              │ Discoveries
   Objects                  │ Context
   Relationships            │ Understanding
   Signals                  │ Action (Goal-planning)
   Evidence                 │
                            │
```

### Why the Boundary Exists

1.  **Trust & Explainability**: The system never guesses if an object exists or how two nodes are related. The graph is built on deterministic criteria. If the AI suggests an insight, the user can inspect the deterministic Evidence bundle backing it.
2.  **Reproducibility**: Re-running the database migrations or re-syncing the provider files yields the exact same graph representation.
3.  **Resource Efficiency**: The heavy computational tasks of indexing and relationship construction are kept rule-based. Local LLMs are reserved only for high-value synthesis (Discoveries) and conversation (Understanding), conserving CPU cycles and battery life.

---

## 8. Extension & Provider Lifecycle

DeepCore supports dynamic registration of external providers and capability extensions. Every extension must step through a rigid, automated lifecycle:

```
[Install] ──► [Capability Registration] ──► [Configuration] ──► [Synchronization]
                                                                        │
                                                                        ▼
[Signal Generation] ◄── [Relationship Processing] ◄── [Canonical Objects]
         │
         ▼
[Evidence Capture] ──► [Discovery Generation] ──► [Context Availability]
```

### Lifecycle Steps

1.  **Install**: The provider package is unpacked in an isolated execution sandbox.
2.  **Capability Registration**: The extension registers its `ProviderDescriptor` with the Capability Registry. This descriptor declares the capabilities, object types, and relationship types the extension exposes.
3.  **Configuration**: The extension requests configuration parameters (e.g., directory paths, local API access credentials).
4.  **Synchronization**: The extension's sync routine is called, processing raw content and outputting Canonical Objects to the Registry Layer.
5.  **Canonical Objects**: The Registry Layer validates the output objects, computes content hashes, and persists them.
6.  **Relationship Processing**: The Knowledge Layer runs the extension's deterministic relationship builders alongside system-wide builders.
7.  **Signal Generation**: Registered signal rules analyze the updated graph to extract mathematical patterns.
8.  **Evidence Capture**: For any triggered signals, Evidence is structured, linking the objects and signals.
9.  **Discovery Generation**: The Intelligence Layer evaluates updated Evidence to re-synthesize themes.
10. **Context Availability**: The extension's outputs are indexed and made discoverable to the Context Engine.

---

## 9. Intelligence Lifecycle: Data Propagation & Recomputation

Synchronization and recomputation propagate through the pipeline via an event-driven, incremental process:

```
┌──────────────┐      ┌──────────────────────┐      ┌─────────────────────────┐
│ Ingestion /  │ ───► │  Object Registered/  │ ───► │  Relationship Builder   │
│ Sync Event   │      │  Updated Event       │      │  Triggered              │
└──────────────┘      └──────────────────────┘      └─────────────────────────┘
                                                                 │
                                                                 ▼
┌──────────────┐      ┌──────────────────────┐      ┌─────────────────────────┐
│ Discovery    │ ◄─── │  Evidence Updated /  │ ◄─── │  Signal Checker Runs    │
│ Recomputed   │      │  Assembled           │      │  (Incremental window)   │
└──────────────┘      └──────────────────────┘      └─────────────────────────┘
```

1.  **Sync Event**: A provider sync run completes, emitting a transaction payload of newly created, modified, or missing Object IDs.
2.  **Registration Hook**: The Registry Layer updates the `registry_objects` table and emits an `ObjectChanged` event.
3.  **Linkage Hook**: The Relationship service reads the changed objects, runs incremental relationship queries, and commits changes, raising a `RelationshipChanged` event.
4.  **Signal Evaluation**: The analytics loop processes sliding temporal windows affected by the changed relationships, outputting new signal values.
5.  **Evidence Assembler**: If a signal passes its threshold, the system packages an Evidence Bundle and updates the database, raising an `EvidenceChanged` event.
6.  **Incremental Synthesis**: The Discovery worker receives the `EvidenceChanged` event. It evaluates only the thematic paths linked to the modified evidence, re-running synthesis to refresh active Discoveries.

---

## 10. Experience Mapping

The technical pipeline stages translate directly into distinct, high-value user outcomes:

| Technical Stage | Technical Value | Experience Outcome |
|---|---|---|
| **Objects** | Normalize files, notes, transcripts, and financial records into standardized database models. | **"Everything is here."**<br>The user feels a sense of secure, complete retention; no memories are lost or fragmented. |
| **Relationships** | Connect concepts, people, systems, and transactions deterministic-link style. | **"Everything is connected."**<br>Context surfaces naturally as the user navigates. No manual folders or tagging required. |
| **Signals & Evidence** | Track velocities, spending shifts, idle states, and ground them in auditable facts. | **"I can trust this."**<br>Insights are not "magic." The user can see exactly why a warning or connection exists. |
| **Discoveries** | Synthesize complex patterns over time into thematic summaries. | **"It understands me."**<br>DeepCore reveals high-level themes, tracking the user’s projects and focus shifts. |
| **Context & Understanding** | Bound local LLM context to active objects; support cited Q&A. | **"It helps me think."**<br>A conversational companion that answers questions based strictly on user memory. |
| **Action** | Translate user intent and plans into API interactions and workflows. | **"It helps me act."**<br>Conversations and thoughts transition smoothly into tasks, notes, or fintech executions. |

---

## 11. Complexity Budget

Every future intelligence capability proposed for DeepCore must justify its existence across a strict **Complexity Budget**. This serves as a formal architectural review gate before any implementation begins.

```
                     COMPLEXITY BUDGET REVIEW GATE
 ┌──────────────────────────────────────────────────────────────────┐
 │                                                                  │
 │  1. Product Value         - Does this improve Memory,            │
 │                             Understanding, or Action?            │
 │  2. Architectural Fit     - Does it preserve the Deterministic   │
 │                             Boundary and Stage Contracts?        │
 │  3. Computational Cost    - Can it run on Tier 1 or Tier 2       │
 │                             consumer hardware?                   │
 │  4. Operational Cost      - Does it run local-first, avoiding    │
 │                             expensive cloud dependencies?        │
 │  5. Human Cognitive Load  - Does it preserve Calm Intelligence   │
 │                             or create noisy dashboards?          │
 │                                                                  │
 └─────────────────────────────────┬────────────────────────────────┘
                                   │
                                   ▼
                            [PASS / REJECT]
```

### Review Gate Constraints

1.  **Product Value**: A feature must directly enhance the core loops of *Remembering*, *Understanding*, or *Acting*. Auxiliary analytics or cosmetic metrics will be rejected.
2.  **Architectural Fit**: The feature must strictly align with the stage contracts. If a feature mixes deterministic relationships and probabilistic AI synthesis, it must be split across the Deterministic Boundary.
3.  **Computational Cost**: Must be verified to run smoothly on Tier 2 baseline environments (16GB RAM / 8 CPU Cores). Background indexing must not cause CPU spikes or thermal throttling.
4.  **Operational Cost**: The feature must be local-first. If a remote cloud API is required, it must remain fully optional and user-configured, with Tier 1 local fallbacks active.
5.  **Human Cognitive Load**: Features must adhere to the *Calm Intelligence* principles. They should present context when needed, avoiding complex multi-column dashboards, notification fatigue, and data tables.

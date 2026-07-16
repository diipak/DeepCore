# Experience Architecture Specification
## DeepCore Product Foundation

---

### 0. The Human Problem

Modern computer operating systems and digital tools are built on structural metaphors from the physical world of the mid-20th century: files, folders, directories, and silos. While these abstractions serve machine architecture, they fundamentally clash with the mechanics of human cognition.

This architectural mismatch manifests in three primary cognitive friction points:

*   **Rigid Silos vs. Associative Memory**: Humans do not recall information by navigating hierarchical trees. Human memory is associative; we remember that a budget proposal is connected to a specific client discussion, which occurred on a rainy Tuesday, which reminds us of an email about cloud costs. Digital systems force us to choose a single "folder" for a file, isolating it from the rich web of associations that give it meaning.
*   **Knowledge Fragmentation**: A single project's context is fragmented across dozens of disconnected tools: files are in directories, discussions are in chat applications, tasks are in trackers, and research is in browser tabs. Each tool demands manual search, manual indexing, and manual correlation.
*   **Context Loss and Interruption Cost**: Reconstructing the mental state of a complex task after an interruption takes significant cognitive energy. Finding where we left off, which files were open, and how they relate is a major source of digital fatigue.

DeepCore exists to bridge this gap, establishing a system that mimics the associative, continuous, and context-rich nature of human thought.

---

### 1. Product Definition

Experientially, DeepCore is a **quiet, local-first cognitive partner** that extends human memory and correlation. 

It is not a "productivity app," a "database manager," or a "search tool." It is a private cognitive layer that runs silently on the user's hardware. It operates under the premise that the user should focus on reasoning, deciding, and creating, while the system handles the cognitive tax of preserving provenance, mapping relationships, and maintaining continuity.

DeepCore is a calm interface. It does not demand attention, gamify engagement, or push notifications. It is a mirror of the user's own understanding—always available, completely private, and organized by meaning.

---

### 2. Mental Model

To use DeepCore, the user should only need to maintain one mental model: **The Associative Web**.

In this model:
*   **Information Flows, It Does Not Sit**: The user does not "file" items. They capture, edit, or create, and the system absorbs.
*   **Relationships are Discovered, Not Declared**: Links emerge organically based on content similarity, temporal proximity, and shared concepts. If two documents discuss the same subject or are edited during the same workflow, they draw close to one another in the associative space.
*   **Context is Proximity**: Searching for an item is not about locating a path; it is about centering the view on that item and observing the constellation of related concepts and references that gather around it.

---

### 3. User Goals

Every workflow and interface in DeepCore must be designed to serve one of four fundamental human goals:

1.  **Solving a Complex Problem**: Querying across diverse knowledge pools to synthesize new conclusions, locate hidden contradictions, or analyze multi-dimensional topics.
2.  **Recovering Forgotten Context**: Returning to a project or thought path after hours, days, or months of absence, and having the cognitive state immediately rebuilt.
3.  **Maintaining Ambient Awareness**: Keeping a quiet, peripheral view on emerging patterns, connections, or structural issues in the user's knowledge ecosystem (such as dead ends, dormant ideas, or sudden overlaps).
4.  **Reducing Cognitive Load**: Offloading details—conversations, read materials, transient notes, or research—to a trusted local repository, confident they will be automatically resurfaced at the exact moment they are relevant.

---

### 4. Cognitive Commitments

These commitments are architectural invariants. Every feature, service, or interface change proposed for DeepCore must respect and enforce these promises:

*   **No Location Memory Required**: The user must never be forced to remember *where* a piece of information is stored to find it. The system must retrieve it via meaning, association, or time.
*   **Explainable Connectivity**: Every relationship, connection, or concept link surfaced by the system must be fully explainable. "Black box" correlations are forbidden. The user must always be able to ask, *"Why is this linked?"* and receive a clear, deterministic explanation of the evidence.
*   **Unbroken Provenance**: The raw source and origin of any memory, fact, or insight must never be hidden or obscured. The path back to the original document, email, webpage, or note must always be a single interaction away.
*   **Protected Attention**: The platform must never interrupt the user's focus. There are no unsolicited alerts, badges, or distractions. The system processes silently in the background and presents its insights only when the user chooses to look.
*   **Continuous Context Preservation**: Transitioning between tasks or shutting down the application must not destroy the current working context. The system must preserve the active workspace state so it can be resumed instantly.

---

### 5. Experience Principles

These five principles govern how the product behaves, feels, and presents information:

*   **Calm over Density**: Protect the user's visual and mental bandwidth. Avoid cluttered grids, high-frequency tickers, and complex nested menus. Use breathing space, curated typography, and clean layouts.
*   **Explain before Expose**: When presenting automated relationships or observations, show the synthesized meaning or the reasoning behind them before exposing the raw underlying database structures.
*   **Purpose before Implementation**: The interface must speak the language of human thought (projects, thoughts, linkages, focus), never the language of database engines, synchronization protocols, or system architecture.
*   **Progressive Disclosure**: Show the simplest, most human-readable summary first. Allow the user to drill down into deeper connections, metadata, and raw logs only as their active intent demands it.
*   **Context over Navigation**: The interface should adapt to what the user is doing *right now*. If the user is writing a document, the system should show relevant context matching that document, rather than forcing the user to navigate away to search.

---

### 6. Product Objects

Rather than exposing database tables or system components, DeepCore presents four core conceptual primitives to the user:

*   **Artifacts (The Units of Context)**: The physical items of knowledge (notes, transcripts, videos, files, transactions). These are the individual nodes of memory.
*   **Themes (The Centers of Meaning)**: Organic clusters of meaning that emerge from the contents of Artifacts. Themes are not folder names or static tags; they are dynamic conceptual hubs (topics, projects, entities) that grow, shrink, and merge based on active knowledge.
*   **Connections (The Associative Links)**: The relationships binding Artifacts and Themes. They can be explicit (user-defined links) or emergent (system-detected similarities, shared references, or temporal proximity).
*   **Observations (The System Insights)**: Temporary or temporal awareness signals generated by the system (e.g., *Dormant Work*, *Active Focus*, *Orphaned Items*, *Broken Connections*). They highlight structural patterns in the user's second brain.

---

### 7. Primary Workflow

The user experience follows a cyclic, four-stage journey:

1.  **Capture (Ambient Ingestion)**: The user drops a file, writes a note, or pastes a link. There is no manual sorting, tagging, or filing required.
2.  **Link (Emergent Synthesis)**: The system quietly maps the new item into the Associative Web. The user experiences the delight of seeing their new note automatically anchor to existing themes and related documents.
3.  **Assist (Conversational Query)**: The user asks the Assistant questions about their accumulated knowledge, exploring connections across sources without needing to open them individually.
4.  **Reflect (Contextual Application)**: The user uses the surfaced relationships, summaries, and context to write, code, or make decisions, closing the loop.

---

### 8. Navigation Architecture

Navigation in DeepCore is not a walk down a hierarchical directory tree. It is a **shift in focus** across an associative space.

The navigation system is built around three conceptual states of movement:

*   **Proximity Navigation**: Moving to an active object centers the user's context. The surrounding references, associations, and observations adapt dynamically to show what is semantically and temporally close to that active object.
*   **Temporal Navigation**: The capacity to slide across a timeline of activity, revealing what was captured, modified, or connected during a specific workflow or day.
*   **Intent-Driven Jumps**: A global search or command interface that lets the user jump instantly to any Theme, Artifact, or Conversation, skipping structural paths entirely.

---

### 9. Home Experience

The Home experience is the **Cognitive Center of Gravity** of the application. It represents the user's active focus and system awareness.

Home is a live reflection of:

*   **The Current Focus**: The active project workspace, ongoing threads, or items that the user is actively working on.
*   **System Observations**: Surfaced insights from the signal engine that require cognitive resolution (such as dormant clusters, broken references, or potential connections).
*   **The Entrance Portal**: A simple, central capture point to drop thoughts or files immediately.

---

### 10. Assistant Experience

The Assistant is the **conversational interface to the user's accumulated understanding**.

*   **Architectural Responsibility**: The Assistant's sole purpose is to translate the complex, multi-layered Context Packages generated by the intelligence engine into clear, conversational, and actionable reasoning.
*   **Contextual Anchorage**: The Assistant does not generate responses from general knowledge alone; it anchors its understanding in the specific Artifacts, Themes, and Connections present in the user's registry.
*   **No Black-Box Answers**: The Assistant must cite its sources for every claim. Every referenced fact, note, or connection in the conversation must link directly to the underlying Artifact, allowing the user to inspect the source instantly.

---

### 11. Progressive Disclosure (Self-Teaching)

DeepCore teaches the user how it works by being **transparent, interactive, and evidence-based**.

*   **Exposing the Rationale**: Whenever the system creates an emergent link, surfaces a concept, or generates an observation, it includes a simple, interactive explanation. Selecting a connection reveals the evidence (e.g., *"We linked these notes because both mention 'API Integration' and were edited on the same day"*).
*   **Actionable Observations**: The system introduces concepts like "Orphaned Notes" or "Dormant Projects" not through documentation, but as live, actionable observations. When an orphan note is detected, the system suggests: *"This note has no connections. Connect it to Theme X?"*
*   **Ambient Onboarding**: On first launch, as the user adds their first notes, they see the graph and concepts populate in real-time, with micro-explanations describing how DeepCore identified the themes and mapped the relationships. The interface teaches through action.

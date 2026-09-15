---
Category: Governance
Status: Stable
Dependencies: [architecture/PRODUCT_VISION.md]
Source-of-truth: True
---

# DeepCore Development Roadmap

Milestone Development Roadmaps for the DeepCore personal intelligence engine.

---

## Completed Phases

### Phase 1: Registry
- Established database foundation (SQLite, SQLAlchemy).
- Created schemas for `RegistryObject`, `RegistryRelationship`, and `SyncRun`.
- Standardized object state tracking (`active`, `missing`, `archived`).

### Phase 2: Capture
- Implemented intake service layer.
- Added automatic metadata extraction for YouTube URLs and manual notes.

### Phase 3: Content Index
- Implemented `ContentIndex` and file watching for Markdown source files.
- Added content hash validation to avoid redundant parsing.

### Phase 4: Concepts
- Created heuristics-based concept extraction.
- Developed relationship matching based on text mentions.
- Built a governance API for approving, ignoring, and merging concepts.

### Phase 5: API Gateway
- Reorganized single routes configuration into a modular routes package.
- Exposed registry, content, and concept capabilities via FastAPI.

### Phase 5.1: Experience APIs
- Refined `/api/concepts` default sorting order to prioritize approved status.
- Added `/api/memories/recent` filtering human-created notes, videos, and documents.
- Created `/api/dashboard` returning dashboard stats, top concepts, and recent memories.

### Phase 6: DeepCore Shell v0.1
- Developed mobile-first responsive web client (React/TypeScript) consuming registry and knowledge endpoints.

### Phase 7: Context Engine
- Built context query resolution querying objects, contents, and relationships.
- Compiles deterministic context packages with content hashes for LLM reasoning windows.

### Phase 8.1 - 8.3: Tool, Skill, & Execution Runtimes
- **Tool Runtime**: Validation, isolated execution, resources tracking, and timeout hooks.
- **Skill Runtime**: Recursive composite tool chains with recursive check limits.
- **Execution Runtime**: Duck-typed execution gateway resolving executables by descriptor.

### Phase 9: Planner Runtime
- Kahn's algorithm scheduler processing plans into execution order.
- Replaced Python expressions with a secure, custom condition expression evaluator.
- Normalizes and binds dynamic variable references before step execution.

### Phase 9.5: Kernel Integration & Diagnostics
- Compiled full kernel e2ee pipeline testing (Retry recovery, skipped branches, cancellations).
- Verified 100% determinism running identical plans 50 times in a loop with zero variance.
- Implemented `KernelHealthReport` compiling runtimes, tools, skills, and executables status.

### Phase 10: Conversation Runtime
- Established client-neutral conversation schemas (`history` and `artifacts` reserved fields).
- Implemented Conversation gateway coordinator, direct command routing, and planner delegation.
- Integrated `/api/conversation` and `/api/conversation/capabilities` API routes.

### Phase 11: Descriptor Standardization Framework
- Standardized metadata contract inheritance from frozen `BaseDescriptor`.
- Implemented `DescriptorProvider` protocol ensuring self-describing components.
- Introduced `ProviderDescriptor`, `PromptDescriptor` (variables metadata), and `ModelDescriptor`.

### Phase 12: Capability Registry Architecture
- Developed a metadata-only `CapabilityRegistry` storing capability descriptors.
- Enforced ID uniqueness, category checks, and pre-registration integrity validations.
- Guarantees alphabetical ID sorting for all lookups.

### Phase 13: Capability Discovery Service
- Created stateless composition layer mapping internal descriptors to `CapabilitySummary` and `CapabilityDetail`.
- Compiles `CapabilityCatalog` dynamically grouped by category.

### Phase 14: Capability Discovery HTTP API
- Integrated dynamic capabilities lookup and dynamic catalog grouping endpoints (`GET /api/capabilities`).
- Standardized gateway mapping to client-safe summaries and category listings.

### Capability 03: Deterministic Relationship Engine
- Implemented relationship rules (references, folder, source, tags, duplicate, version) in ingestion pipeline.
- Added symmetrical complements, provenance tracking, and structured evidence.

### Phase 15: Experience Architecture Specification
- Created `docs/00_Foundation/experience_architecture.md` defining cognitive commitments, invariants, and conceptual workflow mappings.

### Phase 16: Information Architecture Specification
- Created `docs/00_Foundation/information_architecture.md` defining the attention layers, priority rules, experience spaces, and context lifetimes.

---

### Phase 17.0: LLM Wiring (v2 Kickoff — supersedes prior Phase 17 priority)
- Diagnosed that the Conversation Runtime had no reasoning model behind it: DIRECT mode literally echoed the user's message, and the YouTube provider captured only title/channel metadata (no transcript), never content.
- Added `deepcore/intelligence/llm_client.py` (`OllamaClient`), the one deliberately non-deterministic seam in the kernel, calling a local Ollama instance. Configurable via `DEEPCORE_OLLAMA_HOST` / `DEEPCORE_OLLAMA_MODEL` / `DEEPCORE_OLLAMA_TIMEOUT` (`deepcore/config.py`), defaulting to the user's locally available model.
- `ConversationRuntime` DIRECT mode now always compiles a `ContextPackage` (previously only on trigger-object or PLANNING mode) and grounds the LLM prompt in both the Context Engine's graph results and full note-body search via `ContentService.search_content` / `get_content` — not just title/description metadata.
- Unreachable/erroring local models now surface as a clear `ConversationStatus.FAILURE` with a diagnosable message instead of crashing the request.
- Rationale recorded in `.ai/governance/RETROSPECTIVE_AND_V2_KICKOFF.md`: prove a genuinely usable daily-chat-over-notes experience on top of the existing kernel before investing further in runtime depth or the frontend rewrite.
- **Known gap carried forward, not yet fixed**: YouTube transcripts are still not ingested (metadata-only), so video content Q&A doesn't work yet — planned as the fast-follow to this milestone.
- **Known limitation carried forward**: retrieval is still LIKE-based keyword matching (Registry + Content Index), not semantic search, so paraphrased questions may not surface the right notes even though the LLM layer now works.

### Phase 17.0 — Addendum: Two conversation systems discovered, Phase 17.0's target corrected
- Auditing the actual running frontend (Platform Dashboard) revealed a second, independent conversation system already built and uncommitted: `deepcore/core/assistant/service.py` (`ConversationService`), exposed at `/api/conversations/*`, with its own persistence (`ThinkingSession`/`Conversation`/`Message`), five product-defined "thinking modes," and integration with a real `AwarenessService`. **This is the system the UI actually calls.** `ConversationRuntime` (what Phase 17.0 wired to Ollama) is not reachable from the UI at all.
- `ConversationService.post_message` currently generates replies via `_generate_thoughtful_reply`, a hardcoded stub (checks for the literal word "quantum", otherwise returns a canned non-answer). The AI Assistant panel in the running app is a scripted demo, not a real assistant, despite Phase 17.0's fix.
- Decision: keep `ConversationService` as the chat-facing system (better fit — persistence, evidence citations, named modes matching product vision), port the Ollama + Context Engine + Content Search grounding logic into it, and retire `ConversationRuntime`'s DIRECT/PLANNING modes as a competing chat path. Its Planner/Tool/Skill execution stack is not being discarded — it's repurposed as an internal capability `ConversationService` can call into later for multi-step actions, not a standalone chat endpoint.
- Tracked as the immediate next milestone (below), ahead of YouTube transcripts.

### Phase 17.2: Real Data Ingestion — Notes Vault
- The filesystem connector and sync pipeline (`/api/connectors/sync`) were real and working but had never been pointed at real data — every registered source showed 0 notes.
- Found two duplicate "Obsidian Vault" source rows (both seeded pointing at `~/Documents/Notes`, neither ever synced). Verified zero registry objects and zero completed syncs on the unused duplicate (source ID 5) before deleting that single row; nothing on disk was touched.
- Synced source ID 4 against the real vault: 42 objects scanned/created, 0 errors, 41 content-indexed (1 skipped — a genuinely 0-byte file, correctly excluded, not a bug).
- **Known bug found, not yet fixed**: sidebar note-count badges still show "0 notes" for Obsidian Vault despite 42 real synced notes — a display/data-binding issue, not a data issue. Confirmed via direct DB query and the Memories/Dashboard screens that the data itself is correct.

### Phase 17.3: Concept Extraction Quality Fix
- First extraction pass over the 42 real notes produced 1,057 "concepts," but visual inspection of the Concepts screen showed the top of the list (ranked by connection count, which is also how `ContextEngine` prioritizes) was dominated by common English words with no domain meaning ("You" with 11 connections, "Create," "Open," "Use," "Get," etc.) — a direct threat to future assistant answer quality, not just UI clutter.
- Fixed in `deepcore/core/concepts/service.py`: expanded stopword filtering (pronouns, generic verbs, generic UI/note words), and tightened the single-word candidate rule to require an actual technical-term signal (PascalCase, ALLCAPS ≥ 2, or digits) rather than qualifying on frequency/capitalization alone. Multi-word phrases where every word is a stopword are now discarded too.
- Verified zero approved concepts existed before wiping (nothing had been reviewed yet), then deleted the 1,057 unapproved candidates and their 1,332 relationships — notes/events (42/2) confirmed untouched — and re-ran extraction: 556 concepts, 636 mention-relationships, 3,438 total relationships. Top-20-by-connection-count is now dominated by real terms (AI, API, LLM, DeepCore, FastAPI, OpenAI, ChatGPT, Docker Compose, DNS, HTTPS) instead of stopwords.
- **Known gap, not yet fixed**: a few generic terms ("Features," "ID") still appear in the top 20 — likely because the separate heading-based extraction path wasn't tightened the same way as the frequency/single-word path. Residual noise here is expected to be mopped up by the existing concept-governance approve/ignore workflow over time, not blocking further work, but the heading-path filter gap should get the same treatment eventually.

**See `.ai/governance/V2_EXECUTION_PLAN.md` for the full immediate/near-term/long-term breakdown and active task list — that document is now the working source for sequencing, this one remains the historical phase log.**

### Phase 17.4: Real Assistant Wired (commit `0bb83fb`, branch `feature/conversation-service-llm-wiring`)
- Ported the Ollama + Context Engine + Content Search grounding from Phase 17.0 into `ConversationService` (`deepcore/core/assistant/service.py`), the system the UI actually calls — extracted into a reusable `deepcore/intelligence/grounding.py` (`GroundedPromptBuilder`), with bounded conversation-history inclusion and graceful failure handling.
- `ConversationRuntime`, its schemas, and `/api/conversation` fully removed after confirming zero remaining references. Planner/Tool/Skill/Execution stack underneath preserved untouched, per the V2 addendum's decision to keep it for future action-taking.
- Fixed a real workspace-scoping bug found during review: `ContextEngine` wasn't threading `workspace_id` through to `RegistryService`, meaning grounded answers could have silently queried the wrong workspace once more than one exists. Fixed and covered by an adversarial two-workspace test.
- Alongside this, re-ran concept extraction with the "Docker/Python" fix from Phase 17.3: 860 concepts, 1,003 relationships (see Phase 17.3 for the known limitation carried forward — allowlist-only fix, not the generalizing heuristic originally approved).
- **Current open step**: real end-to-end usage — asking it real questions about the real Notes vault and judging the answers, not another automated test. See `.ai/governance/V2_EXECUTION_PLAN.md` item 3.

## Following Milestone: Phase 17.1 — YouTube Transcript Ingestion
Fill in real video content (not just metadata) so the assistant can answer questions grounded in what a video actually says, matching the notes-side content-indexing that already works. YouTube is also not yet on the current connector framework (`deepcore/connectors/`) — it still uses the older `core/providers/` pattern, which is a separate decision to resolve when this milestone is picked up.

## Deferred: former Phase 17 — UI Alignment with Experience & Information Architecture
Align the DeepCore React/TypeScript frontend workspace with the Experience and Information Architecture Specifications. Deferred behind the LLM/transcript milestones above — no point re-aligning a UI to specs before the chat experience underneath it actually works end to end.

### Core Goals (unchanged, deferred)
- **Cognitive Space Separation**: Map the user interface into distinct spaces (Awareness, Knowledge, Understanding, Administration) and enforce strict Platform Isolation for background systems.
- **Attention Layering**: Adjust layouts to respect the 5 layers of attention, keeping focus clean and observations secondary.
- **Workspace Navigation Refactoring**: Transition sidebar elements from DB-centric terms to dynamic, purpose-driven navigation.
- **Context Preservation**: Align the frontend state to preserve active context, transient searches, and dormant states.


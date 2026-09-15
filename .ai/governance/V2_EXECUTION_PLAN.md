---
Category: Governance
Status: Active
Dependencies: [architecture/PRODUCT_VISION.md, governance/RETROSPECTIVE_AND_V2_KICKOFF.md, governance/ROADMAP.md]
Source-of-truth: True
---

# DeepCore V2 Execution Plan

Written: 2026-08-22
Purpose: The concrete, ordered breakdown of what "Jarvis over your own knowledge" (see `PRODUCT_VISION.md` V2 Addendum) means to build, in what order, and why. This is the working task list — update it as items complete or priorities shift, rather than letting it go stale like `PROJECT_STATE.md` did relative to actual code.

---

## How to read this document

Three horizons. Nothing in Near-Term or Long-Term should get real engineering effort until the Immediate horizon is proven — not because the later items don't matter, but because this is exactly the mistake v1 made (building depth before proof of daily use). Each task below has a status placeholder; keep it current.

---

## Immediate — prove the core loop works

**Goal:** you can ask DeepCore a real question about your real notes and get a real, cited answer back, in the system the UI actually calls.

1. **[x] Port Ollama + Context Engine + Content Search grounding into `ConversationService`** — done, commit `0bb83fb` on `feature/conversation-service-llm-wiring`.
   Grounding logic extracted into `deepcore/intelligence/grounding.py` (`GroundedPromptBuilder`), wired into `ConversationService._generate_thoughtful_reply` with conversation history (bounded window) and graceful `LLMUnavailableError` handling. Independently verified: no leftover demo code, workspace_id correctly threaded through `ContextEngine`/`RegistryService` (adversarial two-workspace test confirms no cross-contamination), full test suite passes against the known baseline.

2. **[x] Retire `ConversationRuntime`'s chat-facing modes** — done, same commit.
   `ConversationRuntime`, its schemas (`base.py`), and `/api/conversation` fully removed (not just unmounted) — independently confirmed zero remaining references anywhere in the codebase. The Planner/Tool/Skill/Execution stack underneath is untouched and still fully wired in `composition.py`/`application.py`, exactly as intended.

3. **[ ] Real end-to-end test: ask it something true about your actual notes**
   Not a unit test — you, personally, asking it questions and judging whether the answer is actually good and actually cited. This is the gate. If this doesn't feel real, nothing downstream matters yet. **This is the current open step.**

4. **[ ] Fix the two known-open bugs surfaced during data sync**
   Sidebar note-count badges showing "0 notes" despite real synced data (display/data-binding bug). The Awareness panel claiming "no conceptual anomalies" while 1,057+ unreviewed concepts existed (governance-status disconnect — investigate whether `AwarenessService`'s unapproved-concept check is even querying the right field for bulk-extracted concepts). Small, but they undermine trust in the system precisely when we're trying to prove it's trustworthy.

---

## Near-Term — make it good enough to actually rely on

**Goal:** the assistant is complete and accurate enough that you'd reach for it unprompted, not just when testing it.

5. **[ ] Retrieval quality: move beyond LIKE-based keyword matching**
   Current search (`RegistryService.search_objects`, `ContentService.search_content`) is substring matching — it will miss paraphrased questions even when the answer is sitting right there. Evaluate a lightweight local embedding index (e.g. a local embedding model + a simple vector store) as an addition to, not necessarily a replacement for, keyword search. This is the single biggest lever on "does it actually understand what I'm asking."

6. **[ ] Concept governance triage pass**
   860 candidate concepts exist post-re-extraction (up from 556 — see below), none reviewed. Spend real time approving/ignoring/merging so what the assistant cites as "related concepts" is stuff you'd actually trust, not just heuristically cleaner than before. Also close the heading-based-extraction filter gap ("Features," "ID" still slipping through) noted in `ROADMAP.md` Phase 17.3.
   **Known limitation, not yet fixed:** the "Docker/Python" fix (commit `0bb83fb`) only shipped a ~40-word hardcoded `COMMON_TECH_TERMS` allowlist, not the generalizing mid-sentence-capitalization heuristic that was actually approved in the plan. It works for the specific terms on that list; any real single-capitalized-word term not on it (e.g. "Tailscale") will still be silently dropped, same bug class as the original "Docker" miss. A static allowlist doesn't scale with an evolving personal vault — worth a real fix here (possibly LLM-assisted extraction, now that a local model is wired in) rather than continuing to hand-expand a word list.

7. **[ ] YouTube transcript ingestion**
   The second data source from the original ask. YouTube is currently on the older `core/providers/` pattern, not the current connector framework (`deepcore/connectors/`) — decide whether to build it fresh against the current framework or bridge the old provider in, then actually fetch transcripts (currently a literal placeholder, never implemented).

8. **[ ] Chat-first UX pass**
   Once the assistant is real and reliable, rework the interaction model so chat is the front door and the current dashboard/graph/concepts views become secondary inspection surfaces, not the primary daily experience. This was explicitly deferred earlier in review — pick it up here, now that there's something worth building a front door for. Needs its own dedicated design pass, not a quick reskin.

---

## Long-Term — the actual north star

**Goal:** a private, local, evidence-grounded assistant that knows everything you've chosen to feed it, and can act, not just answer.

9. **[ ] Expand data sources incrementally**
   Calendar, email, finance, browser history, etc. — one at a time, each proven useful before the next, matching the original `PRODUCT_VISION.md` plugin/provider model. Not before Near-Term is solid.

10. **[ ] Pick the Planner/Tool/Skill/Execution stack back up — for real action-taking**
    This is the point of that infrastructure: "remind me about X," "file this note under Y," "trigger a resync." Do not extend this stack speculatively before there's a concrete action to build against.

11. **[ ] Revisit governance/documentation hygiene as a standing practice, not a one-time catch-up**
    This session's biggest process failure wasn't technical — it was 112 files of real work sitting uncommitted and undocumented for weeks. Whatever cadence AG/Claude/you settle into, the safety-commit + review + governance-doc-update loop established in this session should become routine, not a one-off cleanup.

---

## Process note

Established working pattern going forward: Claude (architecture/review) writes scoped specs for AG (implementation). For mechanical, well-specified, safety-checked tasks, AG executes directly and reports a walkthrough. For tasks with real design judgment (like item #1 above), Claude will explicitly ask AG to propose a plan first and pause for review before executing. Claude updates governance docs only after reviewing AG's walkthrough and confirming nothing further is needed — never on the strength of AG's self-report alone.

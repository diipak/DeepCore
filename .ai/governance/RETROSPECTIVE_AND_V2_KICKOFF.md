---
Category: Governance
Status: Historical Record
Dependencies: []
Source-of-truth: True
---

# DeepCore Retrospective — Closing v1, Opening v2

Written: 2026-08-09
Purpose: Preserve v1 as learning history. Nothing here is deleted or reversed — it's a checkpoint before redefining the approach.

---

## The idea that persists

Across every version so far, one thread has never changed: a private, local-first system that captures what you encounter, understands how it connects, and gives it back to you when useful — through one assistant-style interface rather than a pile of separate apps.

That's the part that's still true today. What's being retired is *how far ahead the previous version tried to build it, and in what order.*

---

## The two eras that came before

### Era 0 — "Digital Brain" (design-only)
Docs and mockups only, living in `DigitalBrainDump/` and early planning notes. Core principles coined here: **Effortless Drop** (frictionless capture) and **AI-Powered Rewind** (meaning-based retrieval, not keyword search). Stack explored: React 18 + TypeScript + Vite + IndexedDB + TensorFlow.js client-side, optional cloud sync (Drive/Dropbox/OneDrive), four UI directions explored (FlowBI-style analytics, Apple-minimalist chat, neural/futuristic, mobile PWA). Never reached working code — stayed at architecture-and-mockup stage.

### Era 1 — "DeepCore" engineered kernel (the one being retired now)
A real, running codebase: Python/FastAPI backend + SQLite, React/TypeScript "shell" frontend, full test suite. This is the project currently sitting in `DeepCore/`.

What got built, in order:
1. **Registry** — object model for notes, videos, docs, transactions, etc., with relationships and lifecycle states.
2. **Capture** — intake pipeline with metadata extraction (YouTube, manual notes).
3. **Content Index** — file-watching + hashing for markdown, dedup on re-index.
4. **Concepts** — heuristic concept extraction, governance lifecycle (candidate/approved/ignored), merge/dedup logic.
5. **API Gateway** — FastAPI routes exposing registry/content/concepts.
6. **Shell v0.1** — mobile-first React client.
7. **Context Engine** — deterministic context packages for LLM reasoning.
8. **Tool / Skill / Execution Runtimes** — isolated tool execution, composite skill chains, execution gateway.
9. **Planner Runtime** — Kahn's-algorithm DAG scheduler with a custom condition-expression evaluator.
10. **Kernel Integration** — full e2e pipeline tests, verified deterministic across 50 runs.
11. **Conversation Runtime** — client-neutral conversation schema, command routing.
12. **Descriptor Standardization + Capability Registry/Discovery** — a self-describing metadata layer for every component in the system, with its own HTTP API.
13. Two large Experience/Information Architecture specs, with the next planned phase (17) being a full frontend rewrite to align with them.

Governing philosophy (from `DeepCore_Development_Protocol.md`): "an Operating System for Personal Intelligence," deterministic kernel below the LLM layer, architecture strictly before features.

---

## Why v1 is being set aside

You haven't given me a formal list of reasons, so this section is deliberately short — it's your call, not mine to reverse-engineer. What the artifacts themselves suggest, for you to confirm or correct:

- **Depth before proof-of-life.** Seventeen phases of kernel engineering (runtimes, planners, capability registries, descriptor standardization) were built before there was a frontend anyone could actually live in day to day. That's a lot of deterministic plumbing underneath very little daily-use surface area.
- **Architecture-first as a stated principle, at the cost of visible momentum.** The protocol explicitly ranks architecture above features. That's defensible, but it's also exactly the kind of principle that quietly produces a system that's impressive in the abstract and thin in the "do I open this every day" sense.
- **The next planned phase was already a frontend do-over** (Phase 17: realign the shell to specs written after the fact) — a signal that the UI and the backend drifted apart, or that the backend logic hardened before the actual user experience was ever pressure-tested.

If any of that reads wrong, correct me — I'd rather be argued with than have you nod along to a diagnosis I invented.

---

## What's worth keeping as knowledge, regardless of what v2 looks like

- The **object model** (everything is an object: id/type/title/source/content/concepts/relationships) is a genuinely reusable framing, independent of implementation.
- **Capture → Understand → Act** as a user journey (vs. navigate → open modules → manage data) is a good product instinct worth re-testing, not re-deriving from scratch.
- Concept extraction, relationship inference, and content indexing are solved problems in this codebase — even if the shape of v2 is different, the working code and tests are a reference implementation, not something to redo blind.
- The "deterministic kernel, probabilistic reasoning only at the LLM layer" instinct is a real architectural lesson worth carrying forward regardless of how much of the runtime survives.

---

## Where things stand right now

- `DeepCore/` is untouched — full v1 code, docs, and tests remain exactly where they are. Nothing archived, moved, or deleted.
- No architecture, stack, or scope decision for v2 has been made yet. This document is the marker of "here's where we stopped," not a proposal for where to go next.
- Related but separate: `DigitalBrainDump/` is a small, still-functional standalone capture tool (HTML + Python script, JSON storage) — not part of the DeepCore codebase, but the same "frictionless capture" instinct from Era 0 lives there in working form today.

---

## Correction — DeepCore itself is not retired

Follow-up from Deepak: only Era 0 (the "Digital Brain" design docs + the standalone `DigitalBrainDump/` capture tool) is being set aside. **DeepCore is active WIP and is v2** — the plan is to rethink and clean up the existing engineering, reusing as much of it as genuinely earns its place, not to restart from zero.

First concrete v2 milestone (confirmed): a working assistant chat over the existing Notes folder and the saved YouTube "DeepCore" playlist, aware of the relationships between them, extensible to future connectors. Keep all three existing layers (Data / Ontology / Deep runtime stack) as foundation — nothing thrown away, sequencing = get it actually answering questions first.

Two concrete gaps found once the code (not just the docs) was inspected:
1. `ConversationRuntime` had no LLM behind it — DIRECT mode literally echoed the message. **Fixed** in this pass: wired to a local Ollama model via `deepcore/intelligence/llm_client.py`, grounded in the Context Engine + full note-body content search. See `ROADMAP.md` Phase 17.0.
2. The YouTube provider only ever captured title/channel metadata, never the transcript (`"transcript_placeholder": "Transcript sync pending..."` was a literal placeholder, never implemented). **Not yet fixed** — tracked as Phase 17.1. Until this lands, the assistant can associate a note with a video by title but can't answer questions about what the video actually says.

---

## Open questions for defining v2

Not answered here — flagging them so the next conversation starts from the real fork points instead of re-litigating v1's choices by accident:

1. Build order: prove the daily-use experience first and grow the engine underneath it, or keep some form of engine-first discipline but scope it much smaller?
2. How much of Era 1's code is a foundation to build on vs. a reference to consult while writing something leaner?
3. Platform: is "future native-ready, API-first" still a requirement, or was that premature given there's no user beyond you yet?
4. Scope of v2's first milestone — what's the smallest version that you'd actually use every day?

# 🧠 DeepCore Engineering Directives (Claude, Cline, Cursor, Windsurf)

> **Platform**: DeepCore (Personal Intelligence OS & Deterministic Bridge)  
> **Repository**: `DeepCore`  
> **Master Spec**: `~/Documents/Notes/AI/Specs/Spec - DeepCore (Personal Intelligence Platform).md`

---

## 💬 1. Communication & Demeanor
- **Tone**: Zero sycophancy, zero empty praise. Concise, direct, critically analytical.
- **Priority**: System stability, deterministic execution, and privacy first.

---

## 🎓 2. Cognitive Apprenticeship & Epistemic Protocol (Vichar)
- **Option A Micro-Anchors**: When writing or refactoring code/connectors/schemas, provide a compact 3-bullet "Under the Hood" anchor:
  1. *The Mechanism*: How the OS, Python runtime, SQLite, or network executes it.
  2. *Why Not Alternative*: The rejected design pattern and failure mode it avoids.
  3. *The Invariant Law*: The foundational architectural rule (e.g. deterministic kernel vs probabilistic LLM).
- **Epistemic Self-Inquiry (Neti-Neti)**: Differentiate Hard Facts from Assumptions; surface "Why Not".
- **Mastery Tracking**: Log new CS patterns to `~/Documents/Notes/AI/Learning/Mastery Ledger.md`.

---

## 🛡️ 3. Pre-Flight Architecture Invariants
- **Layer Separation**: DeepCore is an integration orchestrator, NOT a replacement for external sources of truth (Obsidian, Qdrant, SQLite).
- **Connector Invariant**: Do NOT create a separate `LiveConnector` hierarchy. Extend `BaseConnector` supporting both batch and stateless execution surfaces.
- **Pre-Mortem**: Surface failure modes before implementing new services or schemas.

---

## 🧠 4. Universal Memory
- Read and log decisions via `mem0-local` (port 8765): `user_id: user`, `app: Claude`.

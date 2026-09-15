---
Category: Architecture
Status: Stable
Dependencies: []
Source-of-truth: True
---

# DeepCore Product Vision

Version: v0.1  
Status: Design Foundation

---

# V2 Addendum (2026-08-22) — Reframed, Not Replaced

The original vision below is preserved as-written for history. This addendum is the current, operative interpretation of it, arrived at after a full retrospective on why v1's engineering-depth-first approach stalled before producing anything usable. See `.ai/governance/RETROSPECTIVE_AND_V2_KICKOFF.md` and `.ai/governance/V2_EXECUTION_PLAN.md` for the reasoning and the concrete task breakdown.

**The one-sentence version: a private, local, evidence-grounded Jarvis over your own knowledge — that eventually acts, not just answers.**

What changes from the original framing:

- **"Personal operating system" is deliberately narrowed for now.** The original vision's scope (finance, email, calendar, full plugin ecosystem) is not abandoned, but it's explicitly not the near-term target. Scope expands one proven data source at a time (notes now, video next), not all at once.
- **Chat is the front door, not one of five equal navigation items.** The Home/Memory/Graph/Assistant/More navigation model in the original vision is still structurally reasonable, but in practice the assistant should be what you open first, with the other surfaces as secondary inspection tools (verify what it's citing, browse the graph if curious) rather than places you navigate to daily.
- **The deterministic kernel principle still holds and still matters**: Registry, Context Engine, and retrieval must stay deterministic; the LLM is the one permitted probabilistic seam, used only to turn retrieved context into a natural-language answer. This was true in v1 and remains true.
- **Action-taking is real, just deliberately deferred.** The Planner/Tool/Skill/Execution runtime stack built in v1 is not being extended further right now, but it is not being discarded either — it's the mechanism by which a future Jarvis moves from "answers questions" to "does things" (reminders, filing, triggering syncs). It gets picked back up when there's a concrete action use case to build against, not before.
- **Architecture-before-features, tempered.** v1's stall came substantially from building deep, well-engineered infrastructure years ahead of anything that touched daily use. v2 still values architectural integrity, but every increment must prove itself usable before the next layer gets built on top of it.

---

# North Star

DeepCore is a private personal intelligence system.

It is not a notes app.
It is not a file manager.
It is not a chatbot.

DeepCore is a memory layer that understands:

- What exists
- What it contains
- How things connect
- How to retrieve it when needed

The interface should feel like a personal assistant connected to a personal knowledge graph.

---

# Interaction Model v0.3

DeepCore does not use traditional application pages as the primary experience.

DeepCore uses a persistent personal intelligence workspace.

The user journey is:

Capture
→ Remember
→ Understand
→ Act

not:

Navigate
→ Open modules
→ Manage data


## Primary Experience Surfaces

DeepCore has three adaptive surfaces:

### 1. Memory Universe

Purpose:
Navigate everything the user has collected.

Contains:
- knowledge spaces
- source hierarchy
- object discovery
- extensions/providers

Examples:
Notes, videos, documents, GitHub, calendar, finance.


### 2. Conscious Workspace

Purpose:
The main thinking and interaction surface.

This is the center of DeepCore.

Contains:
- personalized home intelligence
- greetings and continuation points
- object explorer
- rich markdown reading
- artifact rendering
- graph exploration
- future interactive content


### 3. Context Intelligence

Purpose:
AI reasoning layer connected to current context.

Contains:
- assistant conversation
- object-aware actions
- explanations
- memory retrieval
- tool usage


Rules:

- The center workspace always owns the main user attention.
- Do not create separate desktop pages for Memory, Graph, or Assistant.
- These are modes inside the same intelligence workspace.
- Desktop expands available surfaces.
- Mobile transitions between the same surfaces.

The architecture must remain compatible with:
- Web/PWA
- iOS native
- Android native
- Desktop clients
---

# Product Principles

## 1. Mobile First

All design decisions start from the smallest device.

Priority:

1. Phone
2. Tablet
3. Desktop

Desktop adds space.
Desktop does not add complexity.

---

## 2. Future Native Ready

The UI must never contain business logic.

Architecture:

DeepCore Engine
        |
REST/API Contract
        |
UI Clients

Possible clients:

- Web/PWA
- iOS native
- macOS native
- Android native

The UI is replaceable.

The memory engine is permanent.

---

# Core Object Philosophy

Everything inside DeepCore is an object.

Examples:

- Markdown note
- YouTube video
- PDF
- Project
- Repository
- Person
- Concept
- Transaction

Every object follows:

```json
{
  "id": "",
  "type": "",
  "title": "",
  "source": "",
  "content": "",
  "concepts": [],
  "relationships": []
}
```

The interface should render objects dynamically.

Avoid creating separate screens for every source.

---

# Navigation Model

Maximum five primary areas.

Suggested:

## Home

Daily intelligence view.

Shows:

- Recent memories
- Important connections
- Suggested actions

---

## Memory

Object browser.

Search and filter all stored knowledge.

---

## Graph

Visual exploration layer.

Graph should NOT load everything.

Graph starts from context.

Example:

Open:
Ollama

Shows:

Docker
Python
RAG
Local AI

Expand manually.

---

## Assistant

Conversation interface.

Assistant can:

- Search memory
- Explain objects
- Compare knowledge
- Find connections

The assistant is powered by context.

---

## More

Settings, providers, extensions.

---

# Assistant Philosophy

Assistant is everywhere.

But assistant is not the whole product.

Examples:

Inside note:

"Ask about this"

Inside graph:

"Explain this connection"

Inside project:

"What changed?"

---

# Graph Rules

Avoid:

Huge meaningless network visualization.

Prefer:

Context expansion.

User controls exploration.

Initial depth:

1-2 relationship levels.

---

# Plugin / Provider Vision

DeepCore grows through providers.

Examples:

- Markdown provider
- YouTube provider
- GitHub provider
- Browser provider
- Email provider
- Finance provider

Providers create objects.

They do not create UI screens.

---

# Component System

Build components before pages.

Required core components:

- ObjectCard
- ObjectDetail
- ConceptChip
- RelationshipView
- GraphPreview
- Timeline
- AssistantPanel
- SearchCommand

Pages are compositions of components.

---

# Theme Rules

Dark mode and light mode from day one.

Never hardcode colors.

Use tokens:

background.primary

surface.card

text.primary

accent.primary

border.default

---

# Visual Direction

Inspired by:

- Apple simplicity
- ChatGPT assistant flow
- Obsidian graph thinking
- Raycast command model
- Arc browser minimalism

The product should feel:

Calm.

Intelligent.

Fast.

Personal.

---

# Development Rules For AI Agents

Do not create random dashboards.

Do not create source-specific UI.

Do not duplicate components.

Respect mobile layout first.

Respect existing backend concepts.

Before implementing UI:

1. Define component
2. Define API contract
3. Implement screen

---

# Long Term Vision

DeepCore becomes a personal operating system layer.

Local first.

Private.

Extensible.

AI enhanced.

User owned.
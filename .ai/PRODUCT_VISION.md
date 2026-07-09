# DeepCore Product Vision

Version: v0.1  
Status: Design Foundation

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
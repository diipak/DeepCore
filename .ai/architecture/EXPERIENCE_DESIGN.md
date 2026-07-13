---
Category: Architecture
Status: Approved
Dependencies: [governance/PRODUCT_VISION.md]
Source-of-truth: True
---

# DeepCore Experience Design v0.1

## Product Philosophy

DeepCore is not a file manager.
DeepCore is not a notes application.
DeepCore is not an admin dashboard.

DeepCore is a personal intelligence interface.

The user experience should feel like exploring a living knowledge system.
The interface should hide database complexity and expose:
- memories
- concepts
- relationships
- insights
- conversations

---

## Core Experience Principles

### 1. Calm Intelligence
The interface should feel:
- focused
- premium
- quiet
- trustworthy

**Avoid**:
- crowded dashboards
- excessive metrics
- developer/admin appearance

The user should feel:
> "I am exploring my own knowledge"

not:
> "I am managing records"

---

### 2. Mobile First
Design priority:
1. **Mobile**
2. **Tablet**
3. **Desktop**

Every screen must work naturally on phone dimensions.

**Rules**:
- touch friendly controls
- bottom navigation preferred on mobile
- no information-dense tables
- no hover-only interactions
- cards over grids
- progressive disclosure

Desktop should expand the experience, not define it.

---

### 3. Native App Future Compatibility
The UI architecture should allow future:
- iOS native app
- Android native app

**Avoid**: web-only assumptions.

**Do not couple**:
- API logic
- UI components
- animations
- platform features

DeepCore API remains the source of truth.

---

## Visual Direction
Inspired by:
- modern AI assistants
- knowledge graph explorers
- Apple-style clarity
- futuristic interfaces without complexity

The experience combines:
- Assistant
- Knowledge Graph
- Personal Library

---

## Theme System
Dark and light modes are first-class.
Never design only one mode.

**Rules**:
- no hardcoded colors
- token-based themes
- semantic colors only

**Examples**:
- **Good**:
  - `background.primary`
  - `surface.card`
  - `text.primary`
  - `accent.glow`
- **Bad**:
  - `#000000`
  - `white`
  - `blue-500` everywhere

---

## Main Screens v0.1

### 1. Home (Core)
- **Powered by**: `GET /api/dashboard`
- **Purpose**:
  > "Show me my knowledge health"
- **Contains**:
  - memory summary
  - concept summary
  - relationship summary
  - top concepts
  - recent memories
- **Avoid**: analytics dashboard feeling.

### 2. Memory Explorer
- **Powered by**: `/api/memories` & `/api/content/search`
- **Purpose**: Find things the user stored.
- **Experience**: Search first. Objects shown as memory cards. Not tables.

### 3. Knowledge Graph
- **Powered by**: `/api/concepts`
- **Purpose**: Visualize connected thinking.
- **Visuals**: Concepts are nodes, relationships are connections.
- **Layouts**: Must work in both a full graph view and a simplified mobile list view.

### 4. Assistant Space
- **Powered later by**: `/api/assistant` (current placeholder only)
- **Experience goal**: A conversation with the user's own knowledge.
- **Assistant References**: Should cite memories, concepts, and sources.

---

## Component Philosophy
- **Prefer**: Memory Card
  - *Title*: Docker RAG System
  - *Metadata*: Note • 2026
  - *Connections*: Ollama, Python, AI
- **Avoid**: Database rows (e.g. `ID | TYPE | CREATED_AT | UUID`)

---

## Navigation
- **Mobile**: Bottom navigation (Home, Memory, Graph, Assistant)
- **Desktop**: Adaptive sidebar allowed.

---

## Animation Rules
Use motion carefully.
- **Allowed**: smooth transitions, graph movement, subtle depth.
- **Avoid**: distracting effects, slow animations, unnecessary futuristic effects.

---

## Forbidden UI Patterns
Do not create:
- ❌ Admin panels
- ❌ CRUD dashboards
- ❌ Database browsers
- ❌ Spreadsheet-like interfaces
- ❌ Developer console UI

---

## Phase 6 Implementation Rule
During DeepCore Shell v0.1:
- **Allowed**: UI components, layouts, responsiveness, API consumption.
- **Not allowed**: new AI features, database changes, backend redesign, new intelligence layers.
- **Goal**: Make the existing DeepCore intelligence understandable and enjoyable.


# Visual System v0.2

DeepCore follows Calm Intelligence design.

The interface must feel like:
- Apple Notes clarity
- Obsidian knowledge navigation
- NotebookLM contextual intelligence
- Linear-level polish

It must NOT become:
- analytics dashboard
- admin console
- colorful productivity app


## Color Philosophy

Colors are semantic, not decorative.

Use muted pastel accents only.

Examples:

Memory:
soft mint / green tones

Concept:
soft violet tones

Assistant:
soft cyan/orchid tones

Warning:
warm amber

Avoid saturated primary colors.


## Theme System

Dark and light themes are first-class.

Components never hardcode colors.

Always use semantic tokens:

background.primary
surface.card
surface.elevated
text.primary
accent.memory
accent.concept
accent.assistant


## Glass Usage Rules

Glass effects are premium surfaces only.

Allowed:
- Assistant panel
- floating command palette
- contextual overlays
- mobile sheets

Forbidden:
- every card
- every button
- long reading surfaces


Readability always beats visual effect.

DeepCore is not:
- file manager
- chatbot
- notes app

DeepCore is:
Personal intelligence workspace.

Primary interaction:
Memory → Understanding → Action

Layout:
Memory Universe
Conscious Workspace
Context Intelligence



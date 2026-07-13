# DeepCore UI Architecture

Version: v0.1  
Status: UI Foundation Contract

---

# Purpose

This document defines how DeepCore interfaces are built.

Goal:

One intelligence engine.
Multiple possible clients.

- Web
- PWA
- iOS
- Android
- Desktop

UI must remain replaceable.

---

# Architecture Principle

DeepCore follows:

Backend owns intelligence.

Frontend owns experience.

Never mix.

```
DeepCore Engine

Registry
Content
Concepts
Relationships
Assistant

        |

API Layer

        |

Clients

Web
Mobile
Native Apps
```

---

# Client Strategy

Initial client:

Responsive Web / PWA

Future clients:

- Swift iOS app
- Android app
- Desktop app

Therefore avoid:

- Browser-only assumptions
- DOM-dependent logic
- LocalStorage as core storage
- UI-owned business rules

---

# Design System First

Never build pages first.

Build:

1. Tokens
2. Components
3. Layouts
4. Screens

---

# Responsive Rules

Mobile is default.

Breakpoints:

Mobile:
0-767px

Tablet:
768-1199px

Desktop:
1200px+

Desktop expands information density.

It does not introduce different workflows.

---

# Core Layout

Mobile:

```
Header

Content

Bottom Navigation
```

Desktop:

```
Sidebar

Main Content

Optional Context Panel
```

Same features.
Different layout.

---

# Navigation

Maximum primary areas:

Home

Memory

Graph

Assistant

More

No nested menu complexity.

---

# Component Contract

## ObjectCard

Displays any RegistryObject.

Supports:

note
video
concept
project
repository
future providers

Must not contain source-specific logic.

---

## ObjectDetail

Universal detail screen.

Sections:

Overview

Content

Concepts

Relationships

Actions

---

## ConceptChip

Displays concepts.

States:

candidate
approved
ignored

Visual difference only.

Logic stays backend.

---

## RelationshipView

Shows object connections.

Input:

source object

relationship list

Output:

human readable connections.

---

## GraphView

Rules:

Never load entire graph.

Always starts with:

selected object

+

nearest relationships

User expands manually.

---

## AssistantPanel

Chat interface.

Can receive context:

object_id

concept_id

current_view

Assistant should understand where user is.

---

# Data Flow

Correct:

```
User Action

↓

API Request

↓

Backend Logic

↓

Response

↓

UI Render
```

Wrong:

```
UI calculates relationships

UI creates concepts

UI modifies intelligence rules
```

---

# State Management Rules

UI state:

Allowed:

- opened panels
- selected filters
- theme
- navigation

Not allowed:

- object truth
- relationships
- extracted concepts

---

# Theme System

Required from first commit.

No direct colors.

Forbidden:
- #ffffff
- black
- saturated neon primaries

Allowed Functional Semantics (Semantic Pastel System):
- background.primary / surface.card: Neutral, dark/calm surfaces.
- `--accent-memory`: Soft blue (Markdown notes, documents, memory lists).
- `--accent-concept`: Soft violet (Ontology concepts, tags, relationship graphs).
- `--accent-assistant`: Soft cyan (AI status, intelligence headers, chat context).
- `--accent-action`: Soft green (Growth, success states, sync success, enabled actions).
- `--accent-warning`: Soft amber (Warnings, attention states, candidate status).
- `--accent-important`: Soft rose (Emotional/personal metadata tags).
- `--accent-video`: Soft red (Videos, YouTube source integrations).

---

# Animation Rules

Animations support understanding.

Allowed:

- graph expansion
- assistant thinking
- transitions

Avoid:

- decorative animations
- distracting motion

---

# Offline / Local First

Design assumes:

Internet may not exist.

DeepCore engine may run locally.

Assistant may be:

Local model

or

Cloud model

UI should not care.

---

# AI Integration Future

Assistant providers are replaceable.

Examples:

Local:
Ollama

Cloud:
External API

Hybrid:
Both

Frontend talks only to DeepCore assistant API.

---

# Extension Future

Plugins create:

Objects

Metadata

Actions

Plugins do NOT create:

Navigation tabs

Custom dashboards

Separate applications

---

# UI Quality Rules

Every screen must pass:

Phone

Tablet

Desktop

Light mode

Dark mode


before considered complete.

---

# Agent Development Rules

Before implementing UI:

1. Check PRODUCT_VISION.md
2. Check UI_ARCHITECTURE.md
3. Create reusable component
4. Connect API
5. Test responsive behavior

Avoid quick CSS patches.

Fix design system problems instead.

---

# Target Feeling

DeepCore should feel like:

A calm personal intelligence companion.

Not an admin dashboard.

Not a database viewer.

Not a developer tool.



# Workspace Navigation v0.2

DeepCore does not use fixed app pages.

It uses expandable spaces.


Navigation Example:

Knowledge
  Memories
  Notes
  Videos
  Concepts

Intelligence
  Graph
  Assistant

Extensions
  Installed extensions appear here


Rules:

- Navigation tree supports unlimited depth.
- Extensions register themselves into navigation.
- Shell must not hardcode future modules.


Desktop:

Memory Universe
|
Conscious Workspace
|
Context Intelligence


## Memory Universe

Left adaptive surface.

Responsibilities:
- navigation tree
- sources
- spaces
- extensions

Can collapse when space is limited.


## Conscious Workspace

Primary flexible surface.

Responsibilities:
- home intelligence
- object browsing
- object detail
- markdown rendering
- artifacts
- graph exploration

The explorer and artifact viewer are states of the same workspace.

Do not permanently split them into separate desktop columns.


## Context Intelligence

Right adaptive surface.

Responsibilities:
- assistant
- reasoning
- contextual actions

Rules:
- Resizable like an IDE assistant panel:
  - Drag handle on the left border.
  - Sizing limits: min width 280px, default 360px, max width 600px.
  - Width state is persisted in `localStorage` under `deepcore_assistant_width`.
- Collapsible using the workspace-wide toggle button.
- Receives current workspace context (selected object ID or concept name).
- Mobile layout disables resizing, fitting full width.


Mobile:

Same architecture.

Only presentation changes:

Memory Universe
→ Conscious Workspace
→ Context Intelligence

No separate mobile experience.




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

#ffffff

black

red

blue

Allowed:

background.primary

text.primary

surface.card

accent.primary

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

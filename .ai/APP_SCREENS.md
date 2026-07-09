# DeepCore Application Screens

Version: v0.1  
Status: Product Blueprint

---

# Purpose

This document defines the core user experience of DeepCore.

The goal is to translate:

Registry + Content + Concepts + Relationships + Assistant

into a simple daily-use application.

The interface should hide complexity.

---

# Core Navigation

DeepCore has five main areas:

1. Home
2. Memory
3. Graph
4. Assistant
5. More

No additional primary tabs without architectural review.

---

# Screen 1 — Home

## Purpose

The command center.

Answer:

"What matters right now?"

Not:

"Show everything stored."

---

## Layout

Mobile:

```
Greeting

Memory Summary

Continue Section

Suggested Connections

Quick Actions
```

Desktop:

```
Left:
Navigation

Center:
Daily Memory View

Right:
Context / Assistant
```

---

## Components

### Memory Summary

Shows:

```
Memories

Concepts

Connections

Sources
```

Example:

```
1,240 memories

350 concepts

4,800 links

7 providers
```

---

### Continue Section

Recently touched knowledge:

Examples:

```
DeepCore UI Planning

Ollama Setup

FinSync Architecture
```

---

### Intelligence Suggestions

Future feature.

Examples:

```
"You have 3 notes about local AI"

"Python and Ollama appear connected often"

"This project has not been updated recently"
```

---

### Quick Actions

Required:

Capture

Ask

Search

Create

---

# Screen 2 — Memory

## Purpose

Universal object explorer.

Not a file browser.

---

## Views

Supports:

List

Cards

Timeline

---

## Filters

By:

Type

Source

Concept

Date

Status

---

## Object Card

Example:

```
Ollama Local Setup

Type:
Note

Concepts:
AI
Docker
Python

Connections:
12
```

---

# Screen 3 — Object Detail

## Purpose

Every memory has one universal page.

No source-specific pages.

---

## Sections

Header:

```
Title

Type

Source

Status
```

---

Content:

Original indexed information.

Examples:

Markdown text

Video metadata

PDF text

Future objects

---

Concept Area:

Shows extracted concepts.

Example:

```
Ollama

Docker

Python

RAG
```

---

Relationships:

Shows:

```
Connected memories

Related projects

Similar concepts
```

---

Actions:

```
Ask about this

Open source

Explore graph
```

---

# Screen 4 — Graph Explorer

## Purpose

Visual thinking layer.

Not decoration.

---

# Important Rule

Never load the entire knowledge graph.

Always start with context.

---

Example:

Open concept:

Ollama


Shows:

```

        Docker


Python — Ollama — RAG


       Local AI

```

---

## Interaction

Tap node:

Expand one level.

Hold node:

Show actions.

---

## Modes

Memory Graph

Concept Graph

Project Graph

---

# Screen 5 — Assistant

## Purpose

Conversation with personal knowledge.

---

# Assistant Philosophy

The assistant does not replace the UI.

It enhances it.

---

## Default Mode

User:

"What was that Docker project I saved?"

Assistant:

Uses:

Registry

Content Index

Concepts

Relationships

---

## Context Mode

From Object:

"Ask about this"

passes:

```
object_id
concepts
relationships
content
```

---

# Screen 6 — Capture

## Purpose

Fast memory creation.

---

Supported:

Current:

Markdown

YouTube


Future:

PDF

Webpage

GitHub

Email

Calendar

Finance

---

Flow:

```
Paste / Share

↓

DeepCore understands source

↓

Creates object

↓

Indexes content

↓

Extracts concepts

↓

Creates relationships

```

---

# Screen 7 — Plugins / Extensions

## Purpose

Allow DeepCore growth.

---

Providers:

Examples:

YouTube

GitHub

Google Drive

Gmail

Finance

Browser

---

Rules:

Plugins add capabilities.

Plugins do not redesign DeepCore.

---

# Empty States

Important.

Never show:

"No data"

Instead:

Examples:

"No memories yet. Capture your first idea."

"Graph will appear when connections exist."

---

# Mobile Experience Rules

Must work one-handed.

Important actions:

Bottom area.

Avoid:

Tiny controls.

Large tables.

Complex menus.

---

# Desktop Experience Rules

Use additional space for context.

Example:

Memory list

+

Selected object

+

Assistant panel


Not more complexity.

---

# Native App Future Rules

Screens should map directly to native views.

HomeView

MemoryView

ObjectView

GraphView

AssistantView


Avoid web-only concepts.

---

# MVP Build Order

Do NOT build everything.

Order:

## Phase UI-1

Home

Memory list

Object detail


## Phase UI-2

Assistant integration

Capture


## Phase UI-3

Graph explorer


## Phase UI-4

Plugins

Native clients

---

# Success Definition

DeepCore succeeds when:

User does not think:

"Where did I store it?"

User asks:

"What do I know about this?"

and DeepCore answers.

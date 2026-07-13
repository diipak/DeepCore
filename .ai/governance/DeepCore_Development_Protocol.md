---
Category: Governance
Status: Stable
Dependencies: []
Source-of-truth: True
---

# DeepCore Development Protocol

Version: v1.0
Status: Source of Truth
Audience: Human Architects, AI Engineering Assistants, Future Contributors

---

# Purpose

This document defines the engineering process used to evolve DeepCore.

It is intentionally independent of any individual AI assistant or conversation.

The objective is to ensure that architectural quality, consistency, and long-term maintainability remain identical regardless of which implementation assistant is being used.

This document is considered a permanent Source of Truth.

---

# DeepCore Philosophy

DeepCore is an Operating System for Personal Intelligence.

It is **not**:

- a chatbot
- an AI demo
- a prompt collection
- an automation workflow

Everything inside DeepCore exists to support one objective:

> Build a deterministic, extensible, local-first operating system capable of understanding, organizing, reasoning over, and acting upon a user's personal knowledge.

---

# Engineering Principles

Every implementation must preserve the following principles.

## 1. Architecture Before Features

Features are temporary.

Architecture is permanent.

No implementation may sacrifice architectural integrity simply to obtain visible progress.

Visible functionality is important, but never at the cost of long-term flexibility.

---

## 2. Deterministic Kernel

Everything below the LLM layer must be deterministic.

The following components must never depend on probabilistic reasoning:

- Registry
- Context Engine
- Planner Runtime
- Execution Runtime
- Skill Runtime
- Tool Runtime

These components must always produce identical outputs for identical inputs.

---

## 3. Layer Separation

Each layer owns one responsibility.

Conversation Runtime

↓

Prompt Composer

↓

LLM Adapter

↓

Planner Runtime

↓

Execution Runtime

↓

Skill Runtime

↓

Tool Runtime

↓

Providers

↓

Registry

No layer may bypass another simply for convenience.

No layer should import responsibilities belonging to another.

---

## 4. Infrastructure Agnostic Design

Components communicate only through stable contracts.

No implementation may introduce unnecessary coupling.

Examples:

- Conversation Runtime must not know specific Skills.
- Planner must not call Tools directly.
- Skills must not manipulate databases directly when a Tool exists.
- Prompt Composer must not know provider implementations.

---

## 5. Everything is Replaceable

Every component should be replaceable without affecting the rest of the system.

This includes:

- Models
- Prompt strategies
- Providers
- Skills
- Tools
- Frontend

DeepCore must never become dependent on a specific vendor.

---

# Descriptor Principle

Every capability inside DeepCore must be self-describing.

Every major component should expose a Descriptor.

Examples:

- ToolDescriptor
- SkillDescriptor
- ProviderDescriptor
- ModelDescriptor
- ConversationDescriptor
- PromptDescriptor

Descriptors are metadata.

Execution logic must remain separate.

---

# Frontend Philosophy

The frontend is not hardcoded.

The frontend discovers capabilities dynamically.

It should never assume:

- installed providers
- installed models
- available skills
- available tools

Instead it queries descriptors and renders what exists.

This allows DeepCore to evolve without frontend rewrites.

---

# Source of Truth Hierarchy

When conflicts exist, resolve them using the following order.

1. Manifesto
2. CURRENT_STATE.md
3. Architecture Design Documents
4. Development Protocol
5. Implementation Walkthroughs
6. Source Code

Implementation must never silently contradict higher-level documents.

---

# Development Workflow

Every implementation phase follows the same lifecycle.

---

## Step 1

Review the current architecture.

Understand the current state before proposing changes.

---

## Step 2

Think ahead.

Review at least the next two or three planned phases.

Avoid introducing decisions that create future architectural debt.

---

## Step 3

Architecture Review.

Identify:

- coupling
- missing abstractions
- API concerns
- extensibility risks
- deterministic violations

If no concerns exist, explicitly state that the architecture remains valid.

---

## Step 4

Produce an AG Implementation Prompt.

Every implementation phase ends with a single copy-paste Markdown block.

This block becomes the implementation contract.

It must contain:

- objective
- user review
- proposed changes
- verification plan

No implementation discussion should replace this block.

---

## Step 5

Implementation.

AG performs implementation.

---

## Step 6

Walkthrough Review.

The completed implementation is reviewed against:

- architecture
- previous phases
- long-term roadmap

Approval or refinements are produced.

---

## Step 7

Repeat.

---

# Architectural Reviews

Reviews are expected to challenge existing proposals.

Agreement is not the goal.

Correctness is.

Counterarguments are encouraged when they improve DeepCore.

Every decision should survive engineering scrutiny rather than personal preference.

---

# Documentation Rules

Every major architectural milestone must produce documentation.

Architecture exists outside conversations.

Conversations are temporary.

Documentation is permanent.

Whenever practical:

- update CURRENT_STATE.md
- update architecture documents
- update diagrams
- preserve design rationale

---

# AI Collaboration

DeepCore intentionally uses multiple AI systems.

Each AI has a different responsibility.

For example:

- Architecture review
- Implementation
- Research
- Documentation

No assistant should become a single source of truth.

The repository is the source of truth.

---

# Success Criteria

Success is not measured by:

- lines of code
- number of phases
- number of prompts

Success is measured by whether the resulting system remains understandable, deterministic, extensible, and capable of evolving for many years.

---

# Closing Principle

Protect the architecture.

Everything else can be rewritten.

---

# Final Rule

Whenever a decision exists between:

- making the current implementation easier

or

- making the future architecture cleaner

prefer the cleaner architecture unless there is objective evidence that doing so would materially harm the project.

DeepCore is intended to evolve over many years.

Every implementation should be evaluated from that perspective.

## Step 0

Synchronize Project State.

Before reviewing architecture:

- Review the latest walkthrough.
- Review CURRENT_STATE.md.
- Review the Development Protocol.
- Determine exactly which phase has just been completed.
- Identify the next planned phase before proposing any work.

Never restart architectural discussions from memory alone.
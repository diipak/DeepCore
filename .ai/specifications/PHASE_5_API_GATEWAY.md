---
Category: Specification
Status: Approved
Dependencies: [architecture/ARCHITECTURE.md]
Source-of-truth: True
---

# Implementation Plan - API Gateway Layer v0.1

Implement Phase 5 — API Gateway Layer.

Expose existing DeepCore intelligence capabilities through stable HTTP APIs.

No new intelligence features should be created.

This phase converts existing CLI-accessible functionality into product-ready APIs for:

- Web UI
- PWA
- Future native mobile applications

---

# Architecture Rule

FastAPI is an interface layer only.

Do NOT duplicate business logic.

Correct:

API Route
    ↓
Existing Service
    ↓
Database


Wrong:

API Route
    ↓
New SQL logic

---

# API Structure

Create:

deepcore/api/routes/

with:

- registry.py
- content.py
- concepts.py
- system.py

---

# Registry APIs

Expose memory objects.

## GET /api/objects

Purpose:

Memory explorer.

Supports:

query parameters:

- search
- type
- source
- limit

Uses:

RegistryService.search_objects()

---

## GET /api/objects/recent

Purpose:

Home screen recent section.

Uses:

RegistryService.recent_objects()

---

## GET /api/objects/{id_or_uuid}

Purpose:

Object detail screen.

Uses:

RegistryService.get_object_details()

---

# Content APIs

## GET /api/content/search

Parameters:

query

Uses:

ContentService.search_content()

---

## GET /api/content/{object_id}

Purpose:

Retrieve indexed object content.

Uses:

ContentService.get_content()

---

# Concept APIs

## GET /api/concepts

Purpose:

Concept browser.

Parameters:

- limit
- show_ignored

Uses:

ConceptService.list_concepts()

---

## GET /api/concepts/{name}

Purpose:

Concept detail screen.

Returns:

- concept metadata
- connected memories


Uses:

ConceptService.get_concept_by_name()

ConceptService.get_connected_memories()

---

## POST /api/concepts/{name}/approve

Body:

{
"type": "tool"
}

Uses:

ConceptService.approve_concept()

---

## POST /api/concepts/{name}/ignore

Uses:

ConceptService.ignore_concept()

---

# System APIs

## GET /api/stats

Purpose:

Home dashboard.

Returns:

- total objects
- objects by type
- objects by source
- concept count
- relationship count

---

# API Response Rules

Never return raw SQLAlchemy objects.

Create response schemas.

All responses must be JSON serializable.

---

# Native App Compatibility Rules

Avoid:

HTML

Markdown-only responses

CLI formatted text

Terminal formatting


Return structured JSON only.

---

# Testing

Create:

tests/test_api.py

Verify:

- object list endpoint
- object detail endpoint
- recent endpoint
- content search endpoint
- concepts endpoint
- stats endpoint

---

# Validation

Run:

pytest tests/

Expected:

All existing tests pass.

New API tests pass.

---

# Success Definition

DeepCore functionality available without CLI.

A future Swift/iOS app should theoretically be able to use every endpoint.


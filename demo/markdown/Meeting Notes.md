---
tags: [deepcore, meeting]
---
# DeepCore Team Sync — 2026-07-13

## Attendees
- Deepak (Product Owner)
- Antigravity (AI Architect)

## Agenda
1. Review of the Intelligence Pipeline architecture spec in [architecture/INTELLIGENCE_PIPELINE.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/.ai/architecture/INTELLIGENCE_PIPELINE.md).
2. Plan execution for Vertical Slice 1: Knowledge Ingestion Pipeline.
3. Set up the demo markdown folder for automated and manual verification.

## Decisions
- We will implement the first vertical slice focusing on deterministic Markdown ingestion only.
- Soft-deletes will mark missing files as `missing` instead of hard-deleting them.
- Providers will remain pure (normalizing only), and indexing will be triggered as a downstream event in the API gateway.

My tasks: [[Personal Tasks]]

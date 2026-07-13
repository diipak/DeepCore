# DeepCore Ingestion Demo Dataset

This directory contains a small, structured verification dataset for testing the DeepCore Knowledge Ingestion Pipeline.

## Files and Purpose

1.  **[Meeting Notes.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/demo/markdown/Meeting%20Notes.md)**:
    *   *Purpose*: Represents typical work/meeting logs containing lists, links, and action points.
    *   *Features*: Contains cross-references to the local `.ai/` documentation directory to test URI resolution.
2.  **[DeepCore Ideas.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/demo/markdown/DeepCore%20Ideas.md)**:
    *   *Purpose*: Represents unstructured brainstorming notes containing paragraphs and lists.
    *   *Features*: Mentions capability models and templates to verify simple keyword indexing.
3.  **[Architecture Thoughts.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/demo/markdown/Architecture%20Thoughts.md)**:
    *   *Purpose*: Structured notes containing sections and short paragraphs detailing system design.
    *   *Features*: Mentions time stamps and content hashes to test extraction metadata logic.
4.  **[Personal Tasks.md](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/demo/markdown/Personal%20Tasks.md)**:
    *   *Purpose*: Task checklist notes containing checkbox elements (`[x]` and `[ ]`).
    *   *Features*: Ideal for testing incremental modifications (e.g. checking off a task and verifying that the updated timestamp and content hash change deterministically on re-sync).

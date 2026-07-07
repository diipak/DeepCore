# Current State - DeepCore Registry MVP

## Completed Work

### Phase 1 Connectivity

1. **MarkdownProvider v0.1**: Built the Markdown notes discovery provider in [markdown.py](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/deepcore/core/providers/markdown.py) inheriting from `BaseProvider`.
   - **Exclusion Walks**: Walks directories recursively and prunes hidden paths (e.g. `.git/`, `.obsidian/`, `.trash/`) and files starting with `.`.
   - **Discovery details**: Extracts path coordinates, UTC ISO-8601 timestamps, and file sizes.
   - **Normalization**: Maps to Registry Object type `note`, source `markdown`, using stripped filenames for titles, relative paths for external IDs, and stores metadata parameters (including `root_path` to handle multiple workspaces).
   - **CLI command integration**: Added command `deepcore sync markdown <path>` producing scanned/new/existing statistics.
   - **Separation from Capture**: Strictly decoupled from Capture Layer to isolate batch sync collections from single intentional intake streams.

2. **Milestone: First complete user memory loop achieved**:
   - **Validated flow**:
     ```
     CLI
      ↓
     CaptureService
      ↓
     YouTubeProvider
      ↓
     RegistryService
      ↓
     SQLite
     ```
   - **Manual Verification**:
     - Captured a real YouTube URL: `deepcore capture "https://youtu.be/T33iI6izAKw?si=Kr_HcOxmHS3nQLVV"`
     - Listed stored objects: `deepcore list` (successfully listed the captured video)
     - Viewed registry statistics: `deepcore stats` (counted and categorized stored items)
   - **Known Limitation**: YouTube metadata extraction fallback was triggered.
   - **Future Improvement**: Evaluate a stronger or more resilient metadata provider.

3. **Capture Layer v0.1**: Built the universal intake layer for DeepCore in [service.py](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/deepcore/core/capture/service.py).
   - **Dynamic Provider Registry**: Decoupled routing logic by registering providers in a registry list (`PROVIDERS = [YouTubeProvider]`) and selecting the matching provider via the `can_handle()` class method, completely avoiding static if/else branching.
   - **Metadata Stamping**: Automatically post-processes objects passing through the Capture Layer to inject capture audit attributes (`captured_via="capture"` and ISO-8601 `captured_at` timestamp) into the `metadata_json` field without coupling providers to the Capture Layer.
   - **Endpoint**: Exposed `POST /capture` routing user payload content to the correct provider and registering (or retrieving duplicates) from the database.
   - **Duplication Integration**: Capturing an existing URL retrieves the existing object and updates the capture audit stamps rather than creating a duplicate.

4. **YouTubeProvider v0.1**: Built the first external provider in [youtube.py](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/deepcore/core/providers/youtube.py) inheriting from `BaseProvider`.
   - **URL Parser**: Parsed 11-character video IDs from standard watch URLs, short URLs, embed URLs, and shorts URLs.
   - **Isolated Metadata Scraper**: Added an isolated `extract_metadata` helper to match metadata (title, channel, thumbnail) from scraped page HTML. Supports both single and double quotes.
   - **Offline Fallback**: Handles network exceptions gracefully, falling back to a default title format: `"YouTube Video {video_id}"`.
   - **Audit Metadata**: Stamped a UTC ISO-8601 `captured_at` timestamp inside the object's `metadata_json`.
   - **Duplicate Handling**: Queries the database to prevent duplicate objects for matching `source_system="youtube"` and `external_id=video_id`.

5. **Automated Tests**:
   - Added [test_markdown_provider.py](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/tests/test_markdown_provider.py) verifying discovery details, folder walk exclusions, file normalization, and duplicate check sync stats.
   - Added [test_capture.py](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/tests/test_capture.py) verifying capture layer behaviors.
   - Added [test_youtube_provider.py](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/tests/test_youtube_provider.py) verifying URL formats.
   - Added [test_cli.py](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/tests/test_cli.py) updates verifying the Typer CLI `sync markdown` outputs and exit statuses.

---

## Active Capabilities

- **Markdown Local Syncing**: Ingests folders of notes batch-wise, keeping original paths, sizing, and OS timestamps intact.
- **Intake Capture**: Standardized `POST /capture` entry point routing URLs to active providers (e.g. YouTube).
- **YouTube Object Syncing**: Ingestion of raw YouTube video URLs with unauthenticated metadata scraping.
- **Database Path Configuration**: Configurable via `DEEPCORE_DB_PATH` environment variable.
- **Robust Testing Setup**: Automatic local DB generation (`test_deepcore.db`) with test execution isolation.

---

## Open Issues
- None.

---

## Next Recommended Step / Known Future Extensions

- **Obsidian Awareness Layer**:
  - Link discovery and parsing (`[[backlinks]]` and embeds)
  - Frontmatter metadata extraction (YAML/JSON block parse)
  - Obsidian tags extraction
  - Obsidian Canvas files parsing
- **Registry Relationship Management**:
  - Implement association layer endpoints (`registry_relationships` CRUD operations) to connect notes and videos.

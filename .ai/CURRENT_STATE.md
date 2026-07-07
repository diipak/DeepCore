# Current State - DeepCore Registry MVP

## Completed Work

### Phase 1 Connectivity
1. **Capture Layer v0.1**: Built the universal intake layer for DeepCore in [service.py](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/deepcore/core/capture/service.py).
   - **Dynamic Provider Registry**: Decoupled routing logic by registering providers in a registry list (`PROVIDERS = [YouTubeProvider]`) and selecting the matching provider via the `can_handle()` class method, completely avoiding static if/else branching.
   - **Metadata Stamping**: Automatically post-processes objects passing through the Capture Layer to inject capture audit attributes (`captured_via="capture"` and ISO-8601 `captured_at` timestamp) into the `metadata_json` field without coupling providers to the Capture Layer.
   - **Endpoint**: Exposed `POST /capture` routing user payload content to the correct provider and registering (or retrieving duplicates) from the database.
   - **Duplication Integration**: Capturing an existing URL retrieves the existing object and updates the capture audit stamps rather than creating a duplicate.
2. **YouTubeProvider v0.1**: Built the first external provider in [youtube.py](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/deepcore/core/providers/youtube.py) inheriting from `BaseProvider`.
   - **URL Parser**: Parsed 11-character video IDs from standard watch URLs, short URLs, embed URLs, and shorts URLs.
   - **Isolated Metadata Scraper**: Added an isolated `extract_metadata` helper to match metadata (title, channel, thumbnail) from scraped page HTML.
   - **Offline Fallback**: Handles network exceptions gracefully, falling back to a default title format: `"YouTube Video {video_id}"`.
   - **Audit Metadata**: Stamped a UTC ISO-8601 `captured_at` timestamp inside the object's `metadata_json`.
   - **Duplicate Handling**: Queries the database to prevent duplicate objects for matching `source_system="youtube"` and `external_id=video_id`.
3. **Automated Tests**:
   - Added comprehensive integration tests in [test_capture.py](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/tests/test_capture.py) verifying dynamic routing, capture metadata injection, HTTP API status codes, and duplicate handling.
   - Added unit tests in [test_youtube_provider.py](file:///Users/deepakbatham/Documents/DocsN_all/Project/DeepCore/tests/test_youtube_provider.py) verifying URL parsing, offline fallbacks, and duplicate checks.

### Registry MVP Foundation (Phase 0)
1. **FastAPI Structure**: Initialized package layout under `deepcore/`.
2. **SQLite Database Schema**: Implemented `registry_objects` and `registry_relationships` tables containing flexible fields like `metadata_json` and `provider_version`.
3. **RegistryService**: Completed CRUD services supporting fetch by ID or UUID.
4. **Provider Interfaces**: Implemented `BaseProvider` and the operational `ManualProvider`.
5. **REST API**: Established `GET /objects`, `POST /objects`, and `GET /objects/{id_or_uuid}` endpoints.

---

## Active Capabilities

- **Intake Capture**: Standardized `POST /capture` entry point routing URLs to active providers (e.g. YouTube).
- **YouTube Object Syncing**: Batch syncing of raw YouTube video URLs, complete with unauthenticated metadata extraction.
- **Database Path Configuration**: Configurable via `DEEPCORE_DB_PATH` environment variable.
- **Provider Normalization**: Seamless mapping of manual and YouTube payloads into strict database schemas.
- **Robust Testing Setup**: Automatic local DB generation (`test_deepcore.db`) with test execution isolation.

---

## Open Issues
- None.

---

## Next Recommended Step
- Implement relationship management between objects (e.g. associating a YouTube video to a note/project object via `registry_relationships`).

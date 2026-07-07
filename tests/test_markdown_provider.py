import json
import os
from datetime import datetime, timezone
import pytest

from deepcore.core.providers.markdown import MarkdownProvider
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import ObjectType

def test_markdown_discovery_and_exclusions(staged_notes_dir):
    """Verify that MarkdownProvider discovers only valid markdown files and ignores hidden paths."""
    provider = MarkdownProvider(root_path=staged_notes_dir)
    discovered = provider.discover()
    
    # Must only discover: note1.md, note2.MD, and nested/note3.md
    assert len(discovered) == 3
    
    filenames = {item["filename"] for item in discovered}
    assert filenames == {"note1.md", "note2.MD", "note3.md"}
    
    # Check details for nested note3.md
    note3_item = next(item for item in discovered if item["filename"] == "note3.md")
    assert note3_item["relative_path"] == os.path.join("nested", "note3.md")
    assert note3_item["parent_folder"] == "nested"
    assert note3_item["file_size"] > 0
    assert note3_item["created_at_ts"] is not None
    assert note3_item["modified_at_ts"] is not None

def test_markdown_normalization(staged_notes_dir):
    """Verify that discovered markdown file details normalize correctly to RegistryObject schema."""
    provider = MarkdownProvider(root_path=staged_notes_dir)
    discovered = provider.discover()
    
    note1_raw = next(item for item in discovered if item["filename"] == "note1.md")
    normalized = provider.normalize(note1_raw)
    
    assert normalized["object_type"] == "note"
    assert normalized["title"] == "note1"
    assert normalized["source_system"] == "markdown"
    assert normalized["external_id"] == "note1.md"
    assert normalized["location"] == note1_raw["absolute_path"]
    
    meta = json.loads(normalized["metadata_json"])
    assert meta["root_path"] == staged_notes_dir
    assert meta["relative_path"] == "note1.md"
    assert meta["folder"] == "Notes"
    assert meta["extension"] == ".md"
    assert meta["file_size"] == len("Hello note 1")
    assert meta["viewer_hint"] == "obsidian_compatible"
    assert meta["provider"] == "markdown"
    
    # Timestamps must be in ISO format
    datetime.fromisoformat(meta["created_at"])
    datetime.fromisoformat(meta["modified_at"])

def test_markdown_sync_and_duplicates(staged_notes_dir, db_session):
    """Verify that sync registers notes and running sync again counts duplicates correctly without creating records."""
    service = RegistryService(db_session)
    provider = MarkdownProvider(root_path=staged_notes_dir)
    
    # First sync
    synced1 = provider.sync(service)
    assert len(synced1) == 3
    assert provider.scanned_count == 3
    assert provider.new_count == 3
    assert provider.existing_count == 0
    
    # Second sync
    synced2 = provider.sync(service)
    assert len(synced2) == 0
    assert provider.scanned_count == 3
    assert provider.new_count == 0
    assert provider.existing_count == 3
    
    # Check stored objects
    db_objs = service.list_objects(filters={"source_system": "markdown"})
    assert len(db_objs) == 3
    
    # Check original paths are preserved
    note3_obj = next(obj for obj in db_objs if obj.title == "note3")
    assert note3_obj.location == os.path.abspath(os.path.join(staged_notes_dir, "nested", "note3.md"))
    assert note3_obj.external_id == os.path.join("nested", "note3.md")

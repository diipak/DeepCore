import json
import os
from unittest.mock import patch, MagicMock
import pytest

from deepcore.core.providers.markdown import MarkdownProvider
from deepcore.core.registry.service import RegistryService
from deepcore.core.capture.service import CaptureService
from deepcore.storage.sqlite.models import RegistryObject, RegistryRelationship

@patch("httpx.get")
def test_resource_extraction_success(mock_get, tmp_path, db_session):
    """Verify that syncing a Markdown note containing links registers the note, captures child objects, and establishes relationships."""
    # Setup single mock side effect to route responses by URL
    def side_effect(url, *args, **kwargs):
        res = MagicMock()
        res.status_code = 200
        if "youtube.com" in url or "youtu.be" in url:
            res.text = "<html><head><meta property='og:title' content='Test Video'></head></html>"
        elif "github.com" in url:
            res.text = "<html><head><meta property='og:title' content='Test Repo'></head></html>"
        else:
            res.text = "<html><head><title>Test Article</title></head></html>"
        return res

    mock_get.side_effect = side_effect

    # Create temporary notes folder
    notes_dir = tmp_path / "MyNotes"
    notes_dir.mkdir()
    
    note_content = (
        "Here are my links:\n"
        "- Youtube: https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
        "- GitHub: https://github.com/my-user/my-repo\n"
        "- Web: https://example.com/another-article\n"
    )
    note_path = notes_dir / "BrainDump.md"
    note_path.write_text(note_content)

    # Sync using MarkdownProvider
    registry_service = RegistryService(db_session)
    provider = MarkdownProvider(root_path=str(notes_dir))
    synced = provider.sync(registry_service)
    
    assert len(synced) == 1
    parent_obj = synced[0]
    assert parent_obj.object_type == "note"
    assert parent_obj.title == "BrainDump"

    # Verify child objects were created in DB
    # 1. YouTube video
    yt_obj = db_session.query(RegistryObject).filter(
        RegistryObject.source_system == "youtube",
        RegistryObject.external_id == "dQw4w9WgXcQ"
    ).first()
    assert yt_obj is not None
    assert yt_obj.object_type == "video"
    assert yt_obj.title == "Test Video"

    # 2. GitHub repo
    gh_obj = db_session.query(RegistryObject).filter(
        RegistryObject.source_system == "github",
        RegistryObject.external_id == "my-user/my-repo"
    ).first()
    assert gh_obj is not None
    assert gh_obj.object_type == "repository"
    assert gh_obj.title == "Test Repo"

    # 3. Web article
    web_obj = db_session.query(RegistryObject).filter(
        RegistryObject.source_system == "web",
        RegistryObject.external_id == "https://example.com/another-article"
    ).first()
    assert web_obj is not None
    assert web_obj.object_type == "document"
    assert web_obj.title == "Test Article"

    # Verify relationships from parent note -> children
    rels = db_session.query(RegistryRelationship).filter(
        RegistryRelationship.from_object_id == parent_obj.id,
        RegistryRelationship.relationship_type == "references"
    ).all()
    assert len(rels) == 3
    target_ids = {r.to_object_id for r in rels}
    assert yt_obj.id in target_ids
    assert gh_obj.id in target_ids
    assert web_obj.id in target_ids


@patch("deepcore.core.providers.youtube.httpx.get")
@patch("deepcore.core.providers.web.httpx.get")
def test_recursion_protection(mock_get_web, mock_get_youtube, db_session):
    """Verify that capture handles circular/recursive URLs cleanly without infinite loops."""
    # Child links back to parent. We will mock a parent Web page referencing a YouTube URL.
    # Note that CaptureService only allows YouTubeProvider at top level.
    # So we call capture on a YouTube URL. Inside its description or mock html, we put a reference back to itself or another link.
    # Since we mock, we can set up parent-child cycle.
    
    url_yt = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # YouTube HTML containing the same YouTube URL
    html_yt = f"<html><head><meta property='og:title' content='Self Reference'></head><body>Link: {url_yt}</body></html>"
    res_yt = MagicMock()
    res_yt.status_code = 200
    res_yt.text = html_yt
    
    mock_get_youtube.return_value = res_yt

    service = CaptureService(db_session)
    # This shouldn't infinite loop because of the processed_urls set
    obj = service.capture(url_yt)
    
    assert obj is not None
    assert obj.object_type == "video"
    assert obj.external_id == "dQw4w9WgXcQ"


@patch("httpx.get")
def test_intelligence_rebuild(mock_get, db_session):
    """Verify that deepcore intelligence rebuild command reprocesses existing notes and documents, extracts links, and is idempotent."""
    def side_effect(url, *args, **kwargs):
        res = MagicMock()
        res.status_code = 200
        if "youtube.com" in url or "youtu.be" in url:
            res.text = "<html><head><meta property='og:title' content='Test Video'></head></html>"
        else:
            res.text = "<html><head><title>Test Article</title></head></html>"
        return res

    mock_get.side_effect = side_effect

    # Create an existing note with links directly in DB
    note_content = "Check this out: https://www.youtube.com/watch?v=dQw4w9WgXcQ and https://example.com/some-page"
    from deepcore.storage.sqlite.models import RegistryObject as DBRegistryObject
    import uuid
    import json
    
    parent_note = DBRegistryObject(
        uuid=str(uuid.uuid4()),
        object_type="note",
        title="Legacy Brain Dump",
        source_system="markdown",
        external_id="legacy-brain-dump",
        description=note_content,
        metadata_json=json.dumps({"root_path": "/some/path"}),
        status="active"
    )
    db_session.add(parent_note)
    db_session.commit()

    # Verify no relationships exist yet
    parent_id = parent_note.id
    from deepcore.storage.sqlite.models import RegistryRelationship as DBRegistryRelationship
    rels_before = db_session.query(DBRegistryRelationship).filter(
        DBRegistryRelationship.from_object_id == parent_id
    ).all()
    assert len(rels_before) == 0

    # Execute rebuild command logic manually using Typer runner
    from typer.testing import CliRunner
    from deepcore.cli.main import app
    
    runner = CliRunner()
    # Note: We need to override DB session in CLI command or mock SessionLocal.
    # We also mock db_session.close to prevent detaching objects in the test session.
    with patch.object(db_session, "close", return_value=None):
        with patch("deepcore.cli.main.SessionLocal", return_value=db_session):
            result = runner.invoke(app, ["intelligence", "rebuild"])
            assert result.exit_code == 0
            assert "🧠" in result.output
            assert "Processed:\n1 memories" in result.output
            assert "🎬 1 videos" in result.output
            assert "🌐 1 web resources" in result.output
            assert "2 references" in result.output

    # Verify child objects were created
    video_obj = db_session.query(DBRegistryObject).filter(
        DBRegistryObject.source_system == "youtube"
    ).first()
    assert video_obj is not None
    assert video_obj.title == "Test Video"

    web_obj = db_session.query(DBRegistryObject).filter(
        DBRegistryObject.source_system == "web"
    ).first()
    assert web_obj is not None
    assert web_obj.title == "Test Article"

    # Verify relationships
    rels_after = db_session.query(DBRegistryRelationship).filter(
        DBRegistryRelationship.from_object_id == parent_id
    ).all()
    assert len(rels_after) == 2

    # Run again to verify idempotency (relationships are not duplicated, skipped is incremented)
    with patch.object(db_session, "close", return_value=None):
        with patch("deepcore.cli.main.SessionLocal", return_value=db_session):
            result2 = runner.invoke(app, ["intelligence", "rebuild"])
            assert result2.exit_code == 0
            assert "🎬 0 videos" in result2.output  # they are skipped
            assert "🌐 0 web resources" in result2.output
            assert "0 references" in result2.output  # no new relationships
            assert "2 existing objects" in result2.output  # 2 skipped existing objects

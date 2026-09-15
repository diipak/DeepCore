import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from deepcore.cli.main import app

@pytest.fixture
def cli_runner(db_session):
    """Provides a CliRunner instance with the SessionLocal db patched to the test transactional session."""
    class NoCloseSession:
        def __init__(self, session):
            self.session = session
        def __getattr__(self, name):
            return getattr(self.session, name)
        def close(self):
            # Ignore close to prevent tearing down the test database session early
            pass

    mock_sess = NoCloseSession(db_session)
    with patch("deepcore.cli.main.SessionLocal", return_value=mock_sess):
        yield CliRunner()

@patch("deepcore.core.providers.youtube.httpx.get")
def test_cli_capture_success(mock_get, cli_runner):
    """Verify that capturing a valid YouTube URL prints the registration details successfully."""
    mock_html = """
    <html>
        <head>
            <meta property="og:title" content="Rickroll">
            <meta property="og:image" content="https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg">
            <link itemprop="name" content="Rick Astley">
        </head>
    </html>
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = mock_html
    mock_get.return_value = mock_response

    result = cli_runner.invoke(app, ["capture", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"])
    assert result.exit_code == 0
    assert "Captured successfully" in result.stdout
    assert "Type:\nvideo" in result.stdout
    assert "Title:\nRickroll" in result.stdout
    assert "Source:\nyoutube" in result.stdout
    assert "UUID:" in result.stdout

def test_cli_capture_unsupported(cli_runner):
    """Verify that capturing an unsupported URL fails with exit code 1 and prints an error."""
    result = cli_runner.invoke(app, ["capture", "https://google.com"])
    assert result.exit_code == 1
    assert "Error:" in result.stdout

def test_cli_list(db_session, cli_runner):
    """Verify that deepcore list prints registered objects and supports filtering by --type and --source."""
    from deepcore.core.registry.service import RegistryService
    from deepcore.core.objects.schemas import RegistryObjectCreate
    
    service = RegistryService(db_session)
    service.register_object(RegistryObjectCreate(
        object_type="video",
        title="AI Explained",
        source_system="youtube",
        external_id="123",
        location="https://youtube.com/watch?v=123"
    ))
    service.register_object(RegistryObjectCreate(
        object_type="note",
        title="Meeting notes",
        source_system="manual",
        location="local"
    ))
    
    # 1. Test listing all objects
    result = cli_runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "TYPE | TITLE | SOURCE | CREATED" in result.stdout
    assert "video | AI Explained | youtube |" in result.stdout
    assert "note | Meeting notes | manual |" in result.stdout
    
    # 2. Test filtering by type
    result_type = cli_runner.invoke(app, ["list", "--type", "video"])
    assert result_type.exit_code == 0
    assert "video | AI Explained | youtube |" in result_type.stdout
    assert "note | Meeting notes" not in result_type.stdout
    
    # 3. Test filtering by source
    result_source = cli_runner.invoke(app, ["list", "--source", "manual"])
    assert result_source.exit_code == 0
    assert "note | Meeting notes | manual |" in result_source.stdout
    assert "video | AI Explained" not in result_source.stdout

def test_cli_stats(db_session, cli_runner):
    """Verify that deepcore stats returns correct overall and group counts, sorted descending by count."""
    from deepcore.core.registry.service import RegistryService
    from deepcore.core.objects.schemas import RegistryObjectCreate
    
    service = RegistryService(db_session)
    # 2 videos
    service.register_object(RegistryObjectCreate(
        object_type="video", title="Video 1", source_system="youtube"
    ))
    service.register_object(RegistryObjectCreate(
        object_type="video", title="Video 2", source_system="youtube"
    ))
    # 1 note
    service.register_object(RegistryObjectCreate(
        object_type="note", title="Note 1", source_system="manual"
    ))
    
    result = cli_runner.invoke(app, ["stats"])
    assert result.exit_code == 0
    assert "DeepCore Registry" in result.stdout
    assert "Total Objects:\n3" in result.stdout
    
    # Verify breakdowns with double newlines separating header and counts
    assert "By Type:\n\nvideo: 2\nnote: 1" in result.stdout
    assert "By Source:\n\nyoutube: 2\nmanual: 1" in result.stdout


def test_cli_sync_markdown(db_session, staged_notes_dir, cli_runner):
    """Verify that deepcore sync markdown <path> runs successfully and prints correct sync statistics."""
    from deepcore.storage.sqlite.models import KnowledgeSource as DBKnowledgeSource
    import json

    # Pre-create KnowledgeSource (Amendment 1 requires it)
    source = DBKnowledgeSource(
        workspace_id=1,
        provider_id="filesystem",
        kind="filesystem",
        name="Test Obsidian Notes",
        location=staged_notes_dir,
        config_json=json.dumps({"path": staged_notes_dir}),
        status="Configured"
    )
    db_session.add(source)
    db_session.commit()

    # 1. Run sync first time (3 files scanned, 3 new)
    result1 = cli_runner.invoke(app, ["sync", "markdown", staged_notes_dir])
    assert result1.exit_code == 0
    assert "DeepCore Sync Completed Successfully" in result1.stdout
    assert "Scanned:  3 files" in result1.stdout
    assert "Created:  3 files" in result1.stdout
    assert "Existing: 0 files" in result1.stdout
    
    # 2. Run sync second time (0 files scanned as none are modified)
    result2 = cli_runner.invoke(app, ["sync", "markdown", staged_notes_dir])
    assert result2.exit_code == 0
    assert "Scanned:  0 files" in result2.stdout
    assert "Created:  0 files" in result2.stdout
    assert "Existing: 0 files" in result2.stdout


def test_cli_find(db_session, cli_runner):
    """Verify deepcore find outputs matching objects with ID, type, title, source in case-insensitive manner."""
    from deepcore.core.registry.service import RegistryService
    from deepcore.core.objects.schemas import RegistryObjectCreate
    
    service = RegistryService(db_session)
    obj = service.register_object(RegistryObjectCreate(
        object_type="note",
        title="Build RAG System",
        source_system="markdown",
        location="/notes/rag.md",
        status="active"
    ))
    
    # 1. Search with exact case query
    result = cli_runner.invoke(app, ["find", "RAG"])
    assert result.exit_code == 0
    assert "ID | TYPE | TITLE | SOURCE" in result.stdout
    assert "--------------------------------" in result.stdout
    assert f"{obj.id} | note | Build RAG System | markdown" in result.stdout
    
    # 2. Search with lowercase query (regression test)
    result_lower = cli_runner.invoke(app, ["find", "rag"])
    assert result_lower.exit_code == 0
    assert f"{obj.id} | note | Build RAG System | markdown" in result_lower.stdout


def test_cli_show_by_id_and_uuid(db_session, cli_runner):
    """Verify deepcore show displays correct detailed fields using either integer ID or UUID."""
    from deepcore.core.registry.service import RegistryService
    from deepcore.core.objects.schemas import RegistryObjectCreate
    
    service = RegistryService(db_session)
    obj = service.register_object(RegistryObjectCreate(
        object_type="note",
        title="Meeting Notes",
        source_system="manual",
        location="/notes/meet.txt",
        status="active",
        metadata_json='{"importance": "high"}'
    ))
    
    # 1. Show by ID
    result_id = cli_runner.invoke(app, ["show", str(obj.id)])
    assert result_id.exit_code == 0
    assert "Title: Meeting Notes" in result_id.stdout
    assert "Source: manual" in result_id.stdout
    assert "Location: /notes/meet.txt" in result_id.stdout
    assert "Status: active" in result_id.stdout
    assert 'Metadata: {"importance": "high"}' in result_id.stdout
    
    # 2. Show by UUID
    result_uuid = cli_runner.invoke(app, ["show", obj.uuid])
    assert result_uuid.exit_code == 0
    assert "Title: Meeting Notes" in result_uuid.stdout
    
    # 3. Show non-existent
    result_fail = cli_runner.invoke(app, ["show", "999999"])
    assert result_fail.exit_code == 1
    assert "Error: Object with identifier '999999' not found" in result_fail.stdout


def test_cli_recent(db_session, cli_runner):
    """Verify deepcore recent prints header, empty line, and recent items."""
    from deepcore.core.registry.service import RegistryService
    from deepcore.core.objects.schemas import RegistryObjectCreate
    
    service = RegistryService(db_session)
    obj = service.register_object(RegistryObjectCreate(
        object_type="note",
        title="Recent Memory",
        source_system="manual",
        status="active"
    ))
    
    result = cli_runner.invoke(app, ["recent"])
    assert result.exit_code == 0
    assert "Recent DeepCore Memories\n" in result.stdout
    assert "DATE | TYPE | TITLE | SOURCE" in result.stdout
    created_str = obj.created_at.strftime("%Y-%m-%d")
    assert f"{created_str} | note | Recent Memory | manual" in result.stdout


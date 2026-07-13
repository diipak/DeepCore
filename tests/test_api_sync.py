import os
import json
import pytest
from deepcore.storage.sqlite.models import RegistryObject, ContentIndex, SyncRun

def test_api_sync_markdown_success(client, staged_notes_dir, db_session):
    """
    Test the end-to-end sync endpoint.
    It should:
    1. Scan files in staged_notes_dir and register objects.
    2. Run downstream content indexing.
    3. Persist the SyncRun record.
    """
    # 1. Trigger the sync via the POST endpoint
    payload = {
        "path": staged_notes_dir
    }
    response = client.post("/api/providers/markdown/sync", json=payload)
    assert response.status_code == 200
    
    sync_run_data = response.json()
    assert sync_run_data["provider"] == "markdown"
    assert sync_run_data["source_location"] == staged_notes_dir
    assert sync_run_data["status"] == "success"
    assert sync_run_data["objects_scanned"] == 3
    assert sync_run_data["objects_created"] == 3
    assert sync_run_data["objects_existing"] == 0
    assert sync_run_data["objects_updated"] == 0
    assert sync_run_data["objects_missing"] == 0

    # 2. Check that RegistryObject records were created
    objs = db_session.query(RegistryObject).filter(RegistryObject.source_system == "markdown").all()
    assert len(objs) == 3
    titles = {obj.title for obj in objs}
    assert titles == {"note1", "note2", "note3"}

    # 3. Check that Downstream Indexing happened (ContentIndex populated)
    indices = db_session.query(ContentIndex).all()
    assert len(indices) == 3
    indexed_text = {idx.raw_text for idx in indices}
    assert "Hello note 1" in indexed_text
    assert "Case insensitive test" in indexed_text
    assert "Nested markdown note" in indexed_text


def test_api_sync_markdown_duplicates(client, staged_notes_dir, db_session):
    """
    Test running the sync twice.
    The second run should report 3 existing/unchanged objects and 0 new ones, with no duplicates.
    """
    payload = {"path": staged_notes_dir}
    
    # First sync
    res1 = client.post("/api/providers/markdown/sync", json=payload)
    assert res1.status_code == 200
    
    # Second sync
    res2 = client.post("/api/providers/markdown/sync", json=payload)
    assert res2.status_code == 200
    
    sync_run = res2.json()
    assert sync_run["objects_scanned"] == 3
    assert sync_run["objects_created"] == 0
    assert sync_run["objects_existing"] == 3
    
    # Verify DB counts remain 3
    objs = db_session.query(RegistryObject).filter(RegistryObject.source_system == "markdown").all()
    assert len(objs) == 3
    indices = db_session.query(ContentIndex).all()
    assert len(indices) == 3


def test_api_sync_markdown_modification(client, staged_notes_dir, db_session):
    """
    Test modifying a file's content and re-syncing.
    The updated file should be registered, content updated in DB, and re-indexed.
    """
    payload = {"path": staged_notes_dir}
    client.post("/api/providers/markdown/sync", json=payload)

    # Modify note1.md content
    note1_path = os.path.join(staged_notes_dir, "note1.md")
    with open(note1_path, "w", encoding="utf-8") as f:
        f.write("Hello note 1 - UPDATED CONTENT")

    # Re-sync
    res = client.post("/api/providers/markdown/sync", json=payload)
    assert res.status_code == 200
    sync_run = res.json()
    assert sync_run["objects_scanned"] == 3
    assert sync_run["objects_created"] == 0
    assert sync_run["objects_updated"] == 1
    assert sync_run["objects_existing"] == 3

    # Check updated content in db
    note1_obj = db_session.query(RegistryObject).filter(
        RegistryObject.source_system == "markdown",
        RegistryObject.title == "note1"
    ).first()
    assert note1_obj is not None
    
    idx = db_session.query(ContentIndex).filter(ContentIndex.object_id == note1_obj.id).first()
    assert idx is not None
    assert idx.raw_text == "Hello note 1 - UPDATED CONTENT"


def test_api_sync_markdown_rename(client, staged_notes_dir, db_session):
    """
    Test renaming a file.
    The existing object should be updated to point to the new location and name without welding duplicate.
    """
    payload = {"path": staged_notes_dir}
    client.post("/api/providers/markdown/sync", json=payload)

    # Rename note1.md to note1_renamed.md
    old_path = os.path.join(staged_notes_dir, "note1.md")
    new_path = os.path.join(staged_notes_dir, "note1_renamed.md")
    os.rename(old_path, new_path)

    # Re-sync
    res = client.post("/api/providers/markdown/sync", json=payload)
    assert res.status_code == 200
    sync_run = res.json()
    # It scans 3 files: note1_renamed.md, note2.MD, note3.md
    assert sync_run["objects_scanned"] == 3
    # note1_renamed.md should trigger a rename update of the existing note1 object.
    assert sync_run["objects_updated"] == 1
    assert sync_run["objects_existing"] == 3

    # Check database
    objs = db_session.query(RegistryObject).filter(RegistryObject.source_system == "markdown").all()
    assert len(objs) == 3
    titles = {obj.title for obj in objs}
    # "note1" title changes to "note1_renamed"
    assert titles == {"note1_renamed", "note2", "note3"}


def test_api_sync_markdown_deletion(client, staged_notes_dir, db_session):
    """
    Test deleting a file.
    The deleted file's object should have its status marked as "missing".
    """
    payload = {"path": staged_notes_dir}
    client.post("/api/providers/markdown/sync", json=payload)

    # Delete note2.MD
    note2_path = os.path.join(staged_notes_dir, "note2.MD")
    os.remove(note2_path)

    # Re-sync
    res = client.post("/api/providers/markdown/sync", json=payload)
    assert res.status_code == 200
    sync_run = res.json()
    assert sync_run["objects_scanned"] == 2
    assert sync_run["objects_existing"] == 2
    assert sync_run["objects_missing"] == 1

    # Check database status
    note2_obj = db_session.query(RegistryObject).filter(
        RegistryObject.source_system == "markdown",
        RegistryObject.title == "note2"
    ).first()
    assert note2_obj is not None
    assert note2_obj.status == "missing"


def test_api_sync_errors(client):
    """
    Test error scenarios.
    1. Unsupported provider.
    2. Non-existent path.
    3. Missing path param.
    """
    # 1. Unsupported provider
    res = client.post("/api/providers/unsupported/sync", json={"path": "/tmp"})
    assert res.status_code == 400
    assert "not supported" in res.json()["detail"]

    # 2. Non-existent path
    res = client.post("/api/providers/markdown/sync", json={"path": "/nonexistent/path/here"})
    assert res.status_code == 400
    assert "does not exist" in res.json()["detail"]

    # 3. Missing path parameter
    res = client.post("/api/providers/markdown/sync", json={})
    assert res.status_code == 400
    assert "path" in res.json()["detail"]

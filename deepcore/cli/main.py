import click
from typer.core import TyperOption
import inspect

# 1. Patch is_flag detection bug in Click 8.2+ compatibility with Typer 0.12
sig = inspect.signature(click.Option.__init__)
click_unset = sig.parameters["flag_value"].default

orig_init = TyperOption.__init__
def patched_init(self, *args, **kwargs):
    if kwargs.get("flag_value") is None and kwargs.get("is_flag") is not True:
        if kwargs.get("type") != click.BOOL:
            kwargs["flag_value"] = click_unset
    orig_init(self, *args, **kwargs)

TyperOption.__init__ = patched_init

# 2. Patch make_metavar compatibility bug in Click 8.2+ compatibility with Typer 0.12
orig_make_metavar = click.Parameter.make_metavar
def patched_make_metavar(self, ctx=None):
    if ctx is None:
        ctx = click.get_current_context(silent=True)
    if ctx is None:
        if self.metavar is not None:
            return self.metavar
        metavar = self.type.name.upper()
        if self.nargs != 1:
            metavar += "..."
        return metavar
    return orig_make_metavar(self, ctx)

click.Parameter.make_metavar = patched_make_metavar

import typer
from typing import Optional
from deepcore.storage.sqlite.db import SessionLocal
from deepcore.core.capture.service import CaptureService, UnsupportedInputError
from deepcore.core.registry.service import RegistryService
from deepcore.core.objects.schemas import RegistryObject as SchemaRegistryObject

app = typer.Typer(help="DeepCore CLI Interface")

# Automatically initialize and migrate SQLite database tables if they do not exist
from deepcore.storage.sqlite.db import engine
from deepcore.storage.sqlite.models import run_migrations
run_migrations(engine)

@app.command("capture")
def capture(content: str):
    """Capture a URL or source into DeepCore."""
    db = SessionLocal()
    try:
        service = CaptureService(db)
        obj = service.capture(content)
        schema_obj = SchemaRegistryObject.model_validate(obj)
        
        typer.echo("Captured successfully\n")
        typer.echo(f"Type:\n{schema_obj.object_type.value}\n")
        typer.echo(f"Title:\n{schema_obj.title}\n")
        typer.echo(f"Source:\n{schema_obj.source_system}\n")
        typer.echo(f"UUID:\n{schema_obj.uuid}")
    except UnsupportedInputError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)
    except ValueError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"Unexpected Error: {e}")
        raise typer.Exit(code=1)
    finally:
        db.close()

@app.command("list")
def list_objects(
    object_type: str = typer.Option(None, "--type", help="Filter by object type"),
    source: str = typer.Option(None, "--source", help="Filter by source system")
):
    """List objects registered in DeepCore."""
    db = SessionLocal()
    try:
        service = RegistryService(db)
        filters = {}
        if object_type:
            filters["object_type"] = object_type
        if source:
            filters["source_system"] = source
            
        db_objects = service.list_objects(filters=filters)
        objects = [SchemaRegistryObject.model_validate(obj) for obj in db_objects]
        
        typer.echo("TYPE | TITLE | SOURCE | CREATED")
        for obj in objects:
            created_str = obj.created_at.strftime("%Y-%m-%d")
            typer.echo(f"{obj.object_type.value} | {obj.title} | {obj.source_system} | {created_str}")
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)
    finally:
        db.close()

@app.command("stats")
def stats():
    """Show statistics about the DeepCore registry."""
    db = SessionLocal()
    try:
        service = RegistryService(db)
        stats_data = service.get_statistics()
        
        total_objects = stats_data["total_objects"]
        by_type = stats_data["by_type"]
        by_source = stats_data["by_source"]
        
        typer.echo("DeepCore Registry")
        typer.echo()
        typer.echo("Total Objects:")
        typer.echo(total_objects)
        typer.echo()
        typer.echo()
        typer.echo("By Type:")
        typer.echo()
        
        # Sort by count descending, then alphabetically by name
        sorted_types = sorted(by_type.items(), key=lambda x: (-x[1], x[0]))
        for t, count in sorted_types:
            typer.echo(f"{t}: {count}")
        typer.echo()
        typer.echo()
        typer.echo("By Source:")
        typer.echo()
        
        # Sort by count descending, then alphabetically by name
        sorted_sources = sorted(by_source.items(), key=lambda x: (-x[1], x[0]))
        for s, count in sorted_sources:
            typer.echo(f"{s}: {count}")
            
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)
    finally:
        db.close()

sync_app = typer.Typer(help="Sync data from local/external sources")
app.add_typer(sync_app, name="sync")

@sync_app.command("markdown")
def sync_markdown(path: str):
    """Sync local Markdown notes into DeepCore."""
    db = SessionLocal()
    try:
        from deepcore.core.providers.markdown import MarkdownProvider
        
        provider = MarkdownProvider(root_path=path)
        service = RegistryService(db)
        provider.sync(service)
        
        typer.echo("DeepCore Markdown Sync")
        typer.echo()
        typer.echo("Scanned:")
        typer.echo(f"{provider.scanned_count} files")
        typer.echo()
        typer.echo("New:")
        typer.echo(provider.new_count)
        typer.echo()
        typer.echo("Existing:")
        typer.echo(provider.existing_count)
        typer.echo()
        typer.echo("Missing:")
        typer.echo(provider.missing_count)
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)
    finally:
        db.close()

@sync_app.command("history")
def sync_history():
    """Show sync runs history."""
    db = SessionLocal()
    try:
        service = RegistryService(db)
        runs = service.list_sync_runs()
        
        typer.echo("DATE | PROVIDER | SCANNED | NEW | STATUS")
        for run in runs:
            date_str = run.started_at.strftime("%Y-%m-%d")
            typer.echo(f"{date_str} | {run.provider} | {run.objects_scanned} | {run.objects_created} | {run.status}")
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)
    finally:
        db.close()

@app.command("find")
def find(query: str):
    """Find active registry objects by title, description, or location."""
    db = SessionLocal()
    try:
        service = RegistryService(db)
        results = service.search_objects(query)
        typer.echo("ID | TYPE | TITLE | SOURCE")
        typer.echo("--------------------------------")
        for obj in results:
            typer.echo(f"{obj.id} | {obj.object_type} | {obj.title} | {obj.source_system}")
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)
    finally:
        db.close()

@app.command("show")
def show(id_or_uuid: str):
    """Show details of a specific registry object by ID or UUID."""
    db = SessionLocal()
    try:
        service = RegistryService(db)
        obj_details = service.get_object_details(id_or_uuid)
        if not obj_details:
            typer.echo(f"Error: Object with identifier '{id_or_uuid}' not found")
            raise typer.Exit(code=1)
        
        typer.echo(f"Title: {obj_details['title']}")
        typer.echo(f"Source: {obj_details['source']}")
        typer.echo(f"Location: {obj_details['location'] or ''}")
        typer.echo(f"Status: {obj_details['status']}")
        typer.echo(f"Metadata: {obj_details['metadata_json'] or ''}")
    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)
    finally:
        db.close()

@app.command("recent")
def recent():
    """Show recent active memory objects."""
    db = SessionLocal()
    try:
        service = RegistryService(db)
        recent_objs = service.recent_objects(limit=10)
        typer.echo("Recent DeepCore Memories\n")
        typer.echo("DATE | TYPE | TITLE | SOURCE")
        for obj in recent_objs:
            date_str = obj.created_at.strftime("%Y-%m-%d")
            typer.echo(f"{date_str} | {obj.object_type} | {obj.title} | {obj.source_system}")
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)
    finally:
        db.close()

def extract_snippet(text: str, query: str, context_len: int = 30) -> str:
    """Extract a snippet of text around the first match of query."""
    idx = text.lower().find(query.lower())
    if idx == -1:
        snippet = text[:context_len * 2]
        if len(text) > context_len * 2:
            snippet += "..."
        return snippet.replace("\n", " ").replace("\r", " ")
    
    start = max(0, idx - context_len)
    end = min(len(text), idx + len(query) + context_len)
    snippet = text[start:end]
    snippet = snippet.replace("\n", " ").replace("\r", " ")
    
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet

@app.command("index")
def index_command():
    """Index all active objects with supported content."""
    db = SessionLocal()
    try:
        from deepcore.core.content.service import ContentService
        service = ContentService(db)
        stats = service.index_all_active_objects()
        typer.echo("DeepCore Content Index")
        typer.echo()
        typer.echo("Objects scanned:")
        typer.echo(stats["scanned"])
        typer.echo()
        typer.echo("Indexed:")
        typer.echo(stats["indexed"])
        typer.echo()
        typer.echo("Skipped:")
        typer.echo(stats["skipped"])
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)
    finally:
        db.close()

content_app = typer.Typer(help="Manage and search content index")
app.add_typer(content_app, name="content")

@content_app.command("search")
def content_search(query: str):
    """Search indexed content raw text."""
    db = SessionLocal()
    try:
        from deepcore.core.content.service import ContentService
        service = ContentService(db)
        results = service.search_content(query)
        typer.echo("ID | TITLE | MATCH")
        typer.echo("------------------------------------")
        for obj, idx in results:
            snippet = extract_snippet(idx.raw_text, query)
            typer.echo(f"{obj.id} | {obj.title} | {snippet}")
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)
    finally:
        db.close()

@content_app.command("show")
def content_show(id_or_uuid: str):
    """Show preview of stored indexed content."""
    db = SessionLocal()
    try:
        from deepcore.core.content.service import ContentService
        service = ContentService(db)
        content_obj = service.get_content(id_or_uuid)
        if not content_obj:
            typer.echo(f"Error: No indexed content found for object '{id_or_uuid}'")
            raise typer.Exit(code=1)
        
        preview = content_obj.raw_text[:1000]
        typer.echo(preview)
    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)
    finally:
        db.close()

concepts_app = typer.Typer(help="Manage and inspect extracted concepts")
app.add_typer(concepts_app, name="concepts")

@concepts_app.command("extract")
def concepts_extract():
    """Extract key concepts from all active indexed memories."""
    db = SessionLocal()
    try:
        from deepcore.core.concepts.service import ConceptService
        service = ConceptService(db)
        stats = service.extract_all()
        typer.echo("DeepCore Concept Extraction")
        typer.echo()
        typer.echo("Scanned:")
        typer.echo(stats["scanned"])
        typer.echo()
        typer.echo("Concepts Created:")
        typer.echo(stats["concepts_created"])
        typer.echo()
        typer.echo("Relationships Created:")
        typer.echo(stats["relationships_created"])
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)
    finally:
        db.close()

@concepts_app.command("list")
def concepts_list(limit: int = 50):
    """List concepts ordered by connection count."""
    db = SessionLocal()
    try:
        from deepcore.core.concepts.service import ConceptService
        service = ConceptService(db)
        results = service.list_concepts(limit=limit)
        typer.echo("CONCEPT | CONNECTIONS")
        for obj, count in results:
            typer.echo(f"{obj.title} | {count}")
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)
    finally:
        db.close()

@concepts_app.command("show")
def concepts_show(concept: str):
    """Show details of a specific concept and its connected memories."""
    db = SessionLocal()
    try:
        from deepcore.core.concepts.service import ConceptService
        service = ConceptService(db)
        concept_obj = service.get_concept_by_name(concept)
        if not concept_obj:
            typer.echo(f"Error: Concept '{concept}' not found")
            raise typer.Exit(code=1)
        
        typer.echo("Concept:")
        typer.echo(concept_obj.title)
        typer.echo()
        typer.echo("Connected Memories:")
        
        memories = service.get_connected_memories(concept_obj.id)
        for mem in memories:
            typer.echo(f"- {mem.title}")
    except typer.Exit:
        raise
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)
    finally:
        db.close()

if __name__ == "__main__":
    app()




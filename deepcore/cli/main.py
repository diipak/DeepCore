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

# Automatically initialize SQLite database tables if they do not exist
from deepcore.storage.sqlite.db import Base, engine
from deepcore.storage.sqlite import models
Base.metadata.create_all(bind=engine)

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
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(code=1)
    finally:
        db.close()

if __name__ == "__main__":
    app()

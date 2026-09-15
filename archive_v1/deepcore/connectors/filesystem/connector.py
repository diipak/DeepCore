import os
from datetime import datetime, timezone
from typing import Dict, Any, Generator
from deepcore.core.acquisition.base import (
    BaseConnector,
    SyncContext,
    HealthStatus,
    ConnectorOperation,
    ExecutionRequest,
    ExecutionResponse,
    ConnectorCapabilities,
)

class FilesystemConnector(BaseConnector):
    """
    Filesystem Connector. Implements Technical Contract for walking local folders,
    verifying directory permissions, and stateless live execution (read, list, search).
    """
    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            supported_operations=[
                ConnectorOperation.READ,
                ConnectorOperation.LIST,
                ConnectorOperation.SEARCH,
            ],
            requires_configuration=True,
            requires_permissions=False,
            supports_pagination=False,
            supports_streaming=False,
            supports_actions=False,
            metadata={"provider": "filesystem", "file_types": [".md", ".markdown"]}
        )

    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """
        Stateless live execution adapter over local filesystem operations.
        """
        op = request.operation
        params = request.parameters or {}
        config = request.context.config or {}
        target_path = params.get("path") or config.get("path")

        if op == ConnectorOperation.READ:
            if not target_path:
                raise ValueError("Operation 'read' requires 'path' parameter or configuration.")
            if not os.path.exists(target_path):
                raise FileNotFoundError(f"File not found: {target_path}")
            if not os.path.isfile(target_path):
                raise ValueError(f"Path is not a regular file: {target_path}")
            
            try:
                stat_info = os.stat(target_path)
                with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                
                res_item = {
                    "absolute_path": os.path.abspath(target_path),
                    "filename": os.path.basename(target_path),
                    "file_size": stat_info.st_size,
                    "modified_at_ts": stat_info.st_mtime,
                    "content": content,
                }
                return ExecutionResponse(
                    results=[res_item],
                    metadata={"count": 1, "path": target_path},
                    diagnostics={"status": "success"}
                )
            except Exception as e:
                raise RuntimeError(f"Failed to read file '{target_path}': {e}")

        elif op == ConnectorOperation.LIST:
            if not target_path:
                raise ValueError("Operation 'list' requires 'path' parameter or configuration.")
            if not os.path.exists(target_path):
                raise FileNotFoundError(f"Directory not found: {target_path}")
            if not os.path.isdir(target_path):
                raise ValueError(f"Path is not a directory: {target_path}")

            results = []
            try:
                for entry in os.scandir(target_path):
                    if entry.name.startswith(".") or entry.name in (".git", ".obsidian", ".trash"):
                        continue
                    try:
                        stat_info = entry.stat()
                        size = stat_info.st_size
                        modified = stat_info.st_mtime
                    except Exception:
                        size = 0
                        modified = 0.0

                    results.append({
                        "filename": entry.name,
                        "absolute_path": os.path.abspath(entry.path),
                        "is_dir": entry.is_dir(),
                        "file_size": size,
                        "modified_at_ts": modified,
                    })
            except Exception as e:
                raise RuntimeError(f"Failed to list directory '{target_path}': {e}")

            return ExecutionResponse(
                results=results,
                metadata={"count": len(results), "path": target_path},
                diagnostics={"status": "success"}
            )

        elif op == ConnectorOperation.SEARCH:
            search_dir = target_path or config.get("path")
            if not search_dir or not os.path.isdir(search_dir):
                raise ValueError("Operation 'search' requires a valid directory 'path'.")
            
            query = params.get("query", "").lower()
            pattern = params.get("pattern", "").lower()
            results = []

            for root, dirs, files in os.walk(search_dir):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in (".git", ".obsidian", ".trash")]
                for file in files:
                    if file.startswith("."):
                        continue
                    if pattern and pattern not in file.lower():
                        continue

                    abs_path = os.path.abspath(os.path.join(root, file))
                    matched = True

                    if query:
                        # Check filename or file content match
                        filename_match = query in file.lower()
                        content_match = False
                        if not filename_match and file.lower().endswith((".md", ".markdown", ".txt", ".json")):
                            try:
                                with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                                    if query in f.read().lower():
                                        content_match = True
                            except Exception:
                                pass
                        matched = filename_match or content_match

                    if matched:
                        try:
                            stat_info = os.stat(abs_path)
                            size = stat_info.st_size
                            modified = stat_info.st_mtime
                        except Exception:
                            size = 0
                            modified = 0.0

                        results.append({
                            "filename": file,
                            "absolute_path": abs_path,
                            "relative_path": os.path.relpath(abs_path, search_dir),
                            "file_size": size,
                            "modified_at_ts": modified,
                        })

            return ExecutionResponse(
                results=results,
                metadata={"count": len(results), "search_dir": search_dir, "query": query},
                diagnostics={"status": "success"}
            )

        else:
            raise NotImplementedError(
                f"Operation '{op.value}' is not supported by FilesystemConnector."
            )
    def authenticate(self, credentials: Dict[str, Any]) -> HealthStatus:
        """Local filesystem requires no remote authentication."""
        return HealthStatus(state="HEALTHY", message="No authentication required.")

    def health(self, ctx: SyncContext) -> HealthStatus:
        """
        Amendment 4 - Standardized Health Reporting.
        Validates path existence, read permissions, config validity, and checks cursor.
        """
        path = ctx.config.get("path")
        if not path:
            return HealthStatus(state="CRITICAL", message="Configuration invalid: 'path' not specified.")

        # Validate Path Exists
        if not os.path.exists(path):
            return HealthStatus(state="CRITICAL", message=f"Path does not exist: {path}")

        # Validate is a directory
        if not os.path.isdir(path):
            return HealthStatus(state="CRITICAL", message=f"Path is not a directory: {path}")

        # Validate Read Permissions
        if not os.access(path, os.R_OK):
            return HealthStatus(state="CRITICAL", message=f"No read permission on directory: {path}")

        # Last successful sync info (from cursor if populated by runtime)
        last_sync = ctx.cursor_state.get("last_sync_time")
        msg = f"Path verified. Last successful sync: {last_sync}" if last_sync else "Path verified. No prior synchronization recorded."
        return HealthStatus(state="HEALTHY", message=msg)

    def discover(self, ctx: SyncContext) -> Generator[Dict[str, Any], None, None]:
        """Perform a full directory walk and yield raw file stats."""
        path = ctx.config.get("path")
        if not path or not os.path.isdir(path):
            raise ValueError(f"Invalid scan directory path: {path}")

        # Track active relative paths to check for deletions later
        active_rel_paths = []

        for root, dirs, files in os.walk(path):
            # Exclude hidden and system directories in-place
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('.git', '.obsidian', '.trash')]

            for file in files:
                if file.startswith('.') or not file.lower().endswith(('.md', '.markdown')):
                    continue

                abs_path = os.path.abspath(os.path.join(root, file))
                rel_path = os.path.relpath(abs_path, path)
                active_rel_paths.append(rel_path)

                try:
                    stat_info = os.stat(abs_path)
                    try:
                        created = stat_info.st_birthtime
                    except AttributeError:
                        created = stat_info.st_ctime
                    modified = stat_info.st_mtime
                    size = stat_info.st_size
                except Exception:
                    created = datetime.now(timezone.utc).timestamp()
                    modified = datetime.now(timezone.utc).timestamp()
                    size = 0

                parent = os.path.basename(os.path.dirname(abs_path))

                yield {
                    "external_id": rel_path,
                    "absolute_path": abs_path,
                    "relative_path": rel_path,
                    "filename": file,
                    "file_size": size,
                    "created_at_ts": created,
                    "modified_at_ts": modified,
                    "parent_folder": parent,
                    "root_path": path
                }

        # Save active paths in cursor for tracking deleted/missing files
        ctx.cursor_state["active_ids"] = active_rel_paths
        ctx.cursor_state["last_sync_time"] = datetime.now(timezone.utc).isoformat()

    def sync(self, ctx: SyncContext) -> Generator[Dict[str, Any], None, None]:
        """
        Perform an incremental walk, yielding only files modified since the last sync.
        """
        # For local filesystem, since we need to check modifications, we run a walk.
        # But we filter results based on st_mtime.
        last_sync_time_str = ctx.cursor_state.get("last_sync_time")
        last_sync_ts = 0.0
        if last_sync_time_str:
            try:
                last_sync_ts = datetime.fromisoformat(last_sync_time_str).timestamp()
            except ValueError:
                pass

        path = ctx.config.get("path")
        if not path or not os.path.isdir(path):
            raise ValueError(f"Invalid sync directory path: {path}")

        active_rel_paths = []

        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('.git', '.obsidian', '.trash')]

            for file in files:
                if file.startswith('.') or not file.lower().endswith(('.md', '.markdown')):
                    continue

                abs_path = os.path.abspath(os.path.join(root, file))
                rel_path = os.path.relpath(abs_path, path)
                active_rel_paths.append(rel_path)

                try:
                    stat_info = os.stat(abs_path)
                    modified = stat_info.st_mtime
                    if modified <= last_sync_ts:
                        # Unmodified, skip yielding
                        continue
                    
                    try:
                        created = stat_info.st_birthtime
                    except AttributeError:
                        created = stat_info.st_ctime
                    size = stat_info.st_size
                except Exception:
                    continue

                parent = os.path.basename(os.path.dirname(abs_path))

                yield {
                    "external_id": rel_path,
                    "absolute_path": abs_path,
                    "relative_path": rel_path,
                    "filename": file,
                    "file_size": size,
                    "created_at_ts": created,
                    "modified_at_ts": modified,
                    "parent_folder": parent,
                    "root_path": path
                }

        # Keep tracking active files in cursor
        ctx.cursor_state["active_ids"] = active_rel_paths
        ctx.cursor_state["last_sync_time"] = datetime.now(timezone.utc).isoformat()

    def watch(self, ctx: SyncContext) -> Generator[Dict[str, Any], None, None]:
        """Amendment 3 - Defer Watch. Watch capability is deferred for future implementation."""
        raise NotImplementedError("Watch capability is not implemented in this milestone.")

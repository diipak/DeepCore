import os
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, Generator, List

from deepcore.core.acquisition.base import (
    BaseConnector,
    SyncContext,
    HealthStatus,
    ConnectorOperation,
    ExecutionRequest,
    ExecutionResponse,
    ConnectorCapabilities,
)

# Check if mdfind CLI is present on PATH (macOS native index)
MDFIND_AVAILABLE = bool(shutil.which("mdfind"))


class SpotlightConnector(BaseConnector):
    """
    Spotlight Connector. TECHNICAL CONTRACT implementation.
    Orchestrates search queries by translating high-level Discovery Strategies
    into native mdfind commands, falling back to glob matching on non-macOS platforms.
    """
    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            supported_operations=[
                ConnectorOperation.SEARCH,
                ConnectorOperation.READ,
            ],
            requires_configuration=True,
            requires_permissions=False,
            supports_pagination=False,
            supports_streaming=False,
            supports_actions=False,
            metadata={"provider": "spotlight", "mdfind_available": MDFIND_AVAILABLE}
        )

    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """
        Stateless live execution adapter over native macOS Spotlight mdfind or fallback scanner.
        """
        op = request.operation
        params = request.parameters or {}
        config = request.context.config or {}
        search_path = params.get("search_path") or params.get("path") or config.get("search_path")

        if op == ConnectorOperation.SEARCH:
            if not search_path or not os.path.isdir(search_path):
                raise ValueError("Operation 'search' requires a valid directory 'search_path' or 'path'.")

            query_term = params.get("query")
            if MDFIND_AVAILABLE:
                if query_term:
                    # Construct Spotlight text search query
                    mdfind_query = f'kMDItemTextContent == "*{query_term}*" || kMDItemFSName == "*{query_term}*"'
                else:
                    mdfind_query = self._build_mdfind_query(config)
                
                paths = self._run_native_mdfind(search_path, mdfind_query, ctx=None)
            else:
                paths = self._run_fallback_scan(search_path, config)
                if query_term:
                    q_lower = query_term.lower()
                    paths = [p for p in paths if q_lower in os.path.basename(p).lower()]

            results = []
            for p in paths:
                if not os.path.exists(p):
                    continue
                try:
                    stat_info = os.stat(p)
                    size = stat_info.st_size
                    modified = stat_info.st_mtime
                except Exception:
                    size = 0
                    modified = 0.0

                results.append({
                    "absolute_path": os.path.abspath(p),
                    "filename": os.path.basename(p),
                    "file_size": size,
                    "modified_at_ts": modified,
                })

            return ExecutionResponse(
                results=results,
                metadata={"count": len(results), "search_path": search_path, "query": query_term},
                diagnostics={"status": "success", "mdfind_used": MDFIND_AVAILABLE}
            )

        elif op == ConnectorOperation.READ:
            target_path = params.get("path") or params.get("absolute_path")
            if not target_path:
                raise ValueError("Operation 'read' requires 'path' parameter.")
            if not os.path.exists(target_path):
                raise FileNotFoundError(f"Path not found: {target_path}")

            try:
                stat_info = os.stat(target_path)
                res_item = {
                    "absolute_path": os.path.abspath(target_path),
                    "filename": os.path.basename(target_path),
                    "is_dir": os.path.isdir(target_path),
                    "file_size": stat_info.st_size,
                    "modified_at_ts": stat_info.st_mtime,
                }
                return ExecutionResponse(
                    results=[res_item],
                    metadata={"count": 1, "path": target_path},
                    diagnostics={"status": "success"}
                )
            except Exception as e:
                raise RuntimeError(f"Failed to inspect metadata for '{target_path}': {e}")

        else:
            raise NotImplementedError(
                f"Operation '{op.value}' is not supported by SpotlightConnector."
            )

    def authenticate(self, credentials: Dict[str, Any]) -> HealthStatus:
        return HealthStatus(state="HEALTHY", message="No authentication required for native index.")

    def health(self, ctx: SyncContext) -> HealthStatus:
        """
        Amendment 4 - Standardized Health Reporting.
        Validates Index Available, Operational, and Discovery Ready states.
        """
        search_path = ctx.config.get("search_path")
        configured = bool(search_path and os.path.isdir(search_path))
        
        # Index Available: mdfind is installed (or mock fallback is active)
        index_available = MDFIND_AVAILABLE
        # Index Operational: can execute a simple query
        index_operational = False
        if MDFIND_AVAILABLE:
            try:
                # Test query: list a single file path
                subprocess.check_output(["mdfind", "-count", 'kMDItemFSName == "nonexistent_test_file"'], timeout=2)
                index_operational = True
            except Exception:
                pass
        else:
            # Fallback mode is always operational
            index_operational = True

        health_state = "HEALTHY"
        messages = []

        if not configured:
            health_state = "CRITICAL"
            messages.append("Status: Not Configured. 'search_path' must point to a valid directory.")
        elif not index_available:
            health_state = "DEGRADED"
            messages.append("Status: Degraded. macOS Spotlight index is not available. Falling back to local file scanner.")
        elif not index_operational:
            health_state = "DEGRADED"
            messages.append("Status: Degraded. macOS Spotlight query system failed to respond.")
        else:
            messages.append("Status: Healthy.")

        last_sync = ctx.cursor_state.get("last_sync_time")
        if last_sync:
            messages.append(f"Last successful sync: {last_sync}")
        else:
            messages.append("No prior synchronization recorded.")

        # Build details dictionary for structural telemetry
        details = {
            "Index Available": index_available,
            "Index Operational": index_operational,
            "Discovery Ready": configured,
            "Knowledge Source Healthy": (health_state == "HEALTHY"),
            "Last Successful Synchronization": last_sync
        }

        return HealthStatus(
            state=health_state,
            message=" | ".join(messages),
            details=details
        )

    def _build_mdfind_query(self, config: Dict[str, Any]) -> str:
        """
        Amendment 3 - Translate high-level Discovery Strategies into native Spotlight terms.
        """
        terms = []

        # 1. File Type Strategy
        file_types = config.get("file_types") or []
        if file_types:
            type_terms = []
            for ext in file_types:
                # Strip leading dot
                clean_ext = ext.lstrip(".")
                type_terms.append(f'kMDItemFSName == "*.{clean_ext}"')
            terms.append(f"({' || '.join(type_terms)})")

        # 2. Tags Strategy
        tags = config.get("tags") or []
        if tags:
            tag_terms = [f'kMDItemUserTags == "{t}"' for t in tags]
            terms.append(f"({' || '.join(tag_terms)})")

        # Fallback default query (all files)
        if not terms:
            return 'kMDItemFSName == "*"'
        return " && ".join(terms)

    def _run_native_mdfind(self, search_path: str, query: str, ctx: SyncContext) -> List[str]:
        """Execute mdfind shell command to discover file paths."""
        cmd = ["mdfind"]
        if search_path:
            cmd.extend(["-onlyin", search_path])
        cmd.append(query)
        
        try:
            output = subprocess.check_output(cmd, timeout=10).decode("utf-8")
            return [p.strip() for p in output.splitlines() if p.strip()]
        except Exception as e:
            if ctx and ctx.logger:
                ctx.logger.error(f"Spotlight mdfind command failed: {e}")
            return []

    def _run_fallback_scan(self, search_path: str, config: Dict[str, Any]) -> List[str]:
        """Glob-based directory scanner fallback for CI/non-macOS testing."""
        file_types = config.get("file_types") or []
        discovered_paths = []
        
        for root, dirs, files in os.walk(search_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.startswith('.'):
                    continue
                # Match file types strategy
                matched = False
                if not file_types:
                    matched = True
                else:
                    for ext in file_types:
                        if file.lower().endswith(ext.lower()):
                            matched = True
                            break
                if matched:
                    discovered_paths.append(os.path.join(root, file))
        return discovered_paths

    def discover(self, ctx: SyncContext) -> Generator[Dict[str, Any], None, None]:
        search_path = ctx.config.get("search_path")
        if not search_path or not os.path.isdir(search_path):
            raise ValueError(f"Invalid search_path: {search_path}")

        # Choose query strategy execution
        if MDFIND_AVAILABLE:
            query = self._build_mdfind_query(ctx.config)
            paths = self._run_native_mdfind(search_path, query, ctx)
        else:
            paths = self._run_fallback_scan(search_path, ctx.config)

        active_paths = []
        for path in paths:
            if not os.path.exists(path):
                continue
            
            active_paths.append(path)
            try:
                stat_info = os.stat(path)
                modified = stat_info.st_mtime
                size = stat_info.st_size
            except Exception:
                modified = datetime.now(timezone.utc).timestamp()
                size = 0

            # Mock macOS tags if fallback, or read from system attributes
            tags = []
            
            yield {
                "absolute_path": path,
                "filename": os.path.basename(path),
                "modified_at_ts": modified,
                "file_size": size,
                "tags": tags
            }

        ctx.cursor_state["active_ids"] = active_paths
        ctx.cursor_state["last_sync_time"] = datetime.now(timezone.utc).isoformat()

    def sync(self, ctx: SyncContext) -> Generator[Dict[str, Any], None, None]:
        """Incremental synchronization. Yields files modified since the last sync."""
        last_sync_str = ctx.cursor_state.get("last_sync_time")
        last_ts = 0.0
        if last_sync_str:
            try:
                last_ts = datetime.fromisoformat(last_sync_str).timestamp()
            except ValueError:
                pass

        search_path = ctx.config.get("search_path")
        if not search_path or not os.path.isdir(search_path):
            raise ValueError(f"Invalid search_path: {search_path}")

        if MDFIND_AVAILABLE:
            query = self._build_mdfind_query(ctx.config)
            paths = self._run_native_mdfind(search_path, query, ctx)
        else:
            paths = self._run_fallback_scan(search_path, ctx.config)

        active_paths = []
        for path in paths:
            if not os.path.exists(path):
                continue
            
            active_paths.append(path)
            try:
                stat_info = os.stat(path)
                modified = stat_info.st_mtime
                if modified <= last_ts:
                    # Unmodified, skip
                    continue
                size = stat_info.st_size
            except Exception:
                continue

            yield {
                "absolute_path": path,
                "filename": os.path.basename(path),
                "modified_at_ts": modified,
                "file_size": size,
                "tags": []
            }

        ctx.cursor_state["active_ids"] = active_paths
        ctx.cursor_state["last_sync_time"] = datetime.now(timezone.utc).isoformat()

    def watch(self, ctx: SyncContext) -> Generator[Dict[str, Any], None, None]:
        raise NotImplementedError("Watch capability is not implemented in this milestone.")

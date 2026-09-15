"""
Scoped Vault Service for DeepCore.

Enforces strict boundary rules for the user's Obsidian knowledge repository:
1. Read-Only access across the general knowledge vault (~/Documents/Notes).
2. Read-Write access strictly jailed to the AI workspace folder (~/Documents/Notes/AI).
   Any attempt to write outside AI/ (e.g. Dev/, root, or parent paths) triggers VaultSecurityError.
3. Path Jail is validated using os.path.realpath to eliminate '..' bypasses and symlink escapes.
4. Syncthing-safe writes: File updates and daily appends use atomic write-to-temp-and-replace
   to avoid race conditions or half-written file states during background Syncthing sweeps.
"""

import os
import fcntl
import logging
import tempfile
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from deepcore2.config import settings

logger = logging.getLogger(__name__)


class VaultSecurityError(PermissionError):
    """Raised when an operation attempts to violate vault boundary rules or escape path jails."""
    pass


class VaultService:
    """Service providing bounded, jail-enforced filesystem operations for Obsidian notes."""

    def __init__(
        self,
        vault_root: Optional[str] = None,
        ai_root: Optional[str] = None,
    ):
        self.vault_root = os.path.realpath(os.path.expanduser(vault_root or settings.VAULT_ROOT))
        self.ai_root = os.path.realpath(os.path.expanduser(ai_root or settings.VAULT_AI_DIR))

    def _resolve_and_validate_read_path(self, rel_path: str) -> str:
        """Resolve path and verify it is strictly contained within vault_root."""
        clean_rel = rel_path.strip().lstrip("/")
        candidate = os.path.realpath(os.path.join(self.vault_root, clean_rel))
        
        # Verify candidate is inside vault_root
        try:
            common = os.path.commonpath([candidate, self.vault_root])
        except ValueError:
            raise VaultSecurityError(f"Path '{rel_path}' is on a different drive or invalid.")

        if common != self.vault_root:
            raise VaultSecurityError(
                f"Read violation: Path '{rel_path}' resolves outside the knowledge vault ({self.vault_root})."
            )
        return candidate

    def _resolve_and_validate_ai_write_path(self, rel_path: str) -> str:
        """
        Resolve path and verify it is strictly contained within ai_root.
        Uses os.path.realpath on both paths to prevent '..' directory traversal and symlink escapes.
        """
        clean_rel = rel_path.strip().lstrip("/")
        # If relative path begins with "AI/", strip it because base is already ai_root
        if clean_rel.startswith("AI/"):
            clean_rel = clean_rel[3:]

        candidate = os.path.realpath(os.path.join(self.ai_root, clean_rel))

        try:
            common = os.path.commonpath([candidate, self.ai_root])
        except ValueError:
            raise VaultSecurityError(f"Path '{rel_path}' is on a different drive or invalid.")

        if common != self.ai_root or candidate == self.ai_root:
            raise VaultSecurityError(
                f"Write violation: DeepCore is strictly forbidden from writing outside AI/ workspace ({self.ai_root}). "
                f"Target path '{rel_path}' resolved to '{candidate}'."
            )
        return candidate

    def read_note(self, rel_path: str) -> str:
        """Read note content from anywhere inside the knowledge vault."""
        resolved = self._resolve_and_validate_read_path(rel_path)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"Note '{rel_path}' not found at '{resolved}'.")
        if not os.path.isfile(resolved):
            raise IsADirectoryError(f"Target '{rel_path}' is a directory, not a note.")

        with open(resolved, "r", encoding="utf-8") as f:
            return f.read()

    def write_ai_note(self, rel_path: str, content: str) -> str:
        """
        Write or overwrite a note strictly within the AI/ workspace.
        Uses atomic write-to-temp-then-replace to prevent Syncthing sync corruption.
        """
        resolved = self._resolve_and_validate_ai_write_path(rel_path)
        target_dir = os.path.dirname(resolved)
        os.makedirs(target_dir, exist_ok=True)

        # Atomic write: write to temp file in same directory, then rename
        temp_file = os.path.join(target_dir, f".tmp_dc_{os.getpid()}_{uuid4().hex[:8]}")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, resolved)
        except Exception as e:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass
            raise IOError(f"Failed to write note to '{resolved}': {e}") from e

        return resolved

    def append_daily_log(
        self,
        entry_text: str,
        title: Optional[str] = None,
        date_str: Optional[str] = None,
    ) -> str:
        """
        Append a timestamped milestone or entry to AI/Daily/YYYY-MM-DD.md.
        Syncthing-safe: uses atomic read-modify-temp-replace with file locking.
        """
        now = datetime.now()
        date_stamp = date_str or now.strftime("%Y-%m-%d")
        time_stamp = now.strftime("%H:%M")
        rel_daily_path = os.path.join("Daily", f"{date_stamp}.md")
        resolved = self._resolve_and_validate_ai_write_path(rel_daily_path)
        target_dir = os.path.dirname(resolved)
        os.makedirs(target_dir, exist_ok=True)

        lock_path = os.path.join(target_dir, f".lock_daily_{date_stamp}")
        temp_file = os.path.join(target_dir, f".tmp_daily_{os.getpid()}_{uuid4().hex[:8]}")

        # Format header and block
        header_title = title or "DeepCore Autonomous Session Note"
        formatted_entry = (
            f"\n\n---\n\n"
            f"### 🕒 [{time_stamp}] {header_title}\n"
            f"{entry_text.strip()}\n"
        )

        try:
            with open(lock_path, "w") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    existing_content = ""
                    if os.path.exists(resolved):
                        with open(resolved, "r", encoding="utf-8") as f:
                            existing_content = f.read()
                    else:
                        existing_content = f"# 📅 Daily Session Log — {date_stamp}\n\n> **DeepCore Knowledge Journal**\n"

                    new_content = existing_content.rstrip() + formatted_entry

                    with open(temp_file, "w", encoding="utf-8") as f:
                        f.write(new_content)
                        f.flush()
                        os.fsync(f.fileno())

                    os.replace(temp_file, resolved)
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
        finally:
            if os.path.exists(lock_path):
                try:
                    os.remove(lock_path)
                except OSError:
                    pass
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass

        return resolved

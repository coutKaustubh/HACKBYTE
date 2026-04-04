"""
tools/code_tools.py — Surgical file reading, searching, and patching over SSH/SFTP.

All operations run on the remote Vultr VM via the shared VMTools SSH client.
"""

from __future__ import annotations
import posixpath
from models.patch import FilePatch, PatchResult


class CodeTools:
    """Wraps an already-connected VMTools instance with code-aware helpers."""

    def __init__(self, vm):
        self._vm = vm                       # VMTools instance (already SSH-connected)
        self.project_root = vm.project_root

    # ── Reading ───────────────────────────────────────────────────────────────

    def read_with_lines(self, path: str, max_lines: int = 500) -> str:
        """Return file content with 1-indexed line numbers prepended.
        
        Example output:
            1: import express from 'express'
            2: const app = express()
        """
        abs_path = self._abs(path)
        raw = self._vm._run(f"cat {abs_path} 2>&1")
        if not raw or "No such file" in raw:
            return f"[CodeTools] File not found: {abs_path}"
        lines = raw.splitlines()[:max_lines]
        return "\n".join(f"{i+1:4d}: {line}" for i, line in enumerate(lines))

    def read_context_around_line(self, path: str, line_num: int, radius: int = 10) -> str:
        """Return `radius` lines before and after `line_num` with line numbers."""
        abs_path = self._abs(path)
        start = max(1, line_num - radius)
        end   = line_num + radius
        raw   = self._vm._run(f"sed -n '{start},{end}p' {abs_path} 2>&1")
        if not raw:
            return f"[CodeTools] Could not read context around line {line_num} in {abs_path}"
        lines = raw.splitlines()
        return "\n".join(f"{start+i:4d}: {line}" for i, line in enumerate(lines))

    def grep_in_file(self, path: str, pattern: str) -> str:
        """Search for a regex pattern inside a remote file, return matching lines."""
        abs_path = self._abs(path)
        out = self._vm._run(f"grep -n '{pattern}' {abs_path} 2>&1")
        return out or f"[CodeTools] No matches for '{pattern}' in {abs_path}"

    def grep_in_project(self, pattern: str, file_glob: str = "*.js *.ts *.mjs *.json") -> str:
        """grep recursively across the whole project for a pattern."""
        out = self._vm._run(
            f"grep -rn '{pattern}' {self.project_root} --include='*.js' "
            f"--include='*.ts' --include='*.mjs' --include='*.json' 2>&1 | head -40"
        )
        return out or f"[CodeTools] No project-wide matches for '{pattern}'"

    def list_with_sizes(self, path: str = "") -> str:
        """ls -la on a directory with human-readable sizes."""
        abs_path = self._abs(path) if path else self.project_root
        return self._vm._run(f"ls -lah {abs_path} 2>&1")

    def file_line_count(self, path: str) -> int:
        """Return the number of lines in a remote file."""
        try:
            out = self._vm._run(f"wc -l < {self._abs(path)} 2>&1")
            return int(out.strip())
        except Exception:
            return 0

    # ── Writing / Patching ────────────────────────────────────────────────────

    def write_full_file(self, path: str, content: str) -> dict:
        """Write complete file content via SFTP. Used when a full rewrite is safer."""
        return self._vm.write_file(path, content)

    def apply_patch(self, patch: FilePatch) -> PatchResult:
        """
        Apply a FilePatch to the remote file hunk by hunk.
        
        Strategy:
          1. Download the file via `cat`
          2. Apply each hunk in reverse line order (so earlier hunks don't shift indices)
          3. Upload the patched content via SFTP
        """
        abs_path = self._abs(patch.file_path)
        raw = self._vm._run(f"cat {abs_path} 2>&1")

        if not raw or "No such file" in raw:
            return PatchResult(
                file_path=abs_path,
                status="FAILED",
                hunks_applied=0,
                hunks_failed=len(patch.hunks),
                details=[f"File not found: {abs_path}"],
            )

        lines   = raw.splitlines()
        details = []
        applied = 0
        failed  = 0

        # Sort hunks in reverse so line indices stay valid as we edit
        for hunk in sorted(patch.hunks, key=lambda h: h.line_start, reverse=True):
            s = hunk.line_start - 1   # convert to 0-indexed
            e = hunk.line_end         # exclusive end

            if s < 0 or e > len(lines):
                details.append(f"  ✗ Hunk L{hunk.line_start}-{hunk.line_end}: out of range (file has {len(lines)} lines)")
                failed += 1
                continue

            replacement_lines = hunk.replacement.splitlines()
            lines[s:e] = replacement_lines
            details.append(f"  ✓ Hunk L{hunk.line_start}-{hunk.line_end}: replaced {e-s} line(s) → {len(replacement_lines)} line(s)")
            applied += 1

        new_content = "\n".join(lines) + "\n"
        write_result = self._vm.write_file(abs_path, new_content)

        if write_result.get("status") != "SUCCESS":
            return PatchResult(
                file_path=abs_path,
                status="FAILED",
                hunks_applied=0,
                hunks_failed=len(patch.hunks),
                details=[f"SFTP write failed: {write_result.get('output')}"],
            )

        return PatchResult(
            file_path=abs_path,
            status="SUCCESS" if failed == 0 else "PARTIAL",
            hunks_applied=applied,
            hunks_failed=failed,
            details=details,
        )

    # ── DB inspection (read-only + safe) ─────────────────────────────────────

    def inspect_db_schema(self, db_type: str = "postgres") -> str:
        """Get a safe overview of the database schema via SSH."""
        if db_type == "postgres":
            cmd = (
                "psql -U postgres -c '\\dt' 2>&1 || "
                "psql -U root -c '\\dt' 2>&1 || "
                "echo 'PostgreSQL not accessible or no tables'"
            )
        elif db_type == "mysql":
            cmd = "mysql -u root -e 'SHOW DATABASES;' 2>&1 || echo 'MySQL not accessible'"
        else:
            cmd = "echo 'Unknown DB type'"
        return self._vm._run(cmd)

    def run_safe_db_query(self, sql: str, db_type: str = "postgres") -> str:
        """
        Run a DB query over SSH — only SELECT and safe UPDATE allowed.
        Raises ValueError for destructive operations.
        """
        _blocked = ["drop ", "delete ", "truncate ", "alter ", "create ", "insert "]
        if any(kw in sql.lower() for kw in _blocked):
            raise ValueError(
                f"[CodeTools] Blocked SQL: operation contains destructive keyword. "
                f"Only SELECT and UPDATE are permitted."
            )

        if db_type == "postgres":
            safe_sql = sql.replace("'", r"\'")
            cmd = f"psql -U postgres -c '{safe_sql}' 2>&1"
        elif db_type == "mysql":
            safe_sql = sql.replace("'", r"\'")
            cmd = f"mysql -u root -e '{safe_sql}' 2>&1"
        else:
            return "[CodeTools] Unknown DB type"

        return self._vm._run(cmd)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _abs(self, path: str) -> str:
        if path.startswith("/"):
            return path
        return posixpath.join(self.project_root, path)

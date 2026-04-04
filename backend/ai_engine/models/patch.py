"""
models/patch.py — Data models for code patch hunks produced by Gemini.
"""
from pydantic import BaseModel
from typing import Optional


class PatchHunk(BaseModel):
    """A single contiguous block of lines to replace in a file."""
    line_start: int          # 1-indexed, inclusive
    line_end:   int          # 1-indexed, inclusive
    original:   str          # what was there (for confirmation/logging)
    replacement: str         # what to write instead


class FilePatch(BaseModel):
    """A complete set of hunks for a single file."""
    file_path:   str
    description: str                  # human-readable summary of the fix
    hunks:       list[PatchHunk]
    confidence:  float = 1.0


class PatchResult(BaseModel):
    """What actually happened when we applied a FilePatch."""
    file_path:  str
    status:     str                   # "SUCCESS" | "PARTIAL" | "FAILED"
    hunks_applied: int
    hunks_failed:  int
    details:    list[str] = []        # per-hunk log lines

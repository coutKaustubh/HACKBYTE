"""
utils/project_tree.py — Remote project file tree cache.

Problem solved:
  Gemini was guessing/hallucinating file paths (e.g. targeting layout.js as an
  entry point) because it had no visibility into what actually exists on the VM.

Solution:
  Cache the real project file tree from the VM and inject it into every Gemini
  prompt so AI only references paths that genuinely exist.

Behaviour:
  - First call: SSH fetch → store in memory + persist to policies/project_tree_cache.json
  - Subsequent calls within TTL: return memory cache (ZERO SSH calls)
  - After TTL: re-fetch, compare SHA-256 hash
      - Same hash   → extend TTL, no tree update logged
      - Changed hash → update tree, log what changed, re-persist
  - execute_node calls invalidate() after any file-modifying action
      → forces a fresh fetch on the next collect cycle
"""

import hashlib
import json
import os
import time
from typing import Optional

# ── Config ─────────────────────────────────────────────────────────────────────
_DEFAULT_TTL_SECS  = 300          # 5 minutes between auto-refresh
_MAX_FILES         = 300          # cap to avoid massive prompts
_PERSIST_PATH      = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "policies", "project_tree_cache.json")
)

# Directories to exclude from the tree (never useful to Gemini)
_EXCLUDE_DIRS = [
    "node_modules", ".git", ".next/cache", "dist", "__pycache__",
    ".cache", "coverage", ".turbo", "build", ".nyc_output",
]


def _build_find_cmd(project_root: str) -> str:
    """Build a `find` command that lists only relevant project files."""
    excludes = " ".join(
        f'-not -path "*/{d}/*"' for d in _EXCLUDE_DIRS
    )
    return (
        f'find {project_root} -type f {excludes} '
        f'| sort | head -{_MAX_FILES} 2>/dev/null'
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class ProjectTreeCache:
    """
    Singleton-safe cache of the remote VM's project file listing.

    Usage:
        tree = tree_cache.get(vm)          # returns string, SSH only on miss
        tree_cache.invalidate()            # force re-fetch on next get()
        changed = tree_cache.has_changed() # True if last refresh updated the tree
    """

    def __init__(self, ttl: int = _DEFAULT_TTL_SECS):
        self._ttl          = ttl
        self._tree: str    = ""
        self._hash: str    = ""
        self._fetched_at   = 0.0
        self._project_root = ""
        self._last_changed = False   # was the tree different on last refresh?

        # Try to hydrate from the local persistence file on startup
        self._load_persisted()

    # ── Public API ─────────────────────────────────────────────────────────────

    def get(self, vm, force: bool = False) -> str:
        """
        Return the project file tree as a newline-separated string.

        Args:
            vm:    VMTools instance (only used on cache miss / refresh)
            force: if True, always re-fetch even if cache is fresh
        """
        if not force and self._is_fresh():
            return self._tree

        self._refresh(vm)
        return self._tree

    def invalidate(self) -> None:
        """Mark cache as stale — next call to get() will re-fetch from VM."""
        self._fetched_at = 0.0
        print("  🌳 [ProjectTree] Cache invalidated — will re-fetch on next collect cycle.")

    def has_changed(self) -> bool:
        """True if the last refresh detected a real tree change."""
        return self._last_changed

    def is_cached(self) -> bool:
        return bool(self._tree)

    def stats(self) -> dict:
        age = round(time.time() - self._fetched_at) if self._fetched_at else None
        lines = self._tree.count("\n") + 1 if self._tree else 0
        return {
            "cached":          self.is_cached(),
            "lines":           lines,
            "age_secs":        age,
            "ttl_secs":        self._ttl,
            "fresh":           self._is_fresh(),
            "project_root":    self._project_root,
        }

    # ── Internal ───────────────────────────────────────────────────────────────

    def _is_fresh(self) -> bool:
        return bool(self._tree) and (time.time() - self._fetched_at) < self._ttl

    def _refresh(self, vm) -> None:
        """Fetch tree from VM, update cache if changed, persist to disk."""
        try:
            root = getattr(vm, "project_root", os.getenv("PROJECT_ROOT", "/root/app"))
            cmd  = _build_find_cmd(root)
            raw  = vm._run(cmd).strip()

            if not raw:
                print("  🌳 [ProjectTree] WARNING: empty tree returned from VM")
                return

            new_hash = _sha256(raw)
            self._last_changed = (new_hash != self._hash)

            if self._last_changed:
                old_lines = self._tree.count("\n") + 1 if self._tree else 0
                new_lines = raw.count("\n") + 1
                delta     = new_lines - old_lines
                sign      = "+" if delta >= 0 else ""
                print(f"  🌳 [ProjectTree] Tree UPDATED — {new_lines} files "
                      f"({sign}{delta} since last fetch). Persisting to disk.")
                self._tree         = raw
                self._hash         = new_hash
                self._project_root = root
                self._persist()
            else:
                print(f"  🌳 [ProjectTree] Tree unchanged ({raw.count(chr(10))+1} files). TTL extended.")

            self._fetched_at = time.time()

        except Exception as e:
            print(f"  🌳 [ProjectTree] Refresh failed: {e} — using stale cache if available.")

    def _persist(self) -> None:
        """Write current tree to local JSON file for persistence across restarts."""
        try:
            os.makedirs(os.path.dirname(_PERSIST_PATH), exist_ok=True)
            with open(_PERSIST_PATH, "w", encoding="utf-8") as f:
                json.dump({
                    "tree":         self._tree,
                    "hash":         self._hash,
                    "fetched_at":   self._fetched_at,
                    "project_root": self._project_root,
                }, f, indent=2)
        except Exception as e:
            print(f"  🌳 [ProjectTree] Persist failed: {e}")

    def _load_persisted(self) -> None:
        """Load tree from disk on startup (avoids SSH call if cache is recent)."""
        try:
            if not os.path.isfile(_PERSIST_PATH):
                return
            with open(_PERSIST_PATH, encoding="utf-8") as f:
                data = json.load(f)
            self._tree         = data.get("tree", "")
            self._hash         = data.get("hash", "")
            self._fetched_at   = float(data.get("fetched_at", 0))
            self._project_root = data.get("project_root", "")
            if self._tree:
                age = round(time.time() - self._fetched_at)
                print(f"  🌳 [ProjectTree] Loaded from disk — {self._tree.count(chr(10))+1} files, "
                      f"age {age}s (TTL={self._ttl}s).")
        except Exception as e:
            print(f"  🌳 [ProjectTree] Could not load persisted cache: {e}")


# ── Module-level singleton ──────────────────────────────────────────────────────
tree_cache = ProjectTreeCache()

"""
utils/cache.py — Simple in-memory LRU cache for expensive Gemini API responses.

Why: Gemini costs money. If the same log fingerprint, file content, or error
context is seen again within the TTL window, we return the cached result and
make ZERO API calls.

Thread safety: Python's GIL protects dict operations. Fine for asyncio + threadpool.
"""

import hashlib
import time
from collections import OrderedDict
from typing      import Any, Optional


# ── Config ─────────────────────────────────────────────────────────────────────
_DEFAULT_TTL      = 600   # seconds — cache entries valid for 10 minutes
_DEFAULT_MAX_SIZE = 128   # max entries before oldest is evicted


class TTLCache:
    """
    Ordered dict-backed cache with per-entry TTL and max-size eviction (LRU style).

    Usage:
        cache = TTLCache(ttl=600, max_size=64)
        key   = cache.make_key("diagnose", logs, snapshot)

        hit   = cache.get(key)
        if hit is None:
            result = expensive_call(...)
            cache.set(key, result)
    """

    def __init__(self, ttl: int = _DEFAULT_TTL, max_size: int = _DEFAULT_MAX_SIZE):
        self._ttl      = ttl
        self._max      = max_size
        self._store: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self.hits   = 0
        self.misses = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            self.misses += 1
            return None
        value, expires_at = self._store[key]
        if time.monotonic() > expires_at:
            del self._store[key]
            self.misses += 1
            return None
        # LRU: move to end on access
        self._store.move_to_end(key)
        self.hits += 1
        return value

    def set(self, key: str, value: Any) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (value, time.monotonic() + self._ttl)
        if len(self._store) > self._max:
            self._store.popitem(last=False)          # evict oldest

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()

    # ── Key builder ───────────────────────────────────────────────────────────

    @staticmethod
    def make_key(*parts: str) -> str:
        """
        Stable SHA-256 key from any number of string parts.
        Truncates each part to 4000 chars to avoid huge keys.
        """
        blob = "\x00".join(str(p)[:4000] for p in parts)
        return hashlib.sha256(blob.encode()).hexdigest()

    # ── Stats ────────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        total = self.hits + self.misses
        rate  = round(self.hits / total * 100, 1) if total else 0.0
        return {
            "entries": len(self._store),
            "hits":    self.hits,
            "misses":  self.misses,
            "hit_rate_pct": rate,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Module-level shared caches (singletons)
# ══════════════════════════════════════════════════════════════════════════════

#: Caches Gemini diagnosis results, keyed by SHA-256(logs + snapshot).
#: TTL=10 min — same error burst within 10 min won't re-diagnose.
diagnosis_cache = TTLCache(ttl=600, max_size=64)

#: Caches Gemini code patches, keyed by SHA-256(file_path + file_content + error_ctx).
#: TTL=30 min — same broken file + same error gets same patch.
patch_cache = TTLCache(ttl=1800, max_size=32)

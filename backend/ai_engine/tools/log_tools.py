"""
Fetch real deploy/app logs over HTTP for the collect node.

Set LOG_SOURCE_URL to any endpoint that returns plain text logs or JSON { "logs": "..." }.
Examples: your own /internal/logs route, a log drain URL, or a small worker that reads Railway exports.
"""

import json
import os
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()


def fetch_deploy_logs() -> Optional[str]:
    url = os.getenv("LOG_SOURCE_URL", "").strip()
    if not url:
        return None

    headers = {}
    token = os.getenv("LOG_SOURCE_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = httpx.get(url, headers=headers, timeout=20.0)
        resp.raise_for_status()
        text = resp.text.strip()
        if not text:
            return None
        # JSON wrapper: {"logs": "..."} or {"lines": [...]}
        if text.startswith("{"):
            try:
                data = json.loads(text)
                if isinstance(data.get("logs"), str):
                    return data["logs"]
                if isinstance(data.get("lines"), list):
                    return "\n".join(str(x) for x in data["lines"])
            except json.JSONDecodeError:
                pass
        return text
    except Exception as e:
        return f"[LOG_SOURCE_URL fetch failed: {e}]"

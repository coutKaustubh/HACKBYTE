"""
tools/fleet.py — Multi-VM fleet management.

Loads VM configurations from policies/fleet.json and manages one VMTools
instance per VM. The background monitor uses VMFleet to poll the entire
fleet in parallel.

fleet.json format:
  [
    {
      "vm_id":        "vultr-prod-01",
      "label":        "Primary Production VM",
      "ip":           "1.2.3.4",          // or "${VULTR_VM_IP}"
      "user":         "root",
      "ssh_key_path": "~/.ssh/id_ed25519",
      "project_root": "/root/app",
      "public_url":   "https://myapp.com",
      "enabled":      true
    }
  ]

Env-var references like "${VARNAME}" are resolved at load time from os.environ.
"""

import json
import os
import re
from typing import Optional

from tools.vm_tools import VMTools, SSHNotConnectedError


_FLEET_JSON = os.path.join(os.path.dirname(__file__), "..", "policies", "fleet.json")
_FLEET_JSON = os.path.normpath(_FLEET_JSON)

# ── Env-var substitution ──────────────────────────────────────────────────────

_ENV_RE = re.compile(r"\$\{([^}]+)\}")


def _resolve(value: str) -> str:
    """Replace ${VAR} references with os.environ values."""
    if not isinstance(value, str):
        return value
    return _ENV_RE.sub(lambda m: os.getenv(m.group(1), m.group(0)), value)


def _resolve_dict(d: dict) -> dict:
    return {k: _resolve(v) if isinstance(v, str) else v for k, v in d.items()}


# ── VMFleet ───────────────────────────────────────────────────────────────────

class VMFleetEntry:
    """A single VM in the fleet with its own VMTools instance."""

    def __init__(self, config: dict):
        self.vm_id        = config["vm_id"]
        self.label        = config.get("label", self.vm_id)
        self.ip           = config.get("ip", "")
        self.project_root = config.get("project_root", "/root/app")
        self.public_url   = config.get("public_url", "")
        self.enabled      = config.get("enabled", True)
        self._config      = config
        self._vm: Optional[VMTools] = None
        self._error: Optional[str] = None

    def connect(self) -> bool:
        """Attempt SSH connection. Returns True on success."""
        if not self.enabled:
            return False
        try:
            # Temporarily override env vars for this VM
            _orig = {
                "VULTR_VM_IP":       os.environ.get("VULTR_VM_IP"),
                "VULTR_VM_USER":     os.environ.get("VULTR_VM_USER"),
                "VULTR_SSH_KEY_PATH":os.environ.get("VULTR_SSH_KEY_PATH"),
                "PROJECT_ROOT":      os.environ.get("PROJECT_ROOT"),
                "PUBLIC_APP_URL":    os.environ.get("PUBLIC_APP_URL"),
            }
            os.environ["VULTR_VM_IP"]        = self._config.get("ip", "")
            os.environ["VULTR_VM_USER"]      = self._config.get("user", "root")
            os.environ["VULTR_SSH_KEY_PATH"] = self._config.get("ssh_key_path", "~/.ssh/id_rsa")
            os.environ["PROJECT_ROOT"]       = self._config.get("project_root", "/root/app")
            os.environ["PUBLIC_APP_URL"]     = self._config.get("public_url", "")
            os.environ["USE_SSH"]            = "true"

            self._vm    = VMTools()
            self._error = None
            return True
        except SSHNotConnectedError as e:
            self._vm    = None
            self._error = str(e)
            return False
        finally:
            # Restore original env vars
            for k, v in _orig.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    @property
    def vm(self) -> Optional[VMTools]:
        return self._vm

    @property
    def connected(self) -> bool:
        return self._vm is not None

    def status_dict(self) -> dict:
        return {
            "vm_id":     self.vm_id,
            "label":     self.label,
            "ip":        self.ip,
            "enabled":   self.enabled,
            "connected": self.connected,
            "error":     self._error,
        }


class VMFleet:
    """
    Manages the full fleet of VMs defined in policies/fleet.json.

    Usage:
        fleet = VMFleet()
        fleet.connect_all()
        for entry in fleet.connected_vms():
            errors = entry.vm._run("journalctl -p err -n 20 --no-pager")
    """

    def __init__(self):
        self._entries: list[VMFleetEntry] = []
        self._load()

    def _load(self) -> None:
        try:
            with open(_FLEET_JSON, encoding="utf-8") as f:
                raw = json.load(f)
            for cfg in raw:
                if cfg.get("enabled", True):
                    self._entries.append(VMFleetEntry(_resolve_dict(cfg)))
        except FileNotFoundError:
            print(f"[VMFleet] fleet.json not found at {_FLEET_JSON} — fleet disabled.")
        except Exception as e:
            print(f"[VMFleet] Failed to load fleet.json: {e}")

    def connect_all(self) -> None:
        """Connect SSH for all enabled VMs. Failures are logged but don't crash."""
        for entry in self._entries:
            ok = entry.connect()
            label = entry.label or entry.vm_id
            if ok:
                print(f"[VMFleet] ✅ Connected: {label} ({entry.ip})")
            else:
                print(f"[VMFleet] ❌ Failed:    {label} ({entry.ip}) — {entry._error}")

    def connected_vms(self) -> list[VMFleetEntry]:
        return [e for e in self._entries if e.connected]

    def all_vms(self) -> list[VMFleetEntry]:
        return self._entries

    def fleet_status(self) -> list[dict]:
        return [e.status_dict() for e in self._entries]

    def __len__(self) -> int:
        return len(self._entries)

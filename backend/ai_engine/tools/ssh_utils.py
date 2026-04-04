"""
tools/ssh_utils.py — Low-level SSH/SFTP utilities shared across vm_tools and code_tools.

Isolating these means:
  - VMTools and CodeTools only hold business logic, not SSH plumbing
  - SSH connection params can be changed in one place
  - Helpers are unit-testable without a live SSH connection
"""

import os
import posixpath
from dotenv import load_dotenv

load_dotenv()


# ── Path helpers ──────────────────────────────────────────────────────────────

def resolve_remote_path(path: str, project_root: str) -> str:
    """
    If `path` is already absolute, return it as-is.
    Otherwise join it with `project_root`.
    """
    if path.startswith("/"):
        return path
    return posixpath.join(project_root, path)


def strip_trailing_slash(path: str) -> str:
    return path.rstrip("/")


# ── SSH client factory ────────────────────────────────────────────────────────

def build_ssh_client():
    """
    Create, configure, and connect a Paramiko SSH client using env vars.
    Raises SSHConnectionError on failure.
    """
    import paramiko

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    host    = os.getenv("VULTR_VM_IP")
    user    = os.getenv("VULTR_VM_USER")
    key     = os.path.expanduser(os.getenv("VULTR_SSH_KEY_PATH", "~/.ssh/id_rsa"))

    try:
        client.connect(hostname=host, username=user, key_filename=key)
        return client
    except Exception as e:
        raise SSHConnectionError(
            f"[SSH] Connection to {host} as {user} with key {key} FAILED: {e}"
        ) from e


# ── SSH runner ────────────────────────────────────────────────────────────────

def run_ssh_command(client, cmd: str) -> str:
    """
    Execute a shell command over an existing SSH connection.
    Returns stdout if non-empty, otherwise stderr.
    """
    _, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    return out if out else err


# ── SFTP writer ───────────────────────────────────────────────────────────────

def sftp_write(client, remote_path: str, content: str) -> dict:
    """
    Write `content` to `remote_path` on the SSH server via SFTP.
    Returns a result dict compatible with VMTools action responses.
    """
    try:
        sftp = client.open_sftp()
        with sftp.file(remote_path, "w") as f:
            f.write(content)
        sftp.close()
        return {
            "action": "write_file",
            "target": remote_path,
            "status": "SUCCESS",
            "output": "File written remotely via SFTP.",
        }
    except Exception as e:
        return {
            "action": "write_file",
            "target": remote_path,
            "status": "FAILED",
            "output": f"SFTP write failed: {e}",
        }


# ── Error types ───────────────────────────────────────────────────────────────

class SSHConnectionError(RuntimeError):
    """Raised when building or using the SSH connection fails."""
    pass

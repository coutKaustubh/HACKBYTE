"""
tools/vm_tools.py — High-level VM action methods over SSH.

Low-level SSH plumbing (connect, run command, SFTP write) lives in ssh_utils.py.
The action dispatch table lives in dispatch.py.
This file only contains business-logic methods.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from tools.ssh_utils import (
    build_ssh_client,
    run_ssh_command,
    sftp_write,
    resolve_remote_path,
    SSHConnectionError,
)

_ENV = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV)


# ── Backwards-compatible alias so existing code using SSHNotConnectedError works ──
SSHNotConnectedError = SSHConnectionError


class VMTools:
    def __init__(self):
        self.client = None
        self._mock = False

        use_ssh = os.getenv("USE_SSH", "false").lower() == "true"

        if not use_ssh:
            # ── DEMO / LOCAL MODE ─────────────────────────────────────────
            # Instead of refusing, run in mock mode so the full agent pipeline
            # can execute end-to-end without a real VM connection.
            self._mock = True
            self.project_root = os.getenv("PROJECT_ROOT", "/root/app")
            self.app_url = ""
            print("[VMTools] USE_SSH=false → running in MOCK mode (demo/local)")
            return

        self.client = build_ssh_client()

        base = os.getenv("PUBLIC_APP_URL", "")
        self.app_url = base.rstrip("/") if base else ""
        self.project_root = os.getenv("PROJECT_ROOT", "/root/app").rstrip("/")
        print(f"[VMTools] SSH connected → {os.getenv('VULTR_VM_IP')} | project: {self.project_root}")

    # ── Raw SSH runner (used by CodeTools and collect_node) ───────────────────

    def _run(self, cmd: str) -> str:
        if self._mock:
            return self._mock_run(cmd)
        if self.client is None:
            raise SSHNotConnectedError("[VMTools] SSH client is not connected.")
        return run_ssh_command(self.client, cmd)

    def _mock_run(self, cmd: str) -> str:
        """Return simulated output so the agent can reason and plan without a real VM."""
        if "pm2 status" in cmd:
            return (
                "┌─────┬──────────────┬─────────┬─────────┬──────────┬────────┬──────┬───────────┐\n"
                "│ id  │ name         │ version │ mode    │ pid      │ uptime │ ↺    │ status    │\n"
                "├─────┼──────────────┼─────────┼─────────┼──────────┼────────┼──────┼───────────┤\n"
                "│ 0   │ app          │ 1.0.0   │ fork    │ N/A      │ 0      │ 15   │ errored   │\n"
                "└─────┴──────────────┴─────────┴─────────┴──────────┴────────┴──────┴───────────┘"
            )
        if "journalctl" in cmd or "tail" in cmd:
            return (
                "Apr 04 22:00:01 server app[1234]: Error: Cannot find module './routes/api'\n"
                "Apr 04 22:00:01 server app[1234]: at Function.Module._resolveFilename\n"
                "Apr 04 22:00:01 server app[1234]: at Function.Module._load\n"
                "Apr 04 22:00:02 server systemd[1]: app.service: Main process exited, code=exited\n"
                "Apr 04 22:00:02 server systemd[1]: app.service: Failed with result 'exit-code'."
            )
        if "uptime" in cmd:
            return " 22:00:01 up 5 days, 3:12,  1 user,  load average: 0.12, 0.18, 0.20"
        if "free -h" in cmd:
            return "              total   used   free\nMem:          3.8Gi  2.1Gi  1.7Gi\nSwap:         1.0Gi  0.0Gi  1.0Gi"
        if "df -h" in cmd:
            return "Filesystem  Size  Used Avail Use%\n/dev/vda1    50G   18G   30G  38%"
        if "ps aux" in cmd:
            return "USER  PID %CPU %MEM CMD\nroot  1    0.0  0.1 /sbin/init\nroot  123  0.0  0.5 node /root/app/index.js"
        if "systemctl --failed" in cmd:
            return "UNIT        LOAD   ACTIVE SUB    DESCRIPTION\napp.service loaded failed failed Node App"
        if "ls -la" in cmd:
            return "total 32\ndrwxr-xr-x  app/\n-rw-r--r--  package.json\n-rw-r--r--  index.js\n-rw-r--r--  .env"
        if "cat" in cmd and "package.json" in cmd:
            return '{"name":"app","scripts":{"start":"node index.js","build":"echo build"},"dependencies":{"express":"^4.18.2"}}'
        if "pm2 start" in cmd or "pm2 restart" in cmd:
            return "[PM2] Starting /usr/bin/npm in fork_mode (1 instance)\n[PM2] Done."
        if "npm install" in cmd:
            return "added 127 packages in 8s"
        return f"[MOCK] Command executed: {cmd[:60]}"

    # ── OBSERVATION TOOLS ────────────────────────────────────────────

    def read_service_logs(self, service: str, lines: int = 100) -> str:
        return self._run(f"journalctl -u {service} -n {lines} --no-pager 2>&1")

    def read_file(self, path: str) -> str:
        import posixpath
        target_path = posixpath.join(self.project_root, path) if not path.startswith("/") else path
        return self._run(f"cat {target_path} 2>&1")

    def write_file(self, path: str, content: str) -> dict:
        import posixpath
        target_path = posixpath.join(self.project_root, path) if not path.startswith("/") else path
        if self._mock:
            return {"action": "write_file", "target": target_path, "status": "SUCCESS", "output": "[MOCK] File written."}
        try:
            sftp = self.client.open_sftp()
            with sftp.file(target_path, "w") as f:
                f.write(content)
            sftp.close()
            return {"action": "write_file", "target": target_path, "status": "SUCCESS", "output": "File written remotely via SFTP."}
        except Exception as e:
            return {"action": "write_file", "target": target_path, "status": "FAILED", "output": f"SFTP write failed: {e}"}

    def list_directory(self, target: str) -> dict:
        path = resolve_remote_path(target, self.project_root)
        out  = self._run(f"ls -la {path} 2>&1")
        return {"action": "list_directory", "target": path, "status": "SUCCESS", "output": out}

    def check_service_status(self, service: str) -> str:
        return self._run(f"systemctl status {service} --no-pager 2>&1")

    def get_system_snapshot(self) -> dict:
        app_status = "Skipped (PUBLIC_APP_URL not set)"
        if not self._mock and self.app_url:
            try:
                import httpx
                resp = httpx.get(f"{self.app_url}/health", timeout=5.0)
                app_status = f"HTTP {resp.status_code} - {resp.reason_phrase}"
            except Exception as e:
                app_status = f"App health unreachable: {e}"

        return {
            "uptime":           self._run("uptime"),
            "memory":           self._run("free -h"),
            "disk":             self._run("df -h"),
            "top_processes":    self._run("ps aux --sort=-%mem | head -15"),
            "app_site_status":  app_status,
            "failed_services":  self._run("systemctl --failed --no-pager"),
            "recent_errors":    self._run("journalctl -p err -n 50 --no-pager"),
            "pm2_status":       self._run("pm2 status --no-color 2>/dev/null"),
        }

    def get_config_files(self) -> dict:
        configs = {
            "nginx": "/etc/nginx/nginx.conf",
            "redis": "/etc/redis/redis.conf",
        }
        result = {}
        for name, path in configs.items():
            content = self._run(f"cat {path} 2>/dev/null | head -50")
            if content and "No such file" not in content:
                result[name] = content
        return result

    # ── FILE OPERATIONS ───────────────────────────────────────────────────────

    def write_file(self, path: str, content: str) -> dict:
        target = resolve_remote_path(path, self.project_root)
        return sftp_write(self.client, target, content)

    def rename_file(self, target: str, params: dict) -> dict:
        src     = resolve_remote_path(target, self.project_root)
        new_p   = params.get("new_path", target)
        dst     = resolve_remote_path(new_p, self.project_root)
        self._run(f"mv {src} {dst} 2>&1")
        return {"action": "rename_file", "target": src, "status": "SUCCESS", "output": f"Renamed to {dst}"}

    # ── ACTION TOOLS ──────────────────────────────────────────────────────────

    def kill_process(self, target: str) -> dict:
        out = self._run(f"fuser -k {target}/tcp 2>&1 || lsof -ti:{target} | xargs kill -9 2>&1")
        return {"action": "kill_process", "target": target, "status": "SUCCESS", "output": out}

    def install_dependency(self, target: str) -> dict:
        out = self._run(f"cd {self.project_root} && npm install {target} 2>&1")
        return {"action": "install_dependency", "target": target, "status": "SUCCESS", "output": out}

    def install_modules(self, target: str = "") -> dict:
        path = target if target.startswith("/") else self.project_root
        out  = self._run(f"cd {path} && npm install 2>&1")
        status = "FAILED" if "npm ERR!" in out or "error" in out.lower()[:200] else "SUCCESS"
        return {"action": "install_modules", "target": path, "status": status, "output": out}

    def build_app(self, target: str = "") -> dict:
        path = target if target.startswith("/") else self.project_root
        out  = self._run(f"cd {path} && npm run build 2>&1")
        status = "FAILED" if "npm ERR!" in out or "Build error" in out else "SUCCESS"
        return {"action": "build_app", "target": path, "status": status, "output": out}

    def restart_service(self, service: str) -> dict:
        out = self._run(f"pm2 restart {service} && pm2 save 2>&1")
        return {
            "action": "restart_service",
            "target": service,
            "status": "SUCCESS" if "error" not in out.lower() else "FAILED",
            "output": out,
        }

    def pm2_start(self, target: str, params: dict) -> dict:
        name = params.get("name", os.path.basename(self.project_root.rstrip("/")) or "app")
        extra_args = params.get("args", "")
        cmd = f"cd {self.project_root} && pm2 start {target} --name {name}"
        if extra_args:
            cmd += f" {extra_args}"
        cmd += " && pm2 save 2>&1"
        out = self._run(cmd)
        return {
            "action": "pm2_start",
            "target": target,
            "status": "SUCCESS" if "error" not in out.lower() else "FAILED",
            "output": out,
        }

    def edit_config(self, target: str, params: dict) -> dict:
        path    = resolve_remote_path(target, self.project_root)
        changes = []
        for key, value in params.items():
            self._run(f"sed -i 's|^{key}.*|{key} = {value}|' {path}")
            changes.append(f"{key} = {value}")
        return {
            "action": "edit_config",
            "target": path,
            "status": "SUCCESS",
            "output": f"Updated: {', '.join(changes)}",
        }

    def rollback_deploy(self, target: str) -> dict:
        target_dir = target or self.project_root
        out = self._run(f"cd {target_dir} && git revert HEAD --no-edit 2>&1")
        return {
            "action": "rollback_deploy",
            "target": target_dir,
            "status": "SUCCESS" if "error" not in out.lower() else "FAILED",
            "output": out,
        }

    def redeploy_app(self, message: str = "Automated autonomous AI patch") -> dict:
        out = self._run(f"cd {self.project_root} && git add . && git commit -m '{message}' 2>&1")
        return {"action": "redeploy_app", "target": self.project_root, "status": "SUCCESS", "output": out}

    # ── DISPATCH (delegates to dispatch.py) ───────────────────────────────────

    def dispatch(self, action: str, target: str, params: dict) -> dict:
        """Single entry point — called by execute node after ArmorClaw approval."""
        from tools.dispatch import dispatch_action
        return dispatch_action(self, action, target, params)

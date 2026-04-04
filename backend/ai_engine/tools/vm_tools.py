import os
from dotenv import load_dotenv

load_dotenv()


class VMTools:
    def __init__(self):
        self.use_ssh = os.getenv("USE_SSH", "false").lower() == "true"
        self.client = None

        if self.use_ssh:
            import paramiko

            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                self.client.connect(
                    hostname=os.getenv("VULTR_VM_IP"),
                    username=os.getenv("VULTR_VM_USER"),
                    key_filename=os.path.expanduser(
                        os.getenv("VULTR_SSH_KEY_PATH", "~/.ssh/id_rsa")
                    ),
                )
            except Exception as e:
                print(f"SSH via Paramiko failed: {e}. Falling back to simulation.")
                self.use_ssh = False
                self.client = None

        # Public URL for /health checks: explicit env
        base = os.getenv("PUBLIC_APP_URL")
        self.app_url = (base or "https://your-app.com").rstrip("/")
        
        self.project_root = os.getenv("PROJECT_ROOT", "/root/url-short").rstrip("/")

        print(f"[VMTools] Running in {'SSH' if self.use_ssh else 'SIMULATION'} mode")

    def _run(self, cmd: str) -> str:
        if self.use_ssh and self.client is not None:
            _, stdout, stderr = self.client.exec_command(cmd)
            out = stdout.read().decode().strip()
            err = stderr.read().decode().strip()
            return out if out else err

        # SIMULATION MODE (Safe fallback — no systemd/journalctl)
        mock_responses = {
            "uptime": "up 2 hours, load average: 0.20, 0.10, 0.05",
            "free -h": "              total        used        free\nMem:           1.0Gi       512Mi       512Mi",
            "df -h": "Filesystem      Size  Used Avail Use% Mounted on\n/dev/root       5.0G  1.0G  4.0G  20% /",
            "systemctl --failed": "0 loaded units listed. Pass --all to see loaded but inactive units, too.",
        }

        for key in mock_responses:
            if key in cmd:
                return mock_responses[key]

        if "journalctl" in cmd:
            return (
                "[SIMULATED] -- Logs begin --\n"
                "Apr 04 10:00:00 host postgres[123]: FATAL: could not open file \"base/16384/2619\": No such file\n"
                "Apr 04 10:00:01 host systemd[1]: postgresql.service: Failed with result 'exit-code'.\n"
                "[SIMULATED] -- end --"
            )

        if "ps aux" in cmd or "ps aux " in cmd:
            return (
                "[SIMULATED]\n"
                "USER  PID %CPU %MEM    VSZ   RSS TTY  STAT START   TIME COMMAND\n"
                "root  401  2.1 10.0 123456 89012 ?    Ss   09:00  0:05 /usr/lib/postgresql/14/bin/postgres\n"
            )

        if "systemctl status" in cmd:
            return (
                "[SIMULATED] postgresql.service - PostgreSQL RDBMS\n"
                "   Loaded: loaded\n"
                "   Active: failed (Result: exit-code)"
            )

        if "systemctl restart" in cmd:
            return ""

        if "systemctl is-active" in cmd:
            return "active"

        if "sed -i" in cmd:
            return ""

        if "git revert" in cmd:
            return "[SIMULATED] Revert successful."

        if cmd.strip().startswith("cat ") or "cat " in cmd[:20]:
            return (
                "# [SIMULATED] sample config\n"
                "max_connections = 100\n"
                "shared_buffers = 128MB\n"
            )

        return f"[SIMULATED] Executed: {cmd}"

    # ── OBSERVATION TOOLS (always allowed) ──────────────────────

    def read_service_logs(self, service: str, lines: int = 100) -> str:
        return self._run(f"journalctl -u {service} -n {lines} --no-pager 2>&1")

    def read_file(self, path: str) -> str:
        import posixpath
        target_path = posixpath.join(self.project_root, path) if not path.startswith("/") else path
        
        if self.use_ssh and self.client is not None:
            return self._run(f"cat {target_path} 2>&1")
        # SIMULATION FALLBACK
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"[SIMULATED FAIL] {e} (Tried: {target_path})"

    def write_file(self, path: str, content: str) -> dict:
        import posixpath
        target_path = posixpath.join(self.project_root, path) if not path.startswith("/") else path
        
        if self.use_ssh and self.client is not None:
            try:
                sftp = self.client.open_sftp()
                with sftp.file(target_path, 'w') as f:
                    f.write(content)
                sftp.close()
                return {
                    "action": "write_file",
                    "target": target_path,
                    "status": "SUCCESS",
                    "output": "File written remotely on Vultr via SFTP."
                }
            except Exception as e:
                # Try creating the directory if it doesn't exist
                return {"status": "FAILED", "output": f"SFTP write failed: {e} at {target_path}"}

        # SIMULATION FALLBACK
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"action": "write_file", "target": target_path, "status": "SUCCESS", "output": "File written locally (Simulation)."}
        except Exception as e:
            return {"status": "FAILED", "output": str(e)}

    def list_directory(self, target: str) -> dict:
        import posixpath
        target_path = posixpath.join(self.project_root, target) if not target.startswith("/") else target
        out = self._run(f"ls -la {target_path} 2>&1")
        return {"action": "list_directory", "target": target_path, "status": "SUCCESS", "output": out}

    def rename_file(self, target: str, params: dict) -> dict:
        import posixpath
        target_path = posixpath.join(self.project_root, target) if not target.startswith("/") else target
        new_path = params.get("new_path", target)
        new_target = posixpath.join(self.project_root, new_path) if not new_path.startswith("/") else new_path
        out = self._run(f"mv {target_path} {new_target} 2>&1")
        return {"action": "rename_file", "target": target_path, "status": "SUCCESS", "output": f"Renamed to {new_target}"}

    def kill_process(self, target: str) -> dict:
        out = self._run(f"fuser -k {target}/tcp 2>&1")
        if "not found" in out or "fuser" in out.lower():
            out = self._run(f"lsof -ti:{target} | xargs kill -9 2>&1")
        return {"action": "kill_process", "target": target, "status": "SUCCESS", "output": f"Killed processes on port {target}"}

    def install_dependency(self, target: str) -> dict:
        out = self._run(f"cd {self.project_root} && npm install {target} 2>&1")
        return {"action": "install_dependency", "target": target, "status": "SUCCESS", "output": out}

    def check_service_status(self, service: str) -> str:
        return self._run(f"systemctl status {service} --no-pager 2>&1")

    def get_system_snapshot(self) -> dict:
        app_status = "Skipped (no PUBLIC_APP_URL)"
        if self.app_url and "your-app" not in self.app_url:
            try:
                import httpx

                health_url = f"{self.app_url}/health"
                resp = httpx.get(health_url, timeout=5.0)
                app_status = f"HTTP {resp.status_code} - {resp.reason_phrase}"
            except Exception as e:
                app_status = f"App health unreachable: {e}"

        return {
            "uptime": self._run("uptime"),
            "memory": self._run("free -h"),
            "disk": self._run("df -h"),
            "top_processes": self._run("ps aux --sort=-%mem | head -15"),
            "app_site_status": app_status,
            "failed_services": self._run("systemctl --failed --no-pager"),
            "recent_errors": self._run("journalctl -p err -n 50 --no-pager"),
        }

    def get_config_files(self) -> dict:
        configs = {
            "postgresql": "/etc/postgresql/14/main/postgresql.conf",
            "nginx": "/etc/nginx/nginx.conf",
            "redis": "/etc/redis/redis.conf",
        }
        result = {}
        for name, path in configs.items():
            content = self._run(f"cat {path} 2>/dev/null | head -50")
            if "No such file" not in content:
                result[name] = content
        return result

    # ── ACTION TOOLS (only run if ArmorClaw approves) ────────────

    def restart_service(self, service: str) -> dict:
        out = self._run(f"pm2 restart {service} 2>&1")
        if "command not found" in out or "errored" in out.lower():
            # fallback to systemd
            self._run(f"systemctl restart {service}")
            status = self._run(f"systemctl is-active {service}")
            return {
                "action": "restart_service",
                "target": service,
                "status": "SUCCESS" if status == "active" else "FAILED",
                "output": f"pm2 failed, fallback systemctl {service} is now {status}",
            }
        return {
            "action": "restart_service",
            "target": service,
            "status": "SUCCESS" if "error" not in out.lower() else "FAILED",
            "output": out,
        }

    def edit_config(self, target: str, params: dict) -> dict:
        import posixpath
        target_path = posixpath.join(self.project_root, target) if not target.startswith("/") else target
        changes = []
        for key, value in params.items():
            self._run(f"sed -i 's|^{key}.*|{key} = {value}|' {target_path}")
            changes.append(f"{key} = {value}")
        return {
            "action": "edit_config",
            "target": target_path,
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
        if self.use_ssh and self.client is not None:
            out = self._run(f"cd {self.project_root} && git add . && git commit -m '{message}' 2>&1")
            return {"action": "redeploy_app", "target": self.project_root, "status": "SUCCESS", "output": out}

        import subprocess
        try:
            cmd = f'git add . && git commit -m "{message}" && git push'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0 or "nothing to commit" in result.stdout:
                return {"action": "redeploy_app", "target": "git", "status": "SUCCESS", "output": result.stdout}
            return {"action": "redeploy_app", "target": "git", "status": "FAILED", "output": result.stderr or result.stdout}
        except Exception as e:
            return {"action": "redeploy_app", "target": "git", "status": "FAILED", "output": str(e)}

    def dispatch(self, action: str, target: str, params: dict) -> dict:
        """Single entry point — called by execute node after ArmorClaw approval"""
        dispatch_map = {
            "restart_service": lambda: self.restart_service(target),
            "edit_config": lambda: self.edit_config(target, params),
            "fix_import_path": lambda: self.edit_config(target, params),
            "rollback_deploy": lambda: self.rollback_deploy(target),
            "redeploy_app": lambda: self.redeploy_app(params.get("message", "AI Patch")),
            "read_logs": lambda: {"output": self.read_service_logs(target)},
            "read_file": lambda: {"output": self.read_file(target)},
            "write_file": lambda: self.write_file(target, params.get("content", "")),
            "create_model_file": lambda: self.write_file(target, params.get("content", "")),
            "list_directory": lambda: self.list_directory(target),
            "rename_file": lambda: self.rename_file(target, params),
            "kill_process": lambda: self.kill_process(target),
            "fix_missing_module": lambda: self.install_dependency(target),
            "install_dependency": lambda: self.install_dependency(target),
        }
        fn = dispatch_map.get(action)
        if not fn:
            return {"status": "FAILED", "output": f"Unknown action: {action}"}
        return fn()

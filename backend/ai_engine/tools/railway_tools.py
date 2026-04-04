import os
import subprocess
from dotenv import load_dotenv

load_dotenv()

class RailwayTools:
    """Tool to fetch logs directly from Railway using the Railway CLI."""
    def __init__(self):
        self.token = os.getenv("RAILWAY_TOKEN")
        self.is_enabled = bool(self.token)

    def _run_cli(self, args: list) -> str:
        if not self.is_enabled:
            return "[Railway] Token not found in .env. Skipping."
        
        env = os.environ.copy()
        # Inject standard token for headless CI/CD authentication
        env["RAILWAY_TOKEN"] = self.token
        
        try:
            # We add timeout to prevent hanging if logs tries to stream indefinitely
            result = subprocess.run(["railway"] + args, env=env, capture_output=True, text=True, timeout=15)
            if result.returncode != 0:
                err = result.stderr.strip()
                if "Not logged in" in err:
                    return "[Railway Error] Invalid token or project not linked."
                return f"[Railway Error] {err}"
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return "[Railway Error] Command timed out while fetching logs."
        except FileNotFoundError:
            return "[Railway Error] 'railway' CLI is not installed on this system. Please run 'npm i -g @railway/cli'."
        except Exception as e:
            return f"[Railway Error] Exception: {str(e)}"

    def get_logs(self) -> str:
        """Fetch general deployment/environment logs from Railway using Railway CLI."""
        # Grab standard logs
        raw = self._run_cli(["logs"])
        if not raw or "[Railway" in raw:
            return raw
            
        # Trim to last 150 lines so we don't blow up Gemini context
        lines = raw.split("\n")
        return "\n".join(lines[-150:])

    def get_error_logs(self) -> str:
        """Fetch error-specific logs using basic filtering to simulate @level:error."""
        raw_logs = self._run_cli(["logs"])
        if "[Railway" in raw_logs:
            return raw_logs
            
        lines = raw_logs.split("\n")
        # Filter logic to pull out lines indicating errors or HTTP 5xx responses
        error_lines = [
            l for l in lines 
            if "error" in l.lower() 
            or "fail" in l.lower() 
            or "exception" in l.lower()
            or "500" in l
            or "502" in l
            or "503" in l
            or "level:error" in l.lower()
        ]
        
        if not error_lines:
            return "No prominent error logs detected in the recent stream."
            
        return "\n".join(error_lines[-100:])

    def get_http_logs(self, path: str = None) -> str:
        """Fetch HTTP specific logs (e.g., slow requests)."""
        raw_logs = self._run_cli(["logs"])
        if "[Railway" in raw_logs:
            return raw_logs
            
        lines = raw_logs.split("\n")
        http_lines = [
            l for l in lines 
            if "HTTP" in l 
            or (path and path in l) 
            or "status" in l.lower()
        ]
        return "\n".join(http_lines[-100:])

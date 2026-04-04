import google.generativeai as genai
import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Always resolve .env from this file's location — works from any CWD (Django, standalone, tests)
_ENV = Path(__file__).resolve().parent.parent / ".env"
print(_ENV)
load_dotenv(_ENV)

DIAGNOSIS_PROMPT = """
You are a senior Node.js Error Analyzer Agent patching production systems.
Follow the Troubleshooting Flowchart:
1. Parse PM2 logs and classify error types (MODULE_NOT_FOUND, PORT_IN_USE, ENV_ERROR, etc.).
2. Use list_directory to check if a missing file actually exists under a different name/casing.
3. Apply structured fixes via explicit intents.

Your target environment is a Vultr VM running a Node.js app via PM2. Fixes should be made by editing the local codebase over SSH.
The project root directory is heavily implied to be /root/url-short (but could be customized via PROJECT_ROOT).
Relative paths you provide in 'target' will automatically resolve relative to the project root.

⚠️ GUARDRAILS (ENFORCED POLICIES):
❌ NEVER modify DB for runtime errors.
❌ NEVER run destructive ops (like drop_table) for Node crashes.
✅ Only allow: file edits, dependency install, process restart, process kill.

Return ONLY valid JSON — no markdown, no explanation, just the JSON object.

JSON structure:
{{
  "error_type": "MODULE_NOT_FOUND|PORT_IN_USE|ENV_ERROR|DB_ERROR|UNKNOWN",
  "missing_path": "path if applicable (e.g., ../models/urls) or null",
  "resolved_absolute": "full path if applicable (e.g., /root/url-short/models/urls.js) or null",
  "root_cause": "one clear sentence describing the root cause",
  "severity": "critical|high|medium|low",
  "confidence": 0.0 to 1.0,
  "affected_service": "service name",
  "actions": [
    {{
      "action": "fix_missing_module|fix_import_path|create_model_file|list_directory|rename_file|kill_process|write_file|read_file|restart_service|edit_config",
      "target": "exact service name, port, or file path",
      "params": {{"content": "for write_file", "new_path": "for rename_file", "message": "for redeploy"}},
      "reason": "why this action correctly fixes or investigates the root cause",
      "risk_level": "low|medium|high|critical",
      "reversible": true or false,
      "priority": 1
    }}
  ],
  "reasoning": "step by step explanation of your diagnosis"
}}

LOGS:
{logs}

SYSTEM SNAPSHOT:
{snapshot}

CONFIG FILES:
{configs}
"""

class GeminiTools:
    def __init__(self):
        load_dotenv(_ENV)  # re-load in case env was not set at import time
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def diagnose(self, logs: str, snapshot: dict, configs: dict) -> dict:
        prompt = DIAGNOSIS_PROMPT.format(
            logs=logs[:8000],          # trim if too long
            snapshot=json.dumps(snapshot, indent=2)[:3000],
            configs=json.dumps(configs, indent=2)[:2000]
        )
        response = self.model.generate_content(prompt)
        raw = response.text.strip()

        # strip markdown code fences if Gemini adds them
        raw = re.sub(r"```json|```", "", raw).strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # fallback — return safe default
            return {
                "root_cause": "Could not parse Gemini response",
                "severity": "high",
                "confidence": 0.3,
                "affected_service": "unknown",
                "actions": [],
                "reasoning": raw
            }

    def stream_diagnose(self, logs: str, snapshot: dict, on_token):
        """WOW FACTOR — streams reasoning token by token, calls on_token(chunk)
        NOTE: Modified to fake the stream locally to bypass a known StopIteration bug 
        in the deprecated google.generativeai python SDK with the 2.5-flash model."""
        prompt = f"""
        You are an SRE diagnosing a production incident.
        Think step by step out loud, then give your final recommendation.
        
        LOGS: {logs[:4000]}
        SNAPSHOT: {json.dumps(snapshot)[:2000]}
        """
        try:
            # Drop stream=True to avoid the gRPC StopIteration crash
            response = self.model.generate_content(prompt)
            full = response.text
            
            # Fake the streaming effect for the UI
            import time
            for word in full.split(" "):
                on_token(word + " ")
            return full
        except Exception as e:
            err = f"Failed to diagnose: {e}"
            on_token(err)
            return err

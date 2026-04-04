import google.generativeai as genai
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DIAGNOSIS_PROMPT = """
You are a senior Site Reliability Engineer.
Analyze the logs, system snapshot, and config below.
Your target environment is a PaaS (like Railway). Fixes should be made by editing the local codebase.
Return ONLY valid JSON — no markdown, no explanation, just the JSON object.

JSON structure:
{{
  "root_cause": "one clear sentence describing the root cause",
  "severity": "critical|high|medium|low",
  "confidence": 0.0 to 1.0,
  "affected_service": "service name",
  "actions": [
    {{
      "action": "redeploy_app|write_file|read_file|restart_service|edit_config|rollback_deploy|read_logs",
      "target": "exact service name or file path",
      "params": {{"content": "for write_file", "message": "for redeploy_app"}},
      "reason": "why this fixes the root cause",
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

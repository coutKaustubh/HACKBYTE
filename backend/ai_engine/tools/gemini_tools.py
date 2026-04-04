"""
tools/gemini_tools.py — All Gemini AI calls for the agent pipeline.

Prompt templates live in tools/prompts.py — this class is pure call routing.
Token usage is recorded via utils/cost_tracker for per-incident cost tracking.
"""
import google.generativeai as genai
import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from tools.prompts import (
    build_diagnosis_prompt,
    build_code_patch_prompt,
    build_reactive_prompt,
)
from utils.cost_tracker import cost_tracker

# Always resolve .env from this file's location — works from any CWD (Django, standalone, tests)
_ENV = Path(__file__).resolve().parent.parent / ".env"
print(_ENV)
load_dotenv(_ENV)

# chars-per-token fallback when SDK metadata unavailable
_CHARS_PER_TOKEN = 4


class GeminiTools:
    def __init__(self):
        load_dotenv(_ENV)  # re-load in case env was not set at import time
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")
        # Current incident_id — set before each pipeline run so cost is attributed correctly
        self.incident_id: str = "unknown"

    # ── Diagnosis ─────────────────────────────────────────────────────────────

    def diagnose(self, logs: str, snapshot: dict, configs: dict,
                 project_tree: str = "", grounded_context: str = "") -> dict:
        import json as _json
        prompt = build_diagnosis_prompt(
            logs=logs,
            snapshot=_json.dumps(snapshot, indent=2),
            configs=_json.dumps(configs, indent=2),
            project_tree=project_tree,
            grounded_context=grounded_context,
        )
        raw = self._call(prompt, call_type="diagnose")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "error_type": "UNKNOWN",
                "root_cause": "Could not parse Gemini response",
                "severity": "high",
                "confidence": 0.3,
                "affected_service": "unknown",
                "actions": [],
                "reasoning": raw,
            }

    # ── Code Patching ─────────────────────────────────────────────────────────

    def generate_code_patch(
        self,
        error_context: str,
        file_path: str,
        file_content_with_lines: str,
        project_tree: str = "",
    ) -> dict:
        prompt = build_code_patch_prompt(
            error_context=error_context,
            file_path=file_path,
            file_content=file_content_with_lines,
            project_tree=project_tree,
        )
        raw = self._call(prompt, call_type="code_patch")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "file_path": file_path,
                "description": "Could not parse patch from Gemini",
                "confidence": 0.0,
                "hunks": [],
                "_raw": raw,
            }

    # ── Reactive Decision ─────────────────────────────────────────────────────

    def decide_next_action(
        self,
        completed_action: str,
        action_output: str,
        next_action: str,
        next_target: str,
    ) -> dict:
        prompt = build_reactive_prompt(
            completed_action=completed_action,
            action_output=action_output,
            next_action=next_action,
            next_target=next_target,
        )
        raw = self._call(prompt, call_type="reactive")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "decision": "PROCEED",
                "reason": "Could not parse decision",
                "modified_target": None,
                "modified_params": {},
            }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _call(self, prompt: str, call_type: str = "unknown") -> str:
        """Raw Gemini call — strips markdown fences and records token cost."""
        response = self.model.generate_content(prompt)
        raw = response.text.strip()
        raw = re.sub(r"```json|```", "", raw).strip()

        # ── Token tracking ─────────────────────────────────────────────────
        try:
            meta     = response.usage_metadata
            in_tok   = meta.prompt_token_count
            out_tok  = meta.candidates_token_count
        except Exception:
            # Fallback: estimate from character count
            in_tok  = len(prompt) // _CHARS_PER_TOKEN
            out_tok = len(raw)    // _CHARS_PER_TOKEN

        cost_tracker.record(self.incident_id, call_type, in_tok, out_tok)

        return raw

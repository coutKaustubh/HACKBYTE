import os
import httpx
from models.intent import Intent, EnforcementResult
from dotenv import load_dotenv

load_dotenv()

# ── Local policy definition ───────────────────────────────────────
# These mirror what you configure on platform.armoriq.ai
POLICIES = {
    "allow": [
        "restart_service",
        "edit_config",
        "rollback_deploy",
        "redeploy_app",
        "read_logs",
        "read_file",
        "write_file"
    ],
    "deny": [
        "drop_table",           # DEMO: always blocked
        "delete_database",      # DEMO: always blocked
        "exec_arbitrary",       # DEMO: always blocked
        "rm_rf"
    ],
    "deny_rules": {
        "drop_table":      ("P-001", "Destructive irreversible operation denied in production"),
        "delete_database": ("P-002", "Database deletion requires manual approval — not autonomous"),
        "exec_arbitrary":  ("P-003", "Arbitrary command execution outside approved action set"),
        "rm_rf":           ("P-004", "Filesystem deletion is permanently blocked")
    }
}

class ArmorTools:
    def __init__(self):
        self.api_key = os.getenv("ARMORIQ_API_KEY")
        self.base_url = "https://api.armoriq.ai"   # update if different

    def check_intent(self, intent: Intent) -> EnforcementResult:
        """
        Check a single intent against policies.
        First checks local policy, then calls ArmorIQ API for the token.
        """

        # ── Step 1: local policy check ────────────────────────────
        if intent.action in POLICIES["deny"]:
            policy_id, reason = POLICIES["deny_rules"].get(
                intent.action,
                ("P-999", "Action not in approved list")
            )
            return EnforcementResult(
                intent_id=intent.intent_id,
                action=intent.action,
                decision="BLOCKED",
                policy_matched=policy_id,
                reason=reason,
                token=None
            )

        if intent.action not in POLICIES["allow"]:
            return EnforcementResult(
                intent_id=intent.intent_id,
                action=intent.action,
                decision="BLOCKED",
                policy_matched="P-000",
                reason=f"Action '{intent.action}' is not in the approved action set",
                token=None
            )

        # ── Step 2: call ArmorIQ API for cryptographic token ──────
        # If API key not set, fallback to local-only mode (fine for demo)
        if not self.api_key or self.api_key == "ak_live_xxx":
            return EnforcementResult(
                intent_id=intent.intent_id,
                action=intent.action,
                decision="ALLOWED",
                policy_matched="local-allow",
                reason=f"Action '{intent.action}' is in approved list",
                token="local-mode-no-token"
            )

        try:
            response = httpx.post(
                f"{self.base_url}/v1/verify",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"intent": intent.model_dump() if hasattr(intent, "model_dump") else intent.dict()},
                timeout=5.0
            )
            data = response.json()
            return EnforcementResult(
                intent_id=intent.intent_id,
                action=intent.action,
                decision=data.get("decision", "ALLOWED"),
                policy_matched=data.get("policy_matched", "api-allow"),
                reason=data.get("reason", "Verified by ArmorIQ"),
                token=data.get("token")
            )
        except Exception:
            # fallback to local policy result if API unreachable
            return EnforcementResult(
                intent_id=intent.intent_id,
                action=intent.action,
                decision="ALLOWED",
                policy_matched="local-fallback",
                reason="ArmorIQ API unreachable — local policy applied",
                token=None
            )

    def check_plan(self, intents: list[Intent]) -> list[EnforcementResult]:
        """Check all intents in a plan, return enforcement result for each"""
        return [self.check_intent(intent) for intent in intents]

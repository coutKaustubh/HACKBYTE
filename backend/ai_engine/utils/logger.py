"""
utils/logger.py — Centralized structured console logger for the AI Engine.

All pipeline output is routed through here so the terminal always prints
in a clean, readable, emoji-annotated format instead of raw dict dumps.

Internal helpers (ANSI codes, formatters) now live in:
  utils/colors.py     — color constants
  utils/formatters.py — pure string formatters (ts, divider, fmt_dict)
"""

from utils.colors import (
    RESET, BOLD, DIM,
    CYAN, GREEN, YELLOW, RED, MAGENTA, BLUE,
)
from utils.formatters import ts as _ts, divider as _divider


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE LIFECYCLE
# ══════════════════════════════════════════════════════════════════════════════

def log_incident_started(incident_id: str, source: str) -> None:
    print()
    print(_divider("═"))
    print(f"{BOLD}{MAGENTA}🚨  INCIDENT STARTED{RESET}  {DIM}{_ts()}{RESET}")
    print(f"   {BOLD}ID    :{RESET} {CYAN}{incident_id}{RESET}")
    print(f"   {BOLD}Source:{RESET} {source}")
    print(_divider("═"))


def log_logs_collected(incident_id: str, log_length: int, pm2_snippet: str, failed_services: str) -> None:
    print()
    print(_divider())
    print(f"{BOLD}{BLUE}📦  LOGS COLLECTED{RESET}  {DIM}{incident_id}  {_ts()}{RESET}")
    print(f"   Log size   : {log_length:,} chars")
    print(f"   PM2 status : {pm2_snippet.strip()[:100] or '(empty)'}")
    if failed_services and "0 loaded" not in failed_services:
        print(f"   {YELLOW}⚠  Failed svcs: {failed_services[:120]}{RESET}")
    print(_divider())


def log_diagnosis_ready(incident_id: str, diagnosis: dict) -> None:
    error_type = diagnosis.get("error_type", "UNKNOWN")
    root_cause = diagnosis.get("root_cause", "")
    actions    = diagnosis.get("actions", [])
    severity   = diagnosis.get("severity", "")
    color      = RED if error_type not in ("UNKNOWN", "low") else YELLOW

    print()
    print(_divider())
    print(f"{BOLD}{color}🔍  DIAGNOSIS READY{RESET}  {DIM}{incident_id}  {_ts()}{RESET}")
    print(f"   {BOLD}Error type :{RESET} {color}{error_type}{RESET}")
    if severity:
        print(f"   {BOLD}Severity   :{RESET} {severity}")
    print(f"   {BOLD}Root cause :{RESET} {root_cause}")
    if actions:
        print(f"   {BOLD}Actions    :{RESET}")
        for i, a in enumerate(actions, 1):
            print(f"     {i}. [{a.get('risk_level','?').upper()}] {a['action']} → {a.get('target','')}")
    print(_divider())


def log_plan_ready(incident_id: str, intents: list) -> None:
    print()
    print(_divider())
    print(f"{BOLD}{CYAN}📋  PLAN READY{RESET}  {DIM}{incident_id}  {_ts()}{RESET}  ({len(intents)} intents)")
    for intent in intents:
        risk = intent.get("risk_level", "?").upper()
        risk_color = RED if risk == "CRITICAL" else (YELLOW if risk in ("HIGH", "MEDIUM") else GREEN)
        print(f"   Step {intent['step']:02d} │ {risk_color}{risk:<8}{RESET} │ {intent['action']:<20} │ {intent.get('target','')[:40]}")
    print(_divider())


def log_action_allowed(incident_id: str, intent_id: str, action: str, policy: str) -> None:
    print(f"  {GREEN}✅ ALLOWED{RESET}  {action:<22} {DIM}policy={policy}  intent={intent_id}{RESET}")


def log_action_blocked(incident_id: str, intent_id: str, action: str, policy: str, reason: str) -> None:
    print(f"  {RED}🚫 BLOCKED{RESET}  {action:<22} {DIM}policy={policy}{RESET}")
    print(f"             {RED}↳ {reason}{RESET}")


def log_action_executed(incident_id: str, action: str, target: str, status: str, output: str, intent_id: str) -> None:
    status_icon = f"{GREEN}✅" if status == "SUCCESS" else f"{RED}❌"
    print()
    print(f"  {status_icon} EXECUTED{RESET}  {BOLD}{action}{RESET} → {target[:50]}")
    output_preview = output.replace("\n", " ").strip()[:200] if output else ""
    if output_preview:
        print(f"             {DIM}↳ {output_preview}{RESET}")


def log_action_failed(incident_id: str, action: str, intent_id: str, error: str) -> None:
    print()
    print(f"  {RED}❌ FAILED{RESET}   {BOLD}{action}{RESET}")
    print(f"             {RED}↳ Error: {error}{RESET}")


def log_incident_resolved(incident_id: str, summary: dict) -> None:
    allowed   = summary.get("actions_allowed", 0)
    blocked   = summary.get("actions_blocked", 0)
    succeeded = summary.get("actions_succeeded", 0)
    cause     = summary.get("root_cause", "")
    msg       = summary.get("summary", "")

    print()
    print(_divider("═"))
    print(f"{BOLD}{GREEN}✅  INCIDENT RESOLVED{RESET}  {DIM}{incident_id}  {_ts()}{RESET}")
    print(f"   Root cause : {cause[:120]}")
    print(f"   Summary    : {msg}")
    print(f"   Actions    : {GREEN}{succeeded} succeeded{RESET}  │  {RED}{blocked} blocked{RESET}  │  {allowed} allowed total")
    if summary.get("blocked_details"):
        for b in summary["blocked_details"]:
            print(f"   {RED}⛔ Blocked  : {b['action']} — {b['reason']}{RESET}")
    print(_divider("═"))
    print()


def log_verify(incident_id: str, pass_num: int, resolved: bool, pm2_out: str = "") -> None:
    print()
    print(_divider())
    icon = f"{GREEN}✅" if resolved else f"{RED}❌"
    print(f"{icon}  VERIFY PASS {pass_num}{RESET}  {DIM}{incident_id}  {_ts()}{RESET}")
    if resolved:
        print(f"   App is online in PM2. Incident considered resolved.")
    else:
        preview = pm2_out.replace("\n", " ").strip()[:200]
        print(f"   App still not online.  PM2: {preview}")
    print(_divider())


def log_human_escalation(incident_id: str, confidence: float, threshold: float, diagnosis: dict) -> None:
    """Printed when Gemini's confidence is below threshold — agent defers to human."""
    print()
    print(_divider("═"))
    print(f"{BOLD}{YELLOW}🚨  HUMAN ESCALATION REQUIRED{RESET}  {DIM}{incident_id}  {_ts()}{RESET}")
    print(f"   {BOLD}Reason    :{RESET} Gemini confidence {confidence:.0%} < threshold {threshold:.0%}")
    print(f"   {BOLD}Error type:{RESET} {diagnosis.get('error_type', 'UNKNOWN')}")
    print(f"   {BOLD}Root cause:{RESET} {diagnosis.get('root_cause', '')[:120]}")
    print(f"   {YELLOW}→ Auto-fix SKIPPED. Manual investigation required.{RESET}")
    print(_divider("═"))
    print()


def log_recurring_alert(incident_id: str, alert: dict) -> None:
    """Printed when the same error on the same service keeps recurring."""
    print()
    print(f"  {YELLOW}⚠️  RECURRING INCIDENT DETECTED{RESET}  {DIM}{incident_id}{RESET}")
    print(f"     {alert['message']}")
    print()


def log_rollback(incident_id: str, success: int, total: int, details: list[str]) -> None:
    """Printed when verify.py auto-restores files after a failed patch."""
    print()
    print(_divider())
    icon = f"{GREEN}✅" if success == total else f"{YELLOW}⚠️ "
    print(f"{icon}  AUTO-ROLLBACK{RESET}  {DIM}{incident_id}  {_ts()}{RESET}")
    print(f"   Restored {success}/{total} file(s) to pre-patch state.")
    for line in details:
        print(f"   {line}")
    print(_divider())


# ══════════════════════════════════════════════════════════════════════════════
# POLLING / BUILD HOOK
# ══════════════════════════════════════════════════════════════════════════════

def log_polling_error_detected(interval: int) -> None:
    print()
    print(f"{RED}{BOLD}🚨  [MONITOR] New server errors detected — waking Agent!{RESET}  interval={interval}s  {DIM}{_ts()}{RESET}")


def log_polling_quiet() -> None:
    print(f"  {DIM}[Monitor {_ts()}] Server healthy — no new errors.{RESET}")


def log_polling_same_logs() -> None:
    """Printed when error logs exist but are identical to the last run — Gemini skipped."""
    print(f"  {GREEN}[Monitor {_ts()}] Logs unchanged since last fix — everything looks OK. Gemini skipped.{RESET}")


def log_polling_agent_done(interval: int) -> None:
    print(f"  {GREEN}[Monitor] Agent finished. Stabilization phase ({interval}s).{RESET}")


def log_build_hook(step: str, detail: str = "") -> None:
    print(f"  {CYAN}[BuildHook]{RESET} {step}  {DIM}{detail}{RESET}")


def log_ssh_error(msg: str) -> None:
    print()
    print(_divider("═"))
    print(f"{RED}{BOLD}🔴  SSH CONNECTION FAILED{RESET}")
    for line in str(msg).splitlines():
        print(f"   {line}")
    print(_divider("═"))
    print()


def log_agent_thinking(incident_id: str, chunk: str) -> None:
    """Stream Gemini reasoning tokens inline."""
    print(f"  {DIM}[thinking] {chunk}{RESET}", end="", flush=True)

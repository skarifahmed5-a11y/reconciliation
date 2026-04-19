"""
Agent 1: Autonomous GL Reconciliation Agent
============================================
Matches sub-ledger entries to General Ledger, flags exceptions,
auto-raises journal entries for standard variances, and escalates
anomalies to human reviewers.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any
from anthropic import Anthropic

# ── Configuration ────────────────────────────────────────────────────────────
MATCH_TOLERANCE_USD       = 0.01    # Cents-level rounding tolerance
FUZZY_DATE_WINDOW_DAYS    = 3       # ±N days for timing differences
AUTO_JE_THRESHOLD_USD     = 500.0   # Auto-post JEs below this amount
ESCALATION_THRESHOLD_USD  = 5000.0  # Escalate to human above this amount
MODEL                     = "claude-sonnet-4-20250514"

client = Anthropic()


# ── Sample Data ───────────────────────────────────────────────────────────────
SAMPLE_GL_ENTRIES = [
    {"id": "GL-001", "date": "2025-03-31", "account": "1100", "description": "Cash - Operating", "amount": 125000.00, "reference": "WIRE-8821"},
    {"id": "GL-002", "date": "2025-03-31", "account": "2000", "description": "AP Trade", "amount": -43200.50, "reference": "INV-4490"},
    {"id": "GL-003", "date": "2025-03-30", "account": "1200", "description": "AR Trade", "amount": 87500.00, "reference": "CUST-0032"},
    {"id": "GL-004", "date": "2025-03-29", "account": "5000", "description": "COGS", "amount": -22000.00, "reference": "PO-7712"},
    {"id": "GL-005", "date": "2025-03-28", "account": "4000", "description": "Revenue", "amount": 98000.00, "reference": "ORD-5531"},
]

SAMPLE_SUBLEDGER = [
    {"id": "SL-001", "date": "2025-03-31", "account": "1100", "description": "Wire Receipt", "amount": 125000.00, "reference": "WIRE-8821"},
    {"id": "SL-002", "date": "2025-03-31", "account": "2000", "description": "Vendor Invoice", "amount": -43200.49, "reference": "INV-4490"},   # $0.01 rounding diff
    {"id": "SL-003", "date": "2025-04-01", "account": "1200", "description": "Customer Receipt", "amount": 87500.00, "reference": "CUST-0032"},  # 1-day timing diff
    {"id": "SL-004", "date": "2025-03-29", "account": "5000", "description": "COGS Allocation", "amount": -22000.00, "reference": "PO-7712"},
    {"id": "SL-006", "date": "2025-03-27", "account": "1100", "description": "Unmatched Receipt", "amount": 15750.00, "reference": "WIRE-9900"}, # No GL match
]


# ── Matching Engine ───────────────────────────────────────────────────────────
def match_entries(gl: list[dict], sl: list[dict]) -> dict[str, Any]:
    """Run matching logic and return structured results."""
    matched, exceptions = [], []
    gl_matched_ids = set()

    for sl_entry in sl:
        best_match = None
        for gl_entry in gl:
            if gl_entry["id"] in gl_matched_ids:
                continue
            if gl_entry["account"] != sl_entry["account"]:
                continue

            # Amount match (within tolerance)
            amount_diff = abs(gl_entry["amount"] - sl_entry["amount"])
            if amount_diff > MATCH_TOLERANCE_USD * 10:
                continue

            # Date match (within window)
            gl_date  = datetime.strptime(gl_entry["date"], "%Y-%m-%d")
            sl_date  = datetime.strptime(sl_entry["date"], "%Y-%m-%d")
            date_gap = abs((gl_date - sl_date).days)

            if date_gap <= FUZZY_DATE_WINDOW_DAYS:
                best_match = {
                    "gl": gl_entry,
                    "sl": sl_entry,
                    "amount_diff": amount_diff,
                    "date_gap_days": date_gap,
                    "match_type": "EXACT" if amount_diff == 0 and date_gap == 0 else "FUZZY",
                }
                gl_matched_ids.add(gl_entry["id"])
                break

        if best_match:
            matched.append(best_match)
        else:
            exceptions.append({
                "sl_entry": sl_entry,
                "reason": "NO_GL_MATCH",
                "amount": sl_entry["amount"],
            })

    # GL entries with no sub-ledger match
    for gl_entry in gl:
        if gl_entry["id"] not in gl_matched_ids:
            exceptions.append({
                "gl_entry": gl_entry,
                "reason": "NO_SL_MATCH",
                "amount": gl_entry["amount"],
            })

    return {"matched": matched, "exceptions": exceptions}


# ── Agent Loop ────────────────────────────────────────────────────────────────
def run_gl_reconciliation_agent(gl_entries: list[dict], subledger: list[dict]) -> None:
    """
    Multi-turn agentic loop. The agent:
      1. Reviews matching results
      2. Decides what to auto-post vs escalate
      3. Produces a reconciliation memo
    """
    print("\n" + "═" * 60)
    print("  GL RECONCILIATION AGENT  |  Starting…")
    print("═" * 60 + "\n")

    # Step 1: Run matching engine
    results = match_entries(gl_entries, subledger)
    n_matched    = len(results["matched"])
    n_exceptions = len(results["exceptions"])
    match_rate   = n_matched / (n_matched + n_exceptions) * 100 if (n_matched + n_exceptions) > 0 else 0

    print(f"✅  Matched:    {n_matched} entries")
    print(f"⚠️   Exceptions: {n_exceptions} entries")
    print(f"📊  Match rate: {match_rate:.1f}%\n")

    # Step 2: Multi-turn agent conversation
    messages = []

    system_prompt = """You are an autonomous GL Reconciliation Agent for a finance team.
Your job is to:
1. Review matching results between sub-ledger and GL entries
2. For each exception, decide: auto-raise JE, flag for review, or escalate
3. Apply these rules:
   - Amount diff < $0.01 AND date diff = 0 → EXACT MATCH (no action)
   - Amount diff ≤ $500 OR timing diff ≤ 3 days → AUTO-RAISE JOURNAL ENTRY (draft)
   - Amount diff > $5,000 OR missing reference → ESCALATE TO HUMAN
   - Otherwise → FLAG FOR REVIEW
4. Output a structured reconciliation memo with:
   - Summary statistics
   - Recommended journal entries (with debit/credit accounts and amounts)
   - Items escalated to human reviewers with clear rationale
   - Overall sign-off status (CLEAR / REQUIRES ATTENTION / ESCALATED)

Be precise, concise, and audit-ready. Always include a timestamp and preparer note."""

    # Turn 1: Feed matching results
    user_msg_1 = f"""Here are the reconciliation results for period ending 2025-03-31:

MATCHED ENTRIES ({n_matched}):
{json.dumps(results['matched'], indent=2)}

UNMATCHED EXCEPTIONS ({n_exceptions}):
{json.dumps(results['exceptions'], indent=2)}

Please analyze each exception, decide on the appropriate action, and produce the reconciliation memo."""

    messages.append({"role": "user", "content": user_msg_1})
    print("🤖  Agent analyzing results…\n")

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=system_prompt,
        messages=messages,
    )
    agent_reply_1 = response.content[0].text
    messages.append({"role": "assistant", "content": agent_reply_1})
    print("── AGENT ANALYSIS ──────────────────────────────────────")
    print(agent_reply_1)

    # Turn 2: Ask agent to finalize and confirm actions
    messages.append({
        "role": "user",
        "content": (
            "Good. Now please output only the final action list as JSON with this shape:\n"
            '{"auto_journal_entries": [...], "escalations": [...], "status": "CLEAR|REQUIRES ATTENTION|ESCALATED"}'
        ),
    })

    response2 = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=system_prompt,
        messages=messages,
    )
    agent_reply_2 = response2.content[0].text
    messages.append({"role": "assistant", "content": agent_reply_2})

    print("\n── FINAL ACTION JSON ────────────────────────────────────")
    print(agent_reply_2)
    print("\n" + "═" * 60)
    print("  GL RECONCILIATION AGENT  |  Complete")
    print("═" * 60 + "\n")


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_gl_reconciliation_agent(SAMPLE_GL_ENTRIES, SAMPLE_SUBLEDGER)

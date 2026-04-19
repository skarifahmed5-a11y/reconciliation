"""
Agent 2: Multi-Agent Month-End Close Accelerator
=================================================
Orchestrates sub-agents for AP/AR matching, intercompany reconciliation,
accrual posting, and close checklist sign-off.
"""

import json
from datetime import datetime
from typing import Any
from anthropic import Anthropic

MODEL  = "claude-sonnet-4-20250514"
client = Anthropic()

# ── Close Checklist ───────────────────────────────────────────────────────────
CLOSE_CHECKLIST = [
    {"id": "AP-01",  "task": "Match all AP invoices to POs and payments",           "owner": "AP Agent",            "status": "PENDING"},
    {"id": "AR-01",  "task": "Match all customer receipts to open invoices",        "owner": "AR Agent",            "status": "PENDING"},
    {"id": "IC-01",  "task": "Reconcile all intercompany account balances",         "owner": "Intercompany Agent",  "status": "PENDING"},
    {"id": "AC-01",  "task": "Post month-end accruals from open PO analysis",       "owner": "Accrual Agent",       "status": "PENDING"},
    {"id": "GL-01",  "task": "GL ↔ Sub-ledger reconciliation (all accounts)",       "owner": "GL Agent",            "status": "PENDING"},
    {"id": "FS-01",  "task": "Tie out balance sheet to sub-ledgers",                "owner": "Financial Agent",     "status": "PENDING"},
    {"id": "RPT-01", "task": "Generate draft financial statements",                 "owner": "Reporting Agent",     "status": "PENDING"},
    {"id": "REV-01", "task": "Controller review and sign-off",                      "owner": "Human - Controller",  "status": "PENDING"},
]

# ── Sample Sub-agent Data ─────────────────────────────────────────────────────
AP_DATA = {
    "open_invoices": [
        {"vendor": "Acme Corp",    "invoice": "INV-4490", "amount": 43200.50, "due": "2025-04-10", "po": "PO-2201", "matched": True},
        {"vendor": "Beta Supplies","invoice": "INV-4501", "amount": 12800.00, "due": "2025-04-15", "po": "PO-2215", "matched": True},
        {"vendor": "Gamma LLC",    "invoice": "INV-4512", "amount": 8500.00,  "due": "2025-04-05", "po": None,      "matched": False},
    ]
}

AR_DATA = {
    "open_invoices": [
        {"customer": "Client A", "invoice": "CUST-0032", "amount": 87500.00, "overdue_days": 0,  "matched": True},
        {"customer": "Client B", "invoice": "CUST-0041", "amount": 23400.00, "overdue_days": 15, "matched": True},
        {"customer": "Client C", "invoice": "CUST-0055", "amount": 6750.00,  "overdue_days": 45, "matched": False},
    ]
}

INTERCOMPANY_DATA = {
    "entities": [
        {"entity_a": "Parent Co",  "entity_b": "Sub A", "parent_balance": 250000.0,  "sub_balance": -250000.0,  "variance": 0.0},
        {"entity_a": "Parent Co",  "entity_b": "Sub B", "parent_balance": 180000.0,  "sub_balance": -179800.0,  "variance": 200.0},
        {"entity_a": "Sub A",      "entity_b": "Sub C", "parent_balance": 45000.0,   "sub_balance": -45000.0,   "variance": 0.0},
    ]
}

OPEN_PO_DATA = {
    "open_pos": [
        {"po": "PO-3301", "vendor": "SaaS Vendor",    "amount": 15000.0,  "service_period": "Mar 2025", "received": True,  "invoiced": False},
        {"po": "PO-3302", "vendor": "Consulting Firm", "amount": 28500.0,  "service_period": "Mar 2025", "received": True,  "invoiced": False},
        {"po": "PO-3303", "vendor": "Utilities Co",    "amount": 4200.0,   "service_period": "Mar 2025", "received": True,  "invoiced": True},
    ]
}


# ── Sub-Agent Runners ─────────────────────────────────────────────────────────
def run_sub_agent(agent_name: str, task: str, data: dict, checklist_id: str, checklist: list) -> dict:
    """Generic sub-agent runner using the Anthropic API."""
    print(f"\n▶  Running {agent_name}…")

    system = f"""You are the {agent_name} for a month-end close process.
Your task: {task}
Be concise. Output a JSON object with keys: "status" (COMPLETE/EXCEPTIONS/ESCALATE), "summary", "exceptions" (list), "actions_taken" (list)."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=system,
        messages=[{"role": "user", "content": f"Here is the data:\n{json.dumps(data, indent=2)}\n\nPerform your task and return JSON only."}],
    )

    raw = response.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {"status": "EXCEPTIONS", "summary": raw, "exceptions": [], "actions_taken": []}

    # Update checklist
    for item in checklist:
        if item["id"] == checklist_id:
            item["status"] = "COMPLETE" if result.get("status") == "COMPLETE" else "EXCEPTIONS"
            break

    print(f"   ✓ {agent_name}: {result.get('status', 'UNKNOWN')} — {result.get('summary', '')[:80]}")
    return result


# ── Orchestrator Agent ────────────────────────────────────────────────────────
def run_month_end_close_orchestrator() -> None:
    """
    Orchestrator that:
    1. Spins up all sub-agents in sequence
    2. Collects results
    3. Produces a close status report
    4. Flags any items requiring human sign-off
    """
    print("\n" + "═" * 60)
    print("  MONTH-END CLOSE ACCELERATOR  |  Starting…")
    print(f"  Period: March 2025  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("═" * 60)

    checklist = [item.copy() for item in CLOSE_CHECKLIST]
    sub_results = {}

    # Run each sub-agent
    sub_results["ap"] = run_sub_agent(
        "AP Matching Agent", "Match all AP invoices to POs and payments. Flag invoices with no PO.",
        AP_DATA, "AP-01", checklist
    )
    sub_results["ar"] = run_sub_agent(
        "AR Matching Agent", "Match customer receipts to open invoices. Flag overdue items > 30 days.",
        AR_DATA, "AR-01", checklist
    )
    sub_results["intercompany"] = run_sub_agent(
        "Intercompany Reconciliation Agent", "Reconcile intercompany balances. Flag any non-zero variance.",
        INTERCOMPANY_DATA, "IC-01", checklist
    )
    sub_results["accruals"] = run_sub_agent(
        "Accrual Posting Agent", "Identify goods/services received but not yet invoiced. Recommend accrual journal entries.",
        OPEN_PO_DATA, "AC-01", checklist
    )

    # Mark remaining checklist items
    for item in checklist:
        if item["id"] in ("GL-01", "FS-01", "RPT-01") and item["status"] == "PENDING":
            item["status"] = "IN PROGRESS"
        if item["id"] == "REV-01":
            item["status"] = "AWAITING HUMAN"

    # Orchestrator summary via Claude
    print("\n🤖  Orchestrator generating close status report…")
    summary_prompt = f"""You are the Month-End Close Orchestrator. All sub-agents have completed.
Here are the results:

SUB-AGENT RESULTS:
{json.dumps(sub_results, indent=2)}

CLOSE CHECKLIST:
{json.dumps(checklist, indent=2)}

Produce a concise Close Status Report with:
1. Overall close status (ON TRACK / AT RISK / BLOCKED)
2. Completion % and items remaining
3. Key exceptions requiring controller attention
4. Recommended next actions (numbered list)
5. Estimated time to close"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1200,
        messages=[{"role": "user", "content": summary_prompt}],
    )

    report = response.content[0].text

    print("\n" + "─" * 60)
    print("  CLOSE STATUS REPORT")
    print("─" * 60)
    print(report)

    print("\n── CHECKLIST STATUS ─────────────────────────────────────")
    for item in checklist:
        icon = {"COMPLETE": "✅", "EXCEPTIONS": "⚠️ ", "IN PROGRESS": "🔄", "AWAITING HUMAN": "👤", "PENDING": "⏳"}.get(item["status"], "❓")
        print(f"  {icon}  [{item['id']}] {item['task'][:50]:<50}  {item['status']}")

    print("\n" + "═" * 60)
    print("  MONTH-END CLOSE ACCELERATOR  |  Complete")
    print("═" * 60 + "\n")


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_month_end_close_orchestrator()

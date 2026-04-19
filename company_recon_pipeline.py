"""
Agent 3: Company Reconciliation Agentic Pipeline
=================================================
Ingests bank statements + ERP data, auto-reconciles, classifies
unmatched items, and drafts CFO-ready exception reports.
"""

import json
from datetime import datetime
from anthropic import Anthropic

MODEL  = "claude-sonnet-4-20250514"
client = Anthropic()

# ── Sample Data ───────────────────────────────────────────────────────────────
BANK_STATEMENT = [
    {"date": "2025-03-31", "description": "WIRE IN - CLIENT A PAYMENT",       "amount":  87500.00, "ref": "WIRE-8821"},
    {"date": "2025-03-31", "description": "ACH OUT - ACME CORP INVOICE",      "amount": -43200.50, "ref": "ACH-4490"},
    {"date": "2025-03-28", "description": "WIRE IN - CLIENT B ORDER",         "amount":  98000.00, "ref": "WIRE-5531"},
    {"date": "2025-03-27", "description": "WIRE IN - UNKNOWN REMITTER",       "amount":  15750.00, "ref": "WIRE-9900"},
    {"date": "2025-03-25", "description": "BANK CHARGE - SERVICE FEE",        "amount":    -85.00, "ref": "FEE-0325"},
    {"date": "2025-03-20", "description": "ACH OUT - BETA SUPPLIES",          "amount": -12800.00, "ref": "ACH-4501"},
    {"date": "2025-03-15", "description": "WIRE IN - CLIENT C PARTIAL PAY",   "amount":  45000.00, "ref": "WIRE-7720"},
]

ERP_TRANSACTIONS = [
    {"date": "2025-03-31", "description": "AR Receipt - Client A",           "amount":  87500.00, "ref": "CUST-0032", "account": "1100"},
    {"date": "2025-03-31", "description": "AP Payment - Acme Corp",          "amount": -43200.49, "ref": "INV-4490",  "account": "2000"},
    {"date": "2025-03-29", "description": "Revenue - Order 5531",            "amount":  98000.00, "ref": "ORD-5531",  "account": "4000"},
    {"date": "2025-03-20", "description": "AP Payment - Beta Supplies",      "amount": -12800.00, "ref": "INV-4501",  "account": "2000"},
    {"date": "2025-03-16", "description": "AR Receipt - Client C",           "amount":  45000.00, "ref": "CUST-0055", "account": "1100"},
    {"date": "2025-03-10", "description": "Prepaid Expense",                 "amount":  -9500.00, "ref": "EXP-0310",  "account": "1500"},
]

EXCEPTION_CATEGORIES = [
    "TIMING_DIFFERENCE",     # Transaction in bank, not yet in ERP (or vice versa)
    "AMOUNT_MISMATCH",       # Same transaction but different amounts
    "BANK_CHARGE_FEE",       # Bank-side charge with no ERP entry
    "MISSING_ERP_ENTRY",     # Bank transaction with no corresponding ERP record
    "MISSING_BANK_ENTRY",    # ERP entry with no corresponding bank transaction
    "DUPLICATE",             # Possible duplicate posting
    "UNIDENTIFIED_RECEIPT",  # Cash received with no known remitter
]


# ── Matching Engine ───────────────────────────────────────────────────────────
def reconcile_bank_to_erp(bank: list[dict], erp: list[dict]) -> dict:
    """Basic matching: exact amount + reference or fuzzy amount + date proximity."""
    matched, bank_exceptions, erp_exceptions = [], [], []
    erp_used = set()

    for b in bank:
        match_found = None
        for i, e in enumerate(erp):
            if i in erp_used:
                continue
            amount_match = abs(b["amount"] - e["amount"]) <= 0.02
            ref_match    = b["ref"] in e["ref"] or e["ref"] in b["ref"]
            b_date = datetime.strptime(b["date"], "%Y-%m-%d")
            e_date = datetime.strptime(e["date"], "%Y-%m-%d")
            date_gap = abs((b_date - e_date).days)

            if amount_match and (ref_match or date_gap <= 3):
                match_found = {
                    "bank":         b,
                    "erp":          e,
                    "amount_diff":  round(b["amount"] - e["amount"], 2),
                    "date_gap_days": date_gap,
                    "match_type":   "EXACT" if abs(b["amount"] - e["amount"]) == 0 and date_gap == 0 else "FUZZY",
                }
                erp_used.add(i)
                break

        if match_found:
            matched.append(match_found)
        else:
            bank_exceptions.append(b)

    for i, e in enumerate(erp):
        if i not in erp_used:
            erp_exceptions.append(e)

    return {
        "matched":          matched,
        "bank_exceptions":  bank_exceptions,
        "erp_exceptions":   erp_exceptions,
    }


# ── Pipeline ──────────────────────────────────────────────────────────────────
def run_company_recon_pipeline() -> None:
    """
    Multi-turn pipeline:
      Turn 1 — Agent classifies each exception
      Turn 2 — Agent drafts CFO exception report with narrative
    """
    print("\n" + "═" * 60)
    print("  COMPANY RECONCILIATION PIPELINE  |  Starting…")
    print(f"  Bank Statement: March 2025  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("═" * 60)

    # Step 1: Reconcile
    results = reconcile_bank_to_erp(BANK_STATEMENT, ERP_TRANSACTIONS)
    n_matched   = len(results["matched"])
    n_bank_exc  = len(results["bank_exceptions"])
    n_erp_exc   = len(results["erp_exceptions"])
    total       = n_matched + n_bank_exc + n_erp_exc
    match_pct   = n_matched / total * 100 if total > 0 else 0

    print(f"\n✅  Matched:          {n_matched} items")
    print(f"⚠️   Bank exceptions:  {n_bank_exc} items")
    print(f"⚠️   ERP exceptions:   {n_erp_exc} items")
    print(f"📊  Reconciled:       {match_pct:.1f}%\n")

    system_prompt = """You are a senior treasury analyst AI agent working for the CFO.
Your role: classify bank reconciliation exceptions and draft executive-level reports.

Exception categories to use:
- TIMING_DIFFERENCE: Transaction exists on both sides but with different dates (≤5 days)
- AMOUNT_MISMATCH: Same transaction, different amounts
- BANK_CHARGE_FEE: Bank-side fee/charge not in ERP
- MISSING_ERP_ENTRY: In bank but not in ERP (needs investigation or journal entry)
- MISSING_BANK_ENTRY: In ERP but not in bank (timing or error)
- UNIDENTIFIED_RECEIPT: Cash received, remitter unknown — escalate immediately
- DUPLICATE: Potential double-posting

When drafting the CFO report:
- Use professional financial language
- Quantify total exposure (sum of unresolved items)
- Prioritize by risk (UNIDENTIFIED > MISSING_ERP > AMOUNT_MISMATCH > TIMING)
- Recommend specific actions for each item
- Include a sign-off recommendation (APPROVE / HOLD FOR REVIEW)"""

    messages = []

    # Turn 1: Classify exceptions
    turn1 = f"""Please classify each of the following bank reconciliation exceptions.
For each item, assign a category from the list and provide a brief rationale.

BANK-SIDE UNMATCHED (items in bank statement but not in ERP):
{json.dumps(results['bank_exceptions'], indent=2)}

ERP-SIDE UNMATCHED (items in ERP but not in bank statement):
{json.dumps(results['erp_exceptions'], indent=2)}

Return a JSON array of classified exceptions."""

    messages.append({"role": "user", "content": turn1})
    print("🤖  Agent classifying exceptions…")

    resp1 = client.messages.create(model=MODEL, max_tokens=1200, system=system_prompt, messages=messages)
    classification_text = resp1.content[0].text
    messages.append({"role": "assistant", "content": classification_text})

    print("\n── EXCEPTION CLASSIFICATION ─────────────────────────────")
    print(classification_text[:1200])

    # Turn 2: Draft CFO report
    messages.append({
        "role": "user",
        "content": (
            "Thank you. Now draft a complete CFO-ready Bank Reconciliation Exception Report for March 2025. "
            "Include: Executive Summary, exception detail table, risk assessment, recommended actions, "
            f"and sign-off recommendation. Total bank balance: $269,164.50. "
            f"Total ERP cash balance: $164,999.51. Unexplained difference: ${269164.50 - 164999.51:,.2f}."
        ),
    })

    print("\n🤖  Drafting CFO exception report…")
    resp2 = client.messages.create(model=MODEL, max_tokens=2000, system=system_prompt, messages=messages)
    cfo_report = resp2.content[0].text
    messages.append({"role": "assistant", "content": cfo_report})

    print("\n" + "─" * 60)
    print("  CFO EXCEPTION REPORT — MARCH 2025")
    print("─" * 60)
    print(cfo_report)

    print("\n" + "═" * 60)
    print("  COMPANY RECONCILIATION PIPELINE  |  Complete")
    print("═" * 60 + "\n")


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_company_recon_pipeline()

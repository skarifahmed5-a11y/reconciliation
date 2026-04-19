# Architecture

## Agent Flow Diagrams

### Agent 1 — GL Reconciliation
```
Sub-ledger entries ─┐
                    ├─► Matching Engine ─► EXACT MATCH  ──────────────────► Log & close
GL entries ─────────┘        │
                             ├─► FUZZY MATCH (±$0.01 or ±3 days) ────────► Auto-raise JE (draft)
                             ├─► AMOUNT DIFF < $500 ──────────────────────► Auto-raise JE
                             ├─► AMOUNT DIFF $500–$5000 ──────────────────► Flag for review
                             └─► AMOUNT DIFF > $5000 / unknown ───────────► Escalate to human
```

### Agent 2 — Month-End Close
```
Orchestrator Agent
    ├─► AP Matching Sub-agent      ──► Match invoices → POs → Payments
    ├─► AR Matching Sub-agent      ──► Match receipts → Open invoices
    ├─► Intercompany Sub-agent     ──► Balance entity A vs entity B
    ├─► Accrual Sub-agent          ──► Analyze open POs → Post accruals
    └─► Checklist Sub-agent        ──► Sign off completed tasks
            │
            └─► Close Status Report ──► Controller (human sign-off)
```

### Agent 3 — Company Recon Pipeline
```
Bank Statement (CSV/PDF) ─┐
                          ├─► Matching Engine ─► Matched items  ──► Auto-cleared
ERP Export ───────────────┘        │
                                   └─► Exceptions ──► Classification Agent
                                                              │
                                              ├─► TIMING_DIFFERENCE
                                              ├─► AMOUNT_MISMATCH
                                              ├─► BANK_CHARGE_FEE
                                              ├─► MISSING_ERP_ENTRY
                                              ├─► UNIDENTIFIED_RECEIPT  ──► Escalate
                                              └─► DUPLICATE
                                                              │
                                                   CFO Report Agent
                                                              │
                                                   Exception Report (PDF/MD)
```

## Technology Stack

| Layer | Technology |
|---|---|
| Agent AI | Claude claude-sonnet-4-20250514 via Anthropic Python SDK |
| Matching Engine | Python (exact + fuzzy matching) |
| Dashboard | HTML/CSS/JS (single-file, no build required) |
| Data Formats | JSON, CSV, PDF (pdfplumber) |
| Testing | pytest |

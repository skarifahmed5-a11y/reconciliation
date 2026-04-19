# 🤖 Agentic AI — Accounts Reconciliation Platform

> Autonomous multi-agent system for GL reconciliation, month-end close acceleration, and CFO-ready exception reporting.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Node](https://img.shields.io/badge/node-18+-brightgreen.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

---

## 🏗️ Architecture Overview

This platform consists of **three autonomous AI agent pipelines**:

| Agent | Responsibility |
|---|---|
| **GL Reconciliation Agent** | Matches sub-ledger to GL entries, flags exceptions, auto-raises journal entries |
| **Month-End Close Accelerator** | AP/AR matching, intercompany recon, accrual posting, checklist sign-off |
| **Company Recon Pipeline** | Ingests bank + ERP data, auto-reconciles, drafts CFO exception reports |

---

## 📁 Project Structure

```
reconciliation-ai/
├── src/
│   ├── agents/
│   │   ├── gl_reconciliation_agent.py       # Agent 1: GL ↔ Sub-ledger matching
│   │   ├── month_end_close_agent.py         # Agent 2: Month-end close orchestrator
│   │   └── company_recon_pipeline.py        # Agent 3: Bank + ERP reconciliation
│   ├── components/
│   │   └── dashboard/                       # React dashboard UI
│   ├── data/
│   │   ├── sample_gl_entries.json
│   │   ├── sample_subledger.json
│   │   └── sample_bank_statement.json
│   └── utils/
│       ├── matching_engine.py               # Core fuzzy/exact matching logic
│       ├── journal_entry_builder.py         # Auto-generates JE drafts
│       └── report_generator.py             # CFO report formatter
├── dashboard/                               # Standalone React dashboard
│   ├── index.html
│   └── app.jsx
├── docs/
│   ├── ARCHITECTURE.md
│   ├── AGENT_FLOWS.md
│   └── API_REFERENCE.md
├── tests/
│   └── test_agents.py
├── requirements.txt
├── package.json
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- An Anthropic API key (for Claude agent calls)

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/reconciliation-ai.git
cd reconciliation-ai

# Python dependencies
pip install -r requirements.txt

# Dashboard dependencies
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY and ERP credentials
```

### 3. Run an Agent

```bash
# Agent 1 — GL Reconciliation
python src/agents/gl_reconciliation_agent.py

# Agent 2 — Month-End Close
python src/agents/month_end_close_agent.py

# Agent 3 — Company Reconciliation Pipeline
python src/agents/company_recon_pipeline.py
```

### 4. Launch Dashboard

```bash
npm run dev
# Open http://localhost:5173
```

---

## 🤖 Agent Details

### Agent 1 — Autonomous GL Reconciliation Agent

**What it does:**
- Ingests sub-ledger transactions and GL entries
- Runs exact + fuzzy matching across amount, date, reference, and entity
- Flags unmatched items with confidence scores
- Auto-raises journal entries for standard variances (rounding, timing)
- Escalates anomalies above threshold to human reviewers

**Key configuration (`config.gl_agent`):**
```python
MATCH_TOLERANCE_USD = 0.01        # Exact match threshold
FUZZY_DATE_WINDOW_DAYS = 3        # ±3 days for timing differences
AUTO_JE_THRESHOLD_USD = 500       # Auto-post JEs below this amount
ESCALATION_THRESHOLD_USD = 5000   # Escalate to human above this
```

---

### Agent 2 — Multi-Agent Month-End Close Accelerator

**What it does:**
- Orchestrates sub-agents for AP matching, AR matching, intercompany recon
- Posts accruals based on open PO analysis
- Tracks close checklist and marks items complete autonomously
- Generates a close status report with outstanding items

**Sub-agents:**
| Sub-agent | Task |
|---|---|
| `ap_matching_agent` | Matches invoices to POs and payments |
| `ar_matching_agent` | Matches customer receipts to open invoices |
| `intercompany_agent` | Reconciles intercompany balances |
| `accrual_agent` | Identifies and posts month-end accruals |
| `checklist_agent` | Signs off completed close tasks |

---

### Agent 3 — Company Reconciliation Agentic Pipeline

**What it does:**
- Ingests raw bank statement (CSV/PDF) and ERP transaction export
- Auto-reconciles matched items
- Classifies unmatched items: *timing difference, bank error, missing entry, duplicate*
- Drafts a CFO-ready exception report with narrative summaries

---

## 📊 Dashboard

The React dashboard provides real-time visibility into all three agents:

- **Reconciliation Status** — match rates, open exceptions, aging
- **Agent Activity Feed** — live log of agent decisions
- **Exception Manager** — review, approve, or override agent actions
- **Close Checklist** — month-end progress tracker
- **CFO Report Preview** — formatted exception report

---

## 🔐 Security & Compliance

- All agent actions are logged with timestamps and rationale
- Journal entries auto-raised by agents are held in **draft** status pending human approval (configurable)
- Supports SOX-compliant audit trail export
- Role-based access: Preparer / Reviewer / Approver

---

## 🧪 Testing

```bash
pytest tests/ -v
```

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

## 🤝 Contributing

PRs welcome. See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

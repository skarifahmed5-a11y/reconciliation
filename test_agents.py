"""
Tests for Reconciliation AI Agents
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.gl_reconciliation_agent import match_entries, SAMPLE_GL_ENTRIES, SAMPLE_SUBLEDGER
from agents.company_recon_pipeline import reconcile_bank_to_erp, BANK_STATEMENT, ERP_TRANSACTIONS


class TestGLMatchingEngine:
    def test_exact_match(self):
        gl  = [{"id": "GL-1", "date": "2025-03-31", "account": "1100", "description": "Wire", "amount": 1000.00, "reference": "W1"}]
        sl  = [{"id": "SL-1", "date": "2025-03-31", "account": "1100", "description": "Wire", "amount": 1000.00, "reference": "W1"}]
        res = match_entries(gl, sl)
        assert len(res["matched"]) == 1
        assert len(res["exceptions"]) == 0
        assert res["matched"][0]["match_type"] == "EXACT"

    def test_rounding_diff_matches(self):
        gl  = [{"id": "GL-1", "date": "2025-03-31", "account": "2000", "description": "Invoice", "amount": -100.00, "reference": "I1"}]
        sl  = [{"id": "SL-1", "date": "2025-03-31", "account": "2000", "description": "Invoice", "amount": -99.99, "reference": "I1"}]
        res = match_entries(gl, sl)
        assert len(res["matched"]) == 1
        assert res["matched"][0]["match_type"] == "FUZZY"

    def test_no_match_different_account(self):
        gl  = [{"id": "GL-1", "date": "2025-03-31", "account": "1100", "description": "X", "amount": 500.00, "reference": "R1"}]
        sl  = [{"id": "SL-1", "date": "2025-03-31", "account": "2000", "description": "X", "amount": 500.00, "reference": "R1"}]
        res = match_entries(gl, sl)
        assert len(res["exceptions"]) == 2  # both unmatched

    def test_sample_data_match_rate(self):
        res = match_entries(SAMPLE_GL_ENTRIES, SAMPLE_SUBLEDGER)
        total    = len(res["matched"]) + len(res["exceptions"])
        match_rate = len(res["matched"]) / total
        assert match_rate > 0.5, "Expected >50% match rate on sample data"

    def test_timing_difference_within_window(self):
        gl  = [{"id": "GL-1", "date": "2025-03-31", "account": "1200", "description": "AR", "amount": 5000.00, "reference": "C1"}]
        sl  = [{"id": "SL-1", "date": "2025-04-01", "account": "1200", "description": "AR", "amount": 5000.00, "reference": "C1"}]
        res = match_entries(gl, sl)
        assert len(res["matched"]) == 1
        assert res["matched"][0]["date_gap_days"] == 1


class TestBankReconciliation:
    def test_exact_bank_match(self):
        bank = [{"date": "2025-03-31", "description": "Wire", "amount": 1000.00, "ref": "W1"}]
        erp  = [{"date": "2025-03-31", "description": "Wire", "amount": 1000.00, "ref": "W1", "account": "1100"}]
        res  = reconcile_bank_to_erp(bank, erp)
        assert len(res["matched"]) == 1
        assert len(res["bank_exceptions"]) == 0

    def test_unmatched_bank_item(self):
        bank = [{"date": "2025-03-27", "description": "Unknown Wire", "amount": 15750.00, "ref": "WIRE-9900"}]
        erp  = []
        res  = reconcile_bank_to_erp(bank, erp)
        assert len(res["bank_exceptions"]) == 1

    def test_sample_data(self):
        res = reconcile_bank_to_erp(BANK_STATEMENT, ERP_TRANSACTIONS)
        assert len(res["matched"]) >= 4, "Expected at least 4 matches on sample data"
        assert len(res["bank_exceptions"]) >= 1, "WIRE-9900 should be unmatched"

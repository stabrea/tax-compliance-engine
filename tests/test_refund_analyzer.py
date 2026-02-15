"""Tests for the RefundAnalyzer."""

from datetime import date
from decimal import Decimal

import pytest

from tax_engine.calculator import Transaction
from tax_engine.refund_analyzer import (
    OverpaymentRecord,
    RefundAnalyzer,
    RefundSummary,
    _get_sol_years,
)


@pytest.fixture
def analyzer() -> RefundAnalyzer:
    return RefundAnalyzer()


def _txn(
    txn_id: str = "TXN-001",
    amount: str = "100.00",
    state: str = "TX",
    city: str | None = "Houston",
    category: str | None = None,
    txn_date: date | None = None,
) -> Transaction:
    return Transaction(
        transaction_id=txn_id,
        transaction_date=txn_date or date(2024, 6, 15),
        amount=Decimal(amount),
        state=state,
        city=city,
        item_category=category,
    )


# ── Overpayment detection ───────────────────────────────────────────


def test_overpayment_detected_when_tax_paid_exceeds_owed(
    analyzer: RefundAnalyzer,
):
    txn = _txn("TXN-001", "1000.00", "TX", "Houston")
    # TX+Houston = 8.25% -> $82.50 owed. Pay $100 -> $17.50 overpaid
    record = analyzer.analyze_transaction(txn, Decimal("100.00"))
    assert record is not None
    assert isinstance(record, OverpaymentRecord)
    assert record.overpayment == Decimal("17.50")
    assert record.tax_owed == Decimal("82.50")


def test_no_overpayment_when_exact_payment(analyzer: RefundAnalyzer):
    txn = _txn("TXN-002", "1000.00", "TX", "Houston")
    # Exact amount owed
    record = analyzer.analyze_transaction(txn, Decimal("82.50"))
    assert record is None


def test_no_overpayment_when_underpaid(analyzer: RefundAnalyzer):
    txn = _txn("TXN-003", "1000.00", "TX", "Houston")
    record = analyzer.analyze_transaction(txn, Decimal("50.00"))
    assert record is None


def test_overpayment_on_exempt_transaction(analyzer: RefundAnalyzer):
    # Grocery is exempt in TX, so any tax paid is overpayment
    txn = _txn("TXN-004", "100.00", "TX", "Houston", category="grocery")
    record = analyzer.analyze_transaction(txn, Decimal("8.25"))
    assert record is not None
    assert record.overpayment == Decimal("8.25")
    assert "Exempt" in record.reason


def test_overpayment_in_no_tax_state(analyzer: RefundAnalyzer):
    # Oregon has no sales tax
    txn = _txn("TXN-005", "500.00", "OR")
    record = analyzer.analyze_transaction(txn, Decimal("35.00"))
    assert record is not None
    assert record.overpayment == Decimal("35.00")


def test_batch_analysis(analyzer: RefundAnalyzer):
    transactions = [
        (_txn("TXN-010", "1000.00", "TX", "Houston"), Decimal("100.00")),
        (_txn("TXN-011", "1000.00", "TX", "Houston"), Decimal("82.50")),
        (_txn("TXN-012", "500.00", "OR"), Decimal("25.00")),
    ]
    summary = analyzer.analyze_batch(transactions)
    assert isinstance(summary, RefundSummary)
    assert summary.total_transactions_reviewed == 3
    assert summary.overpayment_count == 2  # TXN-010 and TXN-012
    assert summary.total_overpayment > Decimal("0")


def test_batch_state_breakdown(analyzer: RefundAnalyzer):
    transactions = [
        (_txn("TXN-020", "1000.00", "TX", "Houston"), Decimal("100.00")),
        (_txn("TXN-021", "500.00", "OR"), Decimal("25.00")),
    ]
    summary = analyzer.analyze_batch(transactions)
    assert "TX" in summary.state_breakdown
    assert "OR" in summary.state_breakdown


def test_estimated_recovery_is_85_percent(analyzer: RefundAnalyzer):
    transactions = [
        (_txn("TXN-030", "1000.00", "TX", "Houston"), Decimal("100.00")),
    ]
    summary = analyzer.analyze_batch(
        transactions, as_of=date(2024, 7, 1)
    )
    eligible_overpayment = sum(
        r.overpayment for r in summary.records if r.refund_eligible
    )
    expected = (eligible_overpayment * Decimal("0.85")).quantize(
        Decimal("0.01")
    )
    assert summary.estimated_recovery == expected


# ── Statute of limitations checking ──────────────────────────────────


def test_recent_transaction_within_sol(analyzer: RefundAnalyzer):
    txn = _txn("TXN-040", "1000.00", "TX", "Houston", txn_date=date(2024, 1, 1))
    record = analyzer.analyze_transaction(
        txn, Decimal("100.00"), as_of=date(2024, 7, 1)
    )
    assert record is not None
    assert record.refund_eligible is True


def test_old_transaction_past_sol(analyzer: RefundAnalyzer):
    # TX has 4-year SOL; transaction from 5 years ago should be expired
    txn = _txn("TXN-041", "1000.00", "TX", "Houston", txn_date=date(2018, 1, 1))
    record = analyzer.analyze_transaction(
        txn, Decimal("100.00"), as_of=date(2024, 7, 1)
    )
    assert record is not None
    assert record.refund_eligible is False


def test_sol_date_populated(analyzer: RefundAnalyzer):
    txn = _txn("TXN-042", "1000.00", "TX", "Houston", txn_date=date(2024, 1, 1))
    record = analyzer.analyze_transaction(
        txn, Decimal("100.00"), as_of=date(2024, 7, 1)
    )
    assert record is not None
    assert record.statute_of_limitations_date is not None
    # TX SOL is 4 years, so expiry should be 2028-01-01
    assert record.statute_of_limitations_date == date(2028, 1, 1)


def test_sol_years_lookup():
    assert _get_sol_years("TX") == 4
    assert _get_sol_years("CA") == 3
    assert _get_sol_years("NY") == 3
    assert _get_sol_years("IL") == 4
    # Unknown state falls back to default of 3
    assert _get_sol_years("ZZ") == 3


def test_batch_warns_about_expired_transactions(analyzer: RefundAnalyzer):
    transactions = [
        (
            _txn("TXN-050", "1000.00", "TX", "Houston", txn_date=date(2018, 1, 1)),
            Decimal("100.00"),
        ),
    ]
    summary = analyzer.analyze_batch(transactions, as_of=date(2024, 7, 1))
    assert len(summary.warnings) > 0
    assert "statute of limitations" in summary.warnings[0].lower()


def test_generate_refund_claims(analyzer: RefundAnalyzer):
    transactions = [
        (_txn("TXN-060", "1000.00", "TX", "Houston"), Decimal("100.00")),
        (_txn("TXN-061", "500.00", "CA", "Los Angeles"), Decimal("60.00")),
    ]
    summary = analyzer.analyze_batch(transactions, as_of=date(2024, 7, 1))
    claims = analyzer.generate_refund_claims(summary)
    assert len(claims) > 0
    # Claims should be sorted by total_refund_requested descending
    if len(claims) > 1:
        assert claims[0].total_refund_requested >= claims[1].total_refund_requested


def test_quick_scan(analyzer: RefundAnalyzer):
    transactions = [
        (_txn("TXN-070", "1000.00", "TX", "Houston"), Decimal("100.00")),
        (_txn("TXN-071", "1000.00", "TX", "Houston"), Decimal("82.50")),
    ]
    hits = analyzer.quick_scan(transactions, minimum_overpayment=Decimal("1.00"))
    assert len(hits) == 1
    assert hits[0].transaction_id == "TXN-070"

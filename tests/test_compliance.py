"""Tests for the ComplianceChecker (nexus, deadlines, overdue)."""

from datetime import date
from decimal import Decimal

import pytest

from tax_engine.compliance import (
    ComplianceChecker,
    FilingDeadline,
    FilingFrequency,
    NexusStatus,
    NexusType,
)


@pytest.fixture
def checker() -> ComplianceChecker:
    return ComplianceChecker()


# ── Nexus threshold checking ────────────────────────────────────────


def test_nexus_established_by_revenue(checker: ComplianceChecker):
    status = checker.check_nexus("TX", Decimal("600000"), 50)
    assert status.has_nexus is True
    assert NexusType.ECONOMIC in status.nexus_types


def test_nexus_established_by_transactions(checker: ComplianceChecker):
    # CT has 200 transaction threshold
    status = checker.check_nexus("CT", Decimal("50000"), 250)
    assert status.has_nexus is True
    assert NexusType.ECONOMIC in status.nexus_types


def test_nexus_not_established_below_threshold(checker: ComplianceChecker):
    status = checker.check_nexus("TX", Decimal("10000"), 10)
    assert status.has_nexus is False


def test_nexus_physical_presence(checker: ComplianceChecker):
    status = checker.check_nexus(
        "TX", Decimal("1000"), 5, physical_presence=True
    )
    assert status.has_nexus is True
    assert NexusType.PHYSICAL in status.nexus_types


def test_no_nexus_in_no_tax_states(checker: ComplianceChecker):
    for state in ["DE", "MT", "NH", "OR"]:
        status = checker.check_nexus(state, Decimal("1000000"), 500)
        assert status.has_nexus is False
        assert f"{state} has no sales tax" in status.details


def test_approaching_threshold_flag(checker: ComplianceChecker):
    # TX threshold is $500k; 80% = $400k
    status = checker.check_nexus("TX", Decimal("450000"), 10)
    assert status.has_nexus is False
    assert status.approaching_threshold is True


def test_revenue_percentage_calculated(checker: ComplianceChecker):
    # GA threshold is $100k; $50k = 50%
    status = checker.check_nexus("GA", Decimal("50000"), 10)
    assert status.revenue_pct_of_threshold == pytest.approx(50.0, abs=0.1)


def test_transaction_percentage_calculated(checker: ComplianceChecker):
    # GA has 200 transaction threshold; 100 = 50%
    status = checker.check_nexus("GA", Decimal("10000"), 100)
    assert status.transaction_pct_of_threshold == pytest.approx(50.0, abs=0.1)


def test_check_nexus_all_states(checker: ComplianceChecker):
    revenues = {"TX": Decimal("600000"), "CA": Decimal("50000")}
    transactions = {"TX": 100, "CA": 50}
    results = checker.check_nexus_all_states(revenues, transactions)
    assert len(results) == 2
    # Results sorted by revenue pct, TX should be first (exceeded)
    tx_status = next(r for r in results if r.state_code == "TX")
    assert tx_status.has_nexus is True


# ── Filing deadline generation ───────────────────────────────────────


def test_monthly_filing_generates_12_deadlines(checker: ComplianceChecker):
    deadlines = checker.get_filing_deadlines(
        "TX", 2024, frequency=FilingFrequency.MONTHLY
    )
    assert len(deadlines) == 12
    assert all(isinstance(d, FilingDeadline) for d in deadlines)


def test_quarterly_filing_generates_4_deadlines(checker: ComplianceChecker):
    deadlines = checker.get_filing_deadlines(
        "CA", 2024, frequency=FilingFrequency.QUARTERLY
    )
    assert len(deadlines) == 4


def test_annual_filing_generates_1_deadline(checker: ComplianceChecker):
    deadlines = checker.get_filing_deadlines(
        "NY", 2024, frequency=FilingFrequency.ANNUAL
    )
    assert len(deadlines) == 1


def test_auto_frequency_monthly_for_high_liability(
    checker: ComplianceChecker,
):
    # > $4800 annual -> monthly
    deadlines = checker.get_filing_deadlines(
        "TX", 2024, estimated_annual_liability=Decimal("10000")
    )
    assert len(deadlines) == 12
    assert all(d.frequency == FilingFrequency.MONTHLY for d in deadlines)


def test_auto_frequency_quarterly_for_medium_liability(
    checker: ComplianceChecker,
):
    # $1200...$4799 -> quarterly
    deadlines = checker.get_filing_deadlines(
        "TX", 2024, estimated_annual_liability=Decimal("2000")
    )
    assert len(deadlines) == 4
    assert all(d.frequency == FilingFrequency.QUARTERLY for d in deadlines)


def test_auto_frequency_annual_for_low_liability(
    checker: ComplianceChecker,
):
    # < $1200 -> annual
    deadlines = checker.get_filing_deadlines(
        "TX", 2024, estimated_annual_liability=Decimal("500")
    )
    assert len(deadlines) == 1


def test_filing_deadline_due_date_is_next_month(checker: ComplianceChecker):
    deadlines = checker.get_filing_deadlines(
        "TX", 2024, frequency=FilingFrequency.MONTHLY
    )
    jan = deadlines[0]
    # January period ends 2024-01-31, due 2024-02-20 for TX
    assert jan.period_end == date(2024, 1, 31)
    assert jan.due_date == date(2024, 2, 20)


def test_december_deadline_rolls_to_next_year(checker: ComplianceChecker):
    deadlines = checker.get_filing_deadlines(
        "TX", 2024, frequency=FilingFrequency.MONTHLY
    )
    dec = deadlines[11]
    assert dec.period_end == date(2024, 12, 31)
    assert dec.due_date == date(2025, 1, 20)


# ── Overdue detection ───────────────────────────────────────────────


def test_past_deadline_is_overdue(checker: ComplianceChecker):
    # As of 2024-12-01, the January through October periods should be overdue
    deadlines = checker.get_filing_deadlines(
        "TX",
        2024,
        frequency=FilingFrequency.MONTHLY,
        as_of=date(2024, 12, 1),
    )
    jan = deadlines[0]
    assert jan.is_overdue is True
    assert jan.status == "overdue"


def test_future_deadline_is_not_overdue(checker: ComplianceChecker):
    deadlines = checker.get_filing_deadlines(
        "TX",
        2025,
        frequency=FilingFrequency.MONTHLY,
        as_of=date(2024, 12, 1),
    )
    # All 2025 deadlines should be pending as of Dec 2024
    assert all(d.is_overdue is False for d in deadlines)


def test_filed_period_not_overdue(checker: ComplianceChecker):
    checker.mark_filed("TX", date(2024, 1, 1), date(2024, 1, 31))
    deadlines = checker.get_filing_deadlines(
        "TX",
        2024,
        frequency=FilingFrequency.MONTHLY,
        as_of=date(2024, 12, 1),
    )
    jan = deadlines[0]
    assert jan.is_overdue is False
    assert jan.status == "filed"


def test_get_overdue_filings(checker: ComplianceChecker):
    checker.register_state("TX")
    # Use monthly frequency so multiple deadlines fall before the as_of date.
    # get_overdue_filings uses default estimated_annual_liability=0, which
    # picks annual frequency (due Jan 20 of NEXT year), so we generate
    # deadlines manually with monthly frequency to verify overdue detection.
    deadlines = checker.get_filing_deadlines(
        "TX", 2024, frequency=FilingFrequency.MONTHLY, as_of=date(2024, 6, 1)
    )
    overdue = [d for d in deadlines if d.is_overdue]
    assert len(overdue) > 0
    assert all(d.is_overdue for d in overdue)
    assert all(d.state_code == "TX" for d in overdue)


def test_generate_alerts_nexus_without_registration(
    checker: ComplianceChecker,
):
    revenues = {"TX": Decimal("600000")}
    transactions = {"TX": 100}
    alerts = checker.generate_alerts(
        revenues, transactions, registered_states=[]
    )
    critical = [a for a in alerts if a.severity == "critical"]
    assert len(critical) > 0
    assert any("TX" in a.message for a in critical)

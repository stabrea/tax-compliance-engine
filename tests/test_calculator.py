"""Tests for the TaxCalculator engine."""

from datetime import date
from decimal import Decimal

import pytest

from tax_engine.rates import TaxRateDatabase
from tax_engine.calculator import (
    BatchResult,
    PricingModel,
    TaxCalculator,
    TaxResult,
    Transaction,
)


@pytest.fixture
def calc() -> TaxCalculator:
    return TaxCalculator()


def _txn(
    amount: str = "100.00",
    state: str = "TX",
    city: str | None = "Houston",
    category: str | None = None,
    customer_type: str = "retail",
    exemption_cert: str | None = None,
) -> Transaction:
    return Transaction(
        transaction_id="TEST-001",
        transaction_date=date(2024, 6, 15),
        amount=Decimal(amount),
        state=state,
        city=city,
        item_category=category,
        customer_type=customer_type,
        exemption_certificate=exemption_cert,
    )


# ── Basic tax calculation ────────────────────────────────────────────


def test_basic_texas_calculation(calc: TaxCalculator):
    result = calc.calculate(_txn("500.00", "TX", "Houston"))
    # TX 6.25% + Houston 2% = 8.25%
    assert result.state_tax == Decimal("31.25")
    assert result.local_tax == Decimal("10.00")
    assert result.tax_amount == Decimal("41.25")
    assert result.effective_rate == pytest.approx(0.0825, abs=0.001)


def test_california_calculation(calc: TaxCalculator):
    result = calc.calculate(_txn("200.00", "CA", "Los Angeles"))
    # CA 7.25% + LA 2.5% = 9.75%
    assert result.state_tax == Decimal("14.50")
    assert result.local_tax == Decimal("5.00")
    assert result.tax_amount == Decimal("19.50")


def test_oregon_no_tax(calc: TaxCalculator):
    result = calc.calculate(_txn("1000.00", "OR"))
    assert result.tax_amount == Decimal("0.00")
    assert result.is_exempt is True


def test_delaware_no_tax(calc: TaxCalculator):
    result = calc.calculate(_txn("500.00", "DE"))
    assert result.tax_amount == Decimal("0.00")
    assert result.is_exempt is True


def test_unknown_state_returns_zero_tax_with_warning(calc: TaxCalculator):
    result = calc.calculate(_txn("100.00", "ZZ"))
    assert result.tax_amount == Decimal("0.00")
    assert len(result.warnings) > 0
    assert "Unknown" in result.warnings[0]


# ── Exempt transaction handling ──────────────────────────────────────


def test_grocery_exempt_in_texas(calc: TaxCalculator):
    result = calc.calculate(_txn("100.00", "TX", "Houston", category="grocery"))
    assert result.is_exempt is True
    assert result.tax_amount == Decimal("0.00")


def test_prescription_exempt_in_california(calc: TaxCalculator):
    result = calc.calculate(
        _txn("50.00", "CA", "Los Angeles", category="prescription")
    )
    assert result.is_exempt is True
    assert result.tax_amount == Decimal("0.00")


def test_clothing_exempt_in_new_york(calc: TaxCalculator):
    result = calc.calculate(
        _txn("100.00", "NY", "New York City", category="clothing")
    )
    assert result.is_exempt is True
    assert result.tax_amount == Decimal("0.00")


def test_wholesale_customer_exempt(calc: TaxCalculator):
    result = calc.calculate(
        _txn("500.00", "TX", "Houston", customer_type="wholesale")
    )
    assert result.is_exempt is True
    assert result.tax_amount == Decimal("0.00")


def test_exemption_certificate_exempt(calc: TaxCalculator):
    result = calc.calculate(
        _txn("500.00", "TX", "Houston", exemption_cert="CERT-12345")
    )
    assert result.is_exempt is True
    assert result.tax_amount == Decimal("0.00")


def test_non_exempt_category_is_taxed(calc: TaxCalculator):
    # "electronics" is not an exemption category
    result = calc.calculate(
        _txn("100.00", "TX", "Houston", category="electronics")
    )
    assert result.is_exempt is False
    assert result.tax_amount > Decimal("0.00")


# ── Multi-jurisdiction calculation ───────────────────────────────────


def test_batch_calculation(calc: TaxCalculator):
    transactions = [
        _txn("100.00", "TX", "Houston"),
        _txn("200.00", "CA", "Los Angeles"),
        _txn("300.00", "OR"),
    ]
    batch = calc.calculate_batch(transactions)
    assert isinstance(batch, BatchResult)
    assert batch.transaction_count == 3
    assert len(batch.results) == 3
    assert batch.total_tax > Decimal("0")
    assert batch.exempt_count >= 1  # OR is exempt


def test_batch_state_breakdown(calc: TaxCalculator):
    transactions = [
        _txn("100.00", "TX", "Houston"),
        _txn("200.00", "TX", "Dallas"),
        _txn("300.00", "CA", "San Francisco"),
    ]
    batch = calc.calculate_batch(transactions)
    assert "TX" in batch.state_breakdown
    assert "CA" in batch.state_breakdown
    assert batch.state_breakdown["TX"] > Decimal("0")
    assert batch.state_breakdown["CA"] > Decimal("0")


def test_use_tax_with_credit(calc: TaxCalculator):
    result = calc.calculate_use_tax(
        purchase_amount=Decimal("1000.00"),
        destination_state="TX",
        destination_city="Houston",
        tax_already_paid=Decimal("30.00"),
    )
    # TX+Houston = 8.25% -> $82.50 tax, minus $30 credit = $52.50
    assert result.tax_amount == Decimal("52.50")
    assert len(result.warnings) > 0
    assert "Credit" in result.warnings[0]


def test_use_tax_no_credit(calc: TaxCalculator):
    result = calc.calculate_use_tax(
        purchase_amount=Decimal("1000.00"),
        destination_state="TX",
        destination_city="Houston",
    )
    assert result.tax_amount == Decimal("82.50")


def test_total_with_tax_property(calc: TaxCalculator):
    result = calc.calculate(_txn("100.00", "TX", "Houston"))
    assert result.total_with_tax == result.taxable_amount + result.tax_amount


def test_transaction_from_dict():
    data = {
        "transaction_id": "TXN-100",
        "transaction_date": "2024-06-15",
        "amount": 500,
        "state": "TX",
        "city": "Houston",
        "item_category": "electronics",
    }
    txn = Transaction.from_dict(data)
    assert txn.transaction_id == "TXN-100"
    assert txn.amount == Decimal("500")
    assert txn.state == "TX"
    assert txn.city == "Houston"

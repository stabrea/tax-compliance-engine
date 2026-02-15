"""
Sales tax refund opportunity analyzer.

Identifies overpayments, exempt transactions that were incorrectly taxed,
rate mismatches, and generates refund filing data.

This mirrors real-world refund analysis work: pulling transaction data,
cross-referencing rates and exemptions, quantifying recoverable amounts,
and preparing the documentation needed for a refund claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from tax_engine.rates import ExemptionCategory, TaxRateDatabase
from tax_engine.calculator import TaxCalculator, Transaction, TaxResult


@dataclass
class OverpaymentRecord:
    """A single identified overpayment."""

    transaction_id: str
    transaction_date: date
    state: str
    city: Optional[str]
    sale_amount: Decimal
    tax_paid: Decimal
    tax_owed: Decimal
    overpayment: Decimal
    reason: str
    refund_eligible: bool = True
    statute_of_limitations_date: Optional[date] = None


@dataclass
class RefundSummary:
    """Aggregated refund analysis results."""

    total_overpayment: Decimal
    total_transactions_reviewed: int
    overpayment_count: int
    records: list[OverpaymentRecord]
    state_breakdown: dict[str, Decimal]
    reason_breakdown: dict[str, Decimal]
    oldest_eligible: Optional[date]
    newest_eligible: Optional[date]
    estimated_recovery: Decimal  # after typical claim success rate
    warnings: list[str] = field(default_factory=list)


@dataclass
class RefundClaim:
    """Data needed to file a refund claim with a state."""

    state_code: str
    claim_period_start: date
    claim_period_end: date
    total_refund_requested: Decimal
    transaction_count: int
    records: list[OverpaymentRecord]
    supporting_reasons: list[str]
    filing_notes: str = ""


# Typical state statute of limitations for refund claims (years)
_STATUTE_OF_LIMITATIONS: dict[str, int] = {
    "default": 3,
    "CA": 3,
    "NY": 3,
    "TX": 4,
    "FL": 3,
    "IL": 4,
    "PA": 3,
    "OH": 4,
    "NJ": 4,
    "WA": 4,
    "GA": 3,
    "NC": 3,
    "VA": 3,
    "MA": 3,
    "MN": 3,
    "CO": 3,
    "SC": 3,
    "AZ": 4,
    "TN": 3,
    "MO": 3,
}

# Estimated claim success rate used for recovery projections
_ESTIMATED_RECOVERY_RATE = Decimal("0.85")


def _get_sol_years(state_code: str) -> int:
    return _STATUTE_OF_LIMITATIONS.get(
        state_code, _STATUTE_OF_LIMITATIONS["default"]
    )


def _round(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class RefundAnalyzer:
    """
    Analyzes transaction history to identify refund opportunities.

    Compares tax actually paid against tax that should have been owed,
    considering correct rates, exemptions, and jurisdiction assignments.
    """

    def __init__(
        self,
        db: Optional[TaxRateDatabase] = None,
        calculator: Optional[TaxCalculator] = None,
    ) -> None:
        self.db = db or TaxRateDatabase()
        self.calculator = calculator or TaxCalculator(self.db)

    def _check_statute_of_limitations(
        self, txn_date: date, state_code: str, as_of: Optional[date] = None
    ) -> tuple[bool, Optional[date]]:
        """Check if a transaction is within the refund statute of limitations."""
        ref = as_of or date.today()
        sol_years = _get_sol_years(state_code)
        cutoff = date(ref.year - sol_years, ref.month, ref.day)
        sol_date = date(txn_date.year + sol_years, txn_date.month, txn_date.day)
        return txn_date >= cutoff, sol_date

    def analyze_transaction(
        self,
        txn: Transaction,
        tax_paid: Decimal,
        as_of: Optional[date] = None,
    ) -> Optional[OverpaymentRecord]:
        """
        Analyze a single transaction for overpayment.

        Compares the tax actually paid against the correctly calculated
        amount, considering rates and exemptions.

        Returns an OverpaymentRecord if an overpayment is found, else None.
        """
        result: TaxResult = self.calculator.calculate(txn)
        tax_owed = result.tax_amount
        overpayment = _round(tax_paid - tax_owed)

        if overpayment <= Decimal("0"):
            return None

        # Determine reason
        reason: str
        if result.is_exempt:
            reason = f"Exempt transaction taxed: {result.exemption_reason}"
        elif tax_paid > tax_owed:
            expected_rate = result.effective_rate
            if tax_owed > 0:
                actual_rate = float(tax_paid / txn.amount)
                reason = (
                    f"Rate mismatch: paid {actual_rate:.4%}, "
                    f"correct rate {expected_rate:.4%}"
                )
            else:
                reason = "Tax collected in no-tax jurisdiction"
        else:
            reason = "Overpayment detected"

        # Statute of limitations check
        eligible, sol_date = self._check_statute_of_limitations(
            txn.transaction_date, txn.state, as_of
        )

        return OverpaymentRecord(
            transaction_id=txn.transaction_id,
            transaction_date=txn.transaction_date,
            state=txn.state,
            city=txn.city,
            sale_amount=txn.amount,
            tax_paid=tax_paid,
            tax_owed=tax_owed,
            overpayment=overpayment,
            reason=reason,
            refund_eligible=eligible,
            statute_of_limitations_date=sol_date,
        )

    def analyze_batch(
        self,
        transactions: list[tuple[Transaction, Decimal]],
        as_of: Optional[date] = None,
    ) -> RefundSummary:
        """
        Analyze a batch of (transaction, tax_paid) pairs for overpayments.

        Returns a RefundSummary with all identified overpayments,
        state and reason breakdowns, and an estimated recovery amount.
        """
        records: list[OverpaymentRecord] = []
        total_overpayment = Decimal("0")
        state_totals: dict[str, Decimal] = {}
        reason_totals: dict[str, Decimal] = {}
        warnings: list[str] = []

        for txn, tax_paid in transactions:
            record = self.analyze_transaction(txn, tax_paid, as_of)
            if record is not None:
                records.append(record)
                total_overpayment += record.overpayment

                state_totals[record.state] = (
                    state_totals.get(record.state, Decimal("0"))
                    + record.overpayment
                )

                reason_key = record.reason.split(":")[0]
                reason_totals[reason_key] = (
                    reason_totals.get(reason_key, Decimal("0"))
                    + record.overpayment
                )

                if not record.refund_eligible:
                    warnings.append(
                        f"Transaction {record.transaction_id} in {record.state} "
                        f"is past statute of limitations "
                        f"(${record.overpayment:.2f})"
                    )

        eligible_records = [r for r in records if r.refund_eligible]
        eligible_dates = [r.transaction_date for r in eligible_records]

        eligible_overpayment = sum(
            (r.overpayment for r in eligible_records), Decimal("0")
        )

        return RefundSummary(
            total_overpayment=total_overpayment,
            total_transactions_reviewed=len(transactions),
            overpayment_count=len(records),
            records=records,
            state_breakdown=state_totals,
            reason_breakdown=reason_totals,
            oldest_eligible=min(eligible_dates) if eligible_dates else None,
            newest_eligible=max(eligible_dates) if eligible_dates else None,
            estimated_recovery=_round(
                eligible_overpayment * _ESTIMATED_RECOVERY_RATE
            ),
            warnings=warnings,
        )

    def generate_refund_claims(
        self, summary: RefundSummary
    ) -> list[RefundClaim]:
        """
        Generate state-by-state refund claim data from an analysis summary.

        Groups eligible overpayments by state and produces the data
        structure needed for each state's refund filing.
        """
        state_records: dict[str, list[OverpaymentRecord]] = {}
        for record in summary.records:
            if not record.refund_eligible:
                continue
            if record.state not in state_records:
                state_records[record.state] = []
            state_records[record.state].append(record)

        claims: list[RefundClaim] = []
        for state_code, records in state_records.items():
            dates = [r.transaction_date for r in records]
            reasons = list({r.reason.split(":")[0] for r in records})
            total = sum((r.overpayment for r in records), Decimal("0"))

            sol_years = _get_sol_years(state_code)
            claims.append(
                RefundClaim(
                    state_code=state_code,
                    claim_period_start=min(dates),
                    claim_period_end=max(dates),
                    total_refund_requested=total,
                    transaction_count=len(records),
                    records=records,
                    supporting_reasons=reasons,
                    filing_notes=(
                        f"Refund claim for {len(records)} transactions. "
                        f"SOL: {sol_years} years from transaction date. "
                        f"Total requested: ${total:,.2f}"
                    ),
                )
            )

        return sorted(
            claims, key=lambda c: c.total_refund_requested, reverse=True
        )

    def quick_scan(
        self,
        transactions: list[tuple[Transaction, Decimal]],
        minimum_overpayment: Decimal = Decimal("1.00"),
    ) -> list[OverpaymentRecord]:
        """
        Fast scan for obvious overpayments above a minimum threshold.

        Useful for a quick check before running full analysis.
        """
        hits: list[OverpaymentRecord] = []
        for txn, tax_paid in transactions:
            record = self.analyze_transaction(txn, tax_paid)
            if record and record.overpayment >= minimum_overpayment:
                hits.append(record)
        return hits

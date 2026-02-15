"""
Multi-jurisdiction sales tax calculation engine.

Handles:
- Single and batch transaction tax computation
- Multi-state jurisdiction resolution
- Exemption application
- Tax-inclusive (back-out) and tax-exclusive pricing
- Use tax calculation for out-of-state purchases
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional

from tax_engine.rates import ExemptionCategory, TaxRateDatabase


class PricingModel(Enum):
    TAX_EXCLUSIVE = "exclusive"  # tax added on top of price
    TAX_INCLUSIVE = "inclusive"  # tax already embedded in price


@dataclass
class Transaction:
    """A single taxable transaction."""

    transaction_id: str
    transaction_date: date
    amount: Decimal
    state: str
    city: Optional[str] = None
    item_category: Optional[str] = None
    exemption_certificate: Optional[str] = None
    customer_type: str = "retail"  # retail, wholesale, exempt
    pricing_model: PricingModel = PricingModel.TAX_EXCLUSIVE

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        return cls(
            transaction_id=str(data.get("transaction_id", "")),
            transaction_date=(
                date.fromisoformat(data["transaction_date"])
                if isinstance(data.get("transaction_date"), str)
                else data.get("transaction_date", date.today())
            ),
            amount=Decimal(str(data["amount"])),
            state=data["state"],
            city=data.get("city"),
            item_category=data.get("item_category"),
            exemption_certificate=data.get("exemption_certificate"),
            customer_type=data.get("customer_type", "retail"),
        )


@dataclass
class TaxResult:
    """Result of a tax calculation for a single transaction."""

    transaction_id: str
    taxable_amount: Decimal
    tax_amount: Decimal
    effective_rate: float
    state: str
    city: Optional[str]
    state_tax: Decimal
    local_tax: Decimal
    is_exempt: bool = False
    exemption_reason: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def total_with_tax(self) -> Decimal:
        return self.taxable_amount + self.tax_amount


@dataclass
class BatchResult:
    """Aggregated result for a batch of transactions."""

    results: list[TaxResult]
    total_taxable: Decimal
    total_tax: Decimal
    total_exempt: Decimal
    transaction_count: int
    exempt_count: int
    state_breakdown: dict[str, Decimal]
    errors: list[str]


# Map common item categories to exemption categories
_CATEGORY_MAP: dict[str, ExemptionCategory] = {
    "grocery": ExemptionCategory.GROCERY,
    "groceries": ExemptionCategory.GROCERY,
    "food": ExemptionCategory.GROCERY,
    "clothing": ExemptionCategory.CLOTHING,
    "apparel": ExemptionCategory.CLOTHING,
    "prescription": ExemptionCategory.PRESCRIPTION_DRUG,
    "prescription_drug": ExemptionCategory.PRESCRIPTION_DRUG,
    "rx": ExemptionCategory.PRESCRIPTION_DRUG,
    "medical": ExemptionCategory.MEDICAL_DEVICE,
    "medical_device": ExemptionCategory.MEDICAL_DEVICE,
    "manufacturing": ExemptionCategory.MANUFACTURING_EQUIPMENT,
    "agricultural": ExemptionCategory.AGRICULTURAL,
    "resale": ExemptionCategory.RESALE,
    "software": ExemptionCategory.SOFTWARE_SAAS,
    "saas": ExemptionCategory.SOFTWARE_SAAS,
    "digital": ExemptionCategory.DIGITAL_GOODS,
}


def _round_tax(amount: Decimal) -> Decimal:
    """Round tax to the nearest cent using banker's rounding variant."""
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class TaxCalculator:
    """
    Sales tax calculation engine.

    Resolves jurisdiction rates, applies exemptions, and computes
    tax for individual transactions or batches.
    """

    def __init__(self, db: Optional[TaxRateDatabase] = None) -> None:
        self.db = db or TaxRateDatabase()

    def _resolve_exemption(
        self, txn: Transaction
    ) -> tuple[bool, str]:
        """
        Determine if a transaction qualifies for exemption.

        Returns (is_exempt, reason).
        """
        # Exempt customer types
        if txn.customer_type in ("wholesale", "exempt"):
            return True, f"Customer type: {txn.customer_type}"

        # Exemption certificate on file
        if txn.exemption_certificate:
            return True, f"Exemption cert: {txn.exemption_certificate}"

        # Category-based exemption
        if txn.item_category:
            cat_key = txn.item_category.lower().strip()
            exemption_cat = _CATEGORY_MAP.get(cat_key)
            if exemption_cat and self.db.is_exempt(txn.state, exemption_cat):
                return True, f"{txn.state} exempts {exemption_cat.value}"

        return False, ""

    def calculate(self, txn: Transaction) -> TaxResult:
        """
        Calculate sales tax for a single transaction.

        Handles exemptions, multi-jurisdiction rates, and
        tax-inclusive back-out calculations.
        """
        state = self.db.get_state(txn.state)
        if state is None:
            return TaxResult(
                transaction_id=txn.transaction_id,
                taxable_amount=txn.amount,
                tax_amount=Decimal("0.00"),
                effective_rate=0.0,
                state=txn.state,
                city=txn.city,
                state_tax=Decimal("0.00"),
                local_tax=Decimal("0.00"),
                is_exempt=False,
                exemption_reason="",
                warnings=[f"Unknown state code: {txn.state}"],
            )

        # No-tax states
        if state.base_rate == 0.0 and not state.has_local_taxes:
            return TaxResult(
                transaction_id=txn.transaction_id,
                taxable_amount=txn.amount,
                tax_amount=Decimal("0.00"),
                effective_rate=0.0,
                state=txn.state,
                city=txn.city,
                state_tax=Decimal("0.00"),
                local_tax=Decimal("0.00"),
                is_exempt=True,
                exemption_reason=f"{state.state_name} has no sales tax",
            )

        # Check exemptions
        is_exempt, reason = self._resolve_exemption(txn)
        if is_exempt:
            return TaxResult(
                transaction_id=txn.transaction_id,
                taxable_amount=txn.amount,
                tax_amount=Decimal("0.00"),
                effective_rate=0.0,
                state=txn.state,
                city=txn.city,
                state_tax=Decimal("0.00"),
                local_tax=Decimal("0.00"),
                is_exempt=True,
                exemption_reason=reason,
            )

        # Resolve rates
        state_rate = Decimal(str(state.base_rate))
        local_rate = Decimal("0")
        if txn.city:
            local = self.db.get_local_rate(txn.state, txn.city)
            if local:
                local_rate = Decimal(str(local.rate))
            elif state.has_local_taxes:
                # Approximate with average local portion
                avg_local = Decimal(str(state.avg_combined_rate)) - state_rate
                local_rate = max(avg_local, Decimal("0"))
        elif state.has_local_taxes:
            avg_local = Decimal(str(state.avg_combined_rate)) - state_rate
            local_rate = max(avg_local, Decimal("0"))

        combined_rate = state_rate + local_rate

        # Compute taxable amount
        if txn.pricing_model == PricingModel.TAX_INCLUSIVE:
            # Back out tax from the total
            taxable = txn.amount / (1 + combined_rate)
            taxable = _round_tax(taxable)
        else:
            taxable = txn.amount

        state_tax = _round_tax(taxable * state_rate)
        local_tax_amt = _round_tax(taxable * local_rate)
        total_tax = state_tax + local_tax_amt

        warnings: list[str] = []
        if not txn.city and state.has_local_taxes:
            warnings.append(
                f"No city specified for {txn.state}; used average local rate"
            )

        return TaxResult(
            transaction_id=txn.transaction_id,
            taxable_amount=taxable,
            tax_amount=total_tax,
            effective_rate=float(combined_rate),
            state=txn.state,
            city=txn.city,
            state_tax=state_tax,
            local_tax=local_tax_amt,
            warnings=warnings,
        )

    def calculate_batch(
        self, transactions: list[Transaction]
    ) -> BatchResult:
        """
        Calculate tax for a batch of transactions.

        Returns aggregated results with state-level breakdown.
        """
        results: list[TaxResult] = []
        errors: list[str] = []
        total_taxable = Decimal("0")
        total_tax = Decimal("0")
        total_exempt = Decimal("0")
        exempt_count = 0
        state_tax_totals: dict[str, Decimal] = {}

        for txn in transactions:
            try:
                result = self.calculate(txn)
                results.append(result)
                total_taxable += result.taxable_amount
                total_tax += result.tax_amount

                if result.is_exempt:
                    exempt_count += 1
                    total_exempt += result.taxable_amount

                state_tax_totals[txn.state] = (
                    state_tax_totals.get(txn.state, Decimal("0"))
                    + result.tax_amount
                )
            except Exception as e:
                errors.append(
                    f"Transaction {txn.transaction_id}: {str(e)}"
                )

        return BatchResult(
            results=results,
            total_taxable=total_taxable,
            total_tax=total_tax,
            total_exempt=total_exempt,
            transaction_count=len(transactions),
            exempt_count=exempt_count,
            state_breakdown=state_tax_totals,
            errors=errors,
        )

    def calculate_use_tax(
        self,
        purchase_amount: Decimal,
        destination_state: str,
        destination_city: Optional[str] = None,
        tax_already_paid: Decimal = Decimal("0"),
    ) -> TaxResult:
        """
        Calculate use tax owed on an out-of-state purchase.

        Use tax applies when sales tax was not collected at point of sale
        but the item is used in a state that imposes sales/use tax.
        Credit is given for any tax already paid to the origin state.
        """
        txn = Transaction(
            transaction_id="use-tax-calc",
            transaction_date=date.today(),
            amount=purchase_amount,
            state=destination_state,
            city=destination_city,
        )

        result = self.calculate(txn)
        credit = min(tax_already_paid, result.tax_amount)
        net_use_tax = result.tax_amount - credit

        return TaxResult(
            transaction_id="use-tax-calc",
            taxable_amount=purchase_amount,
            tax_amount=_round_tax(net_use_tax),
            effective_rate=result.effective_rate,
            state=destination_state,
            city=destination_city,
            state_tax=result.state_tax,
            local_tax=result.local_tax,
            warnings=[
                f"Credit applied for ${credit:.2f} tax already paid"
            ]
            if credit > 0
            else [],
        )

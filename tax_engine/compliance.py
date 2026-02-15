"""
Sales tax compliance checker.

Monitors:
- Filing deadlines by state and frequency
- Economic nexus thresholds (post-Wayfair)
- Overdue return detection
- Registration requirements
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional


class FilingFrequency(Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"


class NexusType(Enum):
    PHYSICAL = "physical"  # office, warehouse, employees
    ECONOMIC = "economic"  # revenue/transaction threshold
    CLICK_THROUGH = "click_through"  # affiliate referrals
    MARKETPLACE = "marketplace"  # marketplace facilitator


@dataclass(frozen=True)
class NexusThreshold:
    """
    Economic nexus threshold for a state.

    Post-Wayfair, most states adopted $100k revenue OR 200 transactions
    as the bright-line threshold, though specifics vary.
    """

    state_code: str
    revenue_threshold: Decimal
    transaction_threshold: Optional[int]
    measurement_period: str  # "current_year", "prior_year", "rolling_12"
    includes_exempt_sales: bool = False
    includes_marketplace_sales: bool = False


@dataclass
class NexusStatus:
    """Result of a nexus analysis for a single state."""

    state_code: str
    has_nexus: bool
    nexus_types: list[NexusType]
    revenue_in_state: Decimal
    transactions_in_state: int
    revenue_threshold: Decimal
    transaction_threshold: Optional[int]
    revenue_pct_of_threshold: float
    transaction_pct_of_threshold: Optional[float]
    approaching_threshold: bool  # within 80%
    details: str = ""


@dataclass
class FilingDeadline:
    """A filing deadline for a specific state and period."""

    state_code: str
    period_start: date
    period_end: date
    due_date: date
    frequency: FilingFrequency
    is_overdue: bool = False
    days_until_due: int = 0
    estimated_liability: Decimal = Decimal("0")
    status: str = "pending"  # pending, filed, overdue, extension


@dataclass
class ComplianceAlert:
    """An actionable compliance alert."""

    severity: str  # critical, warning, info
    state_code: str
    message: str
    action_required: str
    deadline: Optional[date] = None


# -----------------------------------------------------------------------
# Economic nexus thresholds by state (post-Wayfair standards)
# -----------------------------------------------------------------------

_NEXUS_THRESHOLDS: dict[str, dict] = {
    "AL": {"revenue": 250000, "transactions": None, "period": "prior_year"},
    "AK": {"revenue": 100000, "transactions": 200, "period": "current_year"},
    "AZ": {"revenue": 100000, "transactions": None, "period": "prior_year"},
    "AR": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "CA": {"revenue": 500000, "transactions": None, "period": "current_or_prior"},
    "CO": {"revenue": 100000, "transactions": None, "period": "prior_year"},
    "CT": {"revenue": 100000, "transactions": 200, "period": "rolling_12"},
    "FL": {"revenue": 100000, "transactions": None, "period": "prior_year"},
    "GA": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "HI": {"revenue": 100000, "transactions": 200, "period": "current_year"},
    "ID": {"revenue": 100000, "transactions": None, "period": "current_year"},
    "IL": {"revenue": 100000, "transactions": 200, "period": "rolling_12"},
    "IN": {"revenue": 100000, "transactions": 200, "period": "current_year"},
    "IA": {"revenue": 100000, "transactions": None, "period": "current_or_prior"},
    "KS": {"revenue": 100000, "transactions": None, "period": "current_year"},
    "KY": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "LA": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "ME": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "MD": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "MA": {"revenue": 100000, "transactions": None, "period": "current_or_prior"},
    "MI": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "MN": {"revenue": 100000, "transactions": 10, "period": "rolling_12"},
    "MS": {"revenue": 250000, "transactions": None, "period": "rolling_12"},
    "MO": {"revenue": 100000, "transactions": None, "period": "prior_year"},
    "NE": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "NV": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "NJ": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "NM": {"revenue": 100000, "transactions": None, "period": "current_year"},
    "NY": {"revenue": 500000, "transactions": 100, "period": "rolling_4q"},
    "NC": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "ND": {"revenue": 100000, "transactions": None, "period": "current_or_prior"},
    "OH": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "OK": {"revenue": 100000, "transactions": None, "period": "current_or_prior"},
    "PA": {"revenue": 100000, "transactions": None, "period": "current_year"},
    "RI": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "SC": {"revenue": 100000, "transactions": None, "period": "current_or_prior"},
    "SD": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "TN": {"revenue": 100000, "transactions": None, "period": "rolling_12"},
    "TX": {"revenue": 500000, "transactions": None, "period": "rolling_12"},
    "UT": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "VT": {"revenue": 100000, "transactions": 200, "period": "rolling_12"},
    "VA": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "WA": {"revenue": 100000, "transactions": None, "period": "current_or_prior"},
    "WV": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "WI": {"revenue": 100000, "transactions": None, "period": "current_year"},
    "WY": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
    "DC": {"revenue": 100000, "transactions": 200, "period": "current_or_prior"},
}

# States with no economic nexus (no state sales tax)
_NO_NEXUS_STATES = {"DE", "MT", "NH", "OR"}

# Standard filing due dates: day of month after period end
_FILING_DUE_DAY: dict[str, int] = {
    "default": 20,
    "CA": 25,  # last day of month following
    "FL": 20,
    "NY": 20,
    "TX": 20,
    "IL": 20,
    "PA": 20,
    "OH": 23,
    "NJ": 20,
    "WA": 25,
    "GA": 20,
}


def _get_due_day(state_code: str) -> int:
    return _FILING_DUE_DAY.get(state_code, _FILING_DUE_DAY["default"])


def _compute_due_date(period_end: date, state_code: str) -> date:
    """
    Compute the filing due date for a given period end.

    Generally the 20th of the month following the period end.
    """
    due_day = _get_due_day(state_code)
    # Due date is in the month after period_end
    if period_end.month == 12:
        due = date(period_end.year + 1, 1, due_day)
    else:
        due = date(period_end.year, period_end.month + 1, due_day)
    return due


def _determine_frequency(annual_liability: Decimal) -> FilingFrequency:
    """
    Determine filing frequency based on estimated annual liability.

    Common state thresholds:
    - > $4,800/yr or > $400/mo -> monthly
    - > $1,200/yr -> quarterly
    - > $0 -> annual
    """
    if annual_liability >= 4800:
        return FilingFrequency.MONTHLY
    elif annual_liability >= 1200:
        return FilingFrequency.QUARTERLY
    else:
        return FilingFrequency.ANNUAL


class ComplianceChecker:
    """
    Monitors filing obligations, nexus thresholds, and compliance status.

    Designed for multi-state sellers managing ongoing filing requirements.
    """

    def __init__(self) -> None:
        self._nexus_thresholds = self._load_thresholds()
        self._registered_states: set[str] = set()
        self._filed_periods: dict[str, set[str]] = {}  # state -> set of period keys

    def _load_thresholds(self) -> dict[str, NexusThreshold]:
        thresholds: dict[str, NexusThreshold] = {}
        for code, data in _NEXUS_THRESHOLDS.items():
            thresholds[code] = NexusThreshold(
                state_code=code,
                revenue_threshold=Decimal(str(data["revenue"])),
                transaction_threshold=data["transactions"],
                measurement_period=data["period"],
            )
        return thresholds

    def register_state(self, state_code: str) -> None:
        """Mark a state as registered for sales tax collection."""
        self._registered_states.add(state_code.upper())

    def register_states(self, states: list[str]) -> None:
        """Bulk register multiple states."""
        for s in states:
            self.register_state(s)

    def mark_filed(
        self, state_code: str, period_start: date, period_end: date
    ) -> None:
        """Record that a return has been filed for a given period."""
        key = f"{period_start.isoformat()}_{period_end.isoformat()}"
        if state_code not in self._filed_periods:
            self._filed_periods[state_code] = set()
        self._filed_periods[state_code].add(key)

    def check_nexus(
        self,
        state_code: str,
        revenue: Decimal,
        transaction_count: int,
        physical_presence: bool = False,
    ) -> NexusStatus:
        """
        Evaluate nexus status for a single state.

        Considers both economic thresholds and physical presence.
        """
        state_code = state_code.upper()

        if state_code in _NO_NEXUS_STATES:
            return NexusStatus(
                state_code=state_code,
                has_nexus=False,
                nexus_types=[],
                revenue_in_state=revenue,
                transactions_in_state=transaction_count,
                revenue_threshold=Decimal("0"),
                transaction_threshold=None,
                revenue_pct_of_threshold=0.0,
                transaction_pct_of_threshold=None,
                approaching_threshold=False,
                details=f"{state_code} has no sales tax",
            )

        threshold = self._nexus_thresholds.get(state_code)
        if threshold is None:
            return NexusStatus(
                state_code=state_code,
                has_nexus=physical_presence,
                nexus_types=[NexusType.PHYSICAL] if physical_presence else [],
                revenue_in_state=revenue,
                transactions_in_state=transaction_count,
                revenue_threshold=Decimal("0"),
                transaction_threshold=None,
                revenue_pct_of_threshold=0.0,
                transaction_pct_of_threshold=None,
                approaching_threshold=False,
                details="No economic nexus data available",
            )

        nexus_types: list[NexusType] = []
        if physical_presence:
            nexus_types.append(NexusType.PHYSICAL)

        rev_pct = (
            float(revenue / threshold.revenue_threshold) * 100
            if threshold.revenue_threshold > 0
            else 0.0
        )

        txn_pct: Optional[float] = None
        if threshold.transaction_threshold is not None:
            txn_pct = (
                transaction_count / threshold.transaction_threshold
            ) * 100

        economic_nexus = revenue >= threshold.revenue_threshold
        if (
            not economic_nexus
            and threshold.transaction_threshold is not None
        ):
            economic_nexus = transaction_count >= threshold.transaction_threshold

        if economic_nexus:
            nexus_types.append(NexusType.ECONOMIC)

        has_nexus = len(nexus_types) > 0
        approaching = rev_pct >= 80 or (txn_pct is not None and txn_pct >= 80)

        details_parts: list[str] = []
        details_parts.append(
            f"Revenue: ${revenue:,.2f} / ${threshold.revenue_threshold:,.2f} "
            f"({rev_pct:.1f}%)"
        )
        if threshold.transaction_threshold is not None:
            details_parts.append(
                f"Transactions: {transaction_count} / "
                f"{threshold.transaction_threshold} ({txn_pct:.1f}%)"
            )
        details_parts.append(f"Period: {threshold.measurement_period}")

        return NexusStatus(
            state_code=state_code,
            has_nexus=has_nexus,
            nexus_types=nexus_types,
            revenue_in_state=revenue,
            transactions_in_state=transaction_count,
            revenue_threshold=threshold.revenue_threshold,
            transaction_threshold=threshold.transaction_threshold,
            revenue_pct_of_threshold=rev_pct,
            transaction_pct_of_threshold=txn_pct,
            approaching_threshold=approaching and not has_nexus,
            details="; ".join(details_parts),
        )

    def check_nexus_all_states(
        self,
        state_revenues: dict[str, Decimal],
        state_transactions: dict[str, int],
        physical_states: Optional[set[str]] = None,
    ) -> list[NexusStatus]:
        """
        Evaluate nexus across all states where activity exists.

        Returns results sorted by revenue percentage (highest first).
        """
        physical = physical_states or set()
        all_states = set(state_revenues.keys()) | set(state_transactions.keys())
        results: list[NexusStatus] = []

        for state in all_states:
            rev = state_revenues.get(state, Decimal("0"))
            txn = state_transactions.get(state, 0)
            status = self.check_nexus(
                state, rev, txn, state.upper() in physical
            )
            results.append(status)

        return sorted(
            results, key=lambda s: s.revenue_pct_of_threshold, reverse=True
        )

    def get_filing_deadlines(
        self,
        state_code: str,
        year: int,
        frequency: Optional[FilingFrequency] = None,
        estimated_annual_liability: Decimal = Decimal("0"),
        as_of: Optional[date] = None,
    ) -> list[FilingDeadline]:
        """
        Generate filing deadlines for a state and year.

        Auto-determines frequency based on liability if not specified.
        """
        ref_date = as_of or date.today()
        freq = frequency or _determine_frequency(estimated_annual_liability)
        deadlines: list[FilingDeadline] = []

        if freq == FilingFrequency.MONTHLY:
            for month in range(1, 13):
                p_start = date(year, month, 1)
                if month == 12:
                    p_end = date(year, 12, 31)
                else:
                    p_end = date(year, month + 1, 1) - timedelta(days=1)
                due = _compute_due_date(p_end, state_code)
                period_key = f"{p_start.isoformat()}_{p_end.isoformat()}"
                is_filed = (
                    state_code in self._filed_periods
                    and period_key in self._filed_periods[state_code]
                )
                is_overdue = due < ref_date and not is_filed
                days_until = (due - ref_date).days

                deadlines.append(
                    FilingDeadline(
                        state_code=state_code,
                        period_start=p_start,
                        period_end=p_end,
                        due_date=due,
                        frequency=freq,
                        is_overdue=is_overdue,
                        days_until_due=days_until,
                        estimated_liability=estimated_annual_liability / 12,
                        status="filed" if is_filed else (
                            "overdue" if is_overdue else "pending"
                        ),
                    )
                )

        elif freq == FilingFrequency.QUARTERLY:
            quarters = [
                (date(year, 1, 1), date(year, 3, 31)),
                (date(year, 4, 1), date(year, 6, 30)),
                (date(year, 7, 1), date(year, 9, 30)),
                (date(year, 10, 1), date(year, 12, 31)),
            ]
            for p_start, p_end in quarters:
                due = _compute_due_date(p_end, state_code)
                period_key = f"{p_start.isoformat()}_{p_end.isoformat()}"
                is_filed = (
                    state_code in self._filed_periods
                    and period_key in self._filed_periods[state_code]
                )
                is_overdue = due < ref_date and not is_filed
                days_until = (due - ref_date).days

                deadlines.append(
                    FilingDeadline(
                        state_code=state_code,
                        period_start=p_start,
                        period_end=p_end,
                        due_date=due,
                        frequency=freq,
                        is_overdue=is_overdue,
                        days_until_due=days_until,
                        estimated_liability=estimated_annual_liability / 4,
                        status="filed" if is_filed else (
                            "overdue" if is_overdue else "pending"
                        ),
                    )
                )

        elif freq == FilingFrequency.ANNUAL:
            p_start = date(year, 1, 1)
            p_end = date(year, 12, 31)
            due = _compute_due_date(p_end, state_code)
            period_key = f"{p_start.isoformat()}_{p_end.isoformat()}"
            is_filed = (
                state_code in self._filed_periods
                and period_key in self._filed_periods[state_code]
            )
            is_overdue = due < ref_date and not is_filed
            days_until = (due - ref_date).days

            deadlines.append(
                FilingDeadline(
                    state_code=state_code,
                    period_start=p_start,
                    period_end=p_end,
                    due_date=due,
                    frequency=freq,
                    is_overdue=is_overdue,
                    days_until_due=days_until,
                    estimated_liability=estimated_annual_liability,
                    status="filed" if is_filed else (
                        "overdue" if is_overdue else "pending"
                    ),
                )
            )

        return deadlines

    def get_overdue_filings(
        self,
        registered_states: Optional[list[str]] = None,
        year: int = 2024,
        as_of: Optional[date] = None,
    ) -> list[FilingDeadline]:
        """Return all overdue filing deadlines across registered states."""
        states = registered_states or list(self._registered_states)
        overdue: list[FilingDeadline] = []
        for state in states:
            deadlines = self.get_filing_deadlines(
                state, year, as_of=as_of
            )
            overdue.extend(d for d in deadlines if d.is_overdue)
        return sorted(overdue, key=lambda d: d.due_date)

    def generate_alerts(
        self,
        state_revenues: dict[str, Decimal],
        state_transactions: dict[str, int],
        registered_states: Optional[list[str]] = None,
        as_of: Optional[date] = None,
    ) -> list[ComplianceAlert]:
        """
        Generate compliance alerts based on current state.

        Checks for:
        - Unregistered states where nexus exists
        - States approaching nexus thresholds
        - Overdue filings
        """
        ref_date = as_of or date.today()
        alerts: list[ComplianceAlert] = []
        registered = set(
            s.upper() for s in (registered_states or self._registered_states)
        )

        # Nexus alerts
        for state in set(state_revenues.keys()) | set(state_transactions.keys()):
            status = self.check_nexus(
                state,
                state_revenues.get(state, Decimal("0")),
                state_transactions.get(state, 0),
            )

            if status.has_nexus and state.upper() not in registered:
                alerts.append(
                    ComplianceAlert(
                        severity="critical",
                        state_code=state,
                        message=(
                            f"Economic nexus established in {state} but "
                            f"not registered for sales tax collection"
                        ),
                        action_required=(
                            f"Register for sales tax in {state} immediately. "
                            f"Revenue: ${status.revenue_in_state:,.2f}"
                        ),
                    )
                )
            elif status.approaching_threshold:
                alerts.append(
                    ComplianceAlert(
                        severity="warning",
                        state_code=state,
                        message=(
                            f"Approaching economic nexus threshold in {state} "
                            f"({status.revenue_pct_of_threshold:.0f}% of revenue limit)"
                        ),
                        action_required=(
                            f"Monitor {state} activity. Prepare registration "
                            f"materials proactively."
                        ),
                    )
                )

        # Overdue filing alerts
        for state in registered:
            deadlines = self.get_filing_deadlines(
                state, ref_date.year, as_of=ref_date
            )
            for d in deadlines:
                if d.is_overdue:
                    days_late = (ref_date - d.due_date).days
                    severity = "critical" if days_late > 30 else "warning"
                    alerts.append(
                        ComplianceAlert(
                            severity=severity,
                            state_code=state,
                            message=(
                                f"{state} return for "
                                f"{d.period_start.isoformat()} to "
                                f"{d.period_end.isoformat()} is {days_late} "
                                f"days past due"
                            ),
                            action_required=(
                                f"File {state} return immediately. "
                                f"Late penalties may apply."
                            ),
                            deadline=d.due_date,
                        )
                    )

        return sorted(
            alerts,
            key=lambda a: (
                0 if a.severity == "critical" else (
                    1 if a.severity == "warning" else 2
                )
            ),
        )

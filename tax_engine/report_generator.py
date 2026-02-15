"""
Compliance report generator.

Produces:
- Monthly/quarterly tax liability summaries
- State-by-state breakdowns
- Nexus analysis reports
- Refund opportunity reports
- CSV and JSON export
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from tax_engine.calculator import BatchResult, TaxResult
from tax_engine.compliance import (
    ComplianceAlert,
    ComplianceChecker,
    FilingDeadline,
    NexusStatus,
)
from tax_engine.refund_analyzer import RefundClaim, RefundSummary


class _DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal and date objects."""

    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, date):
            return o.isoformat()
        return super().default(o)


def _decimal_to_float(obj: Any) -> Any:
    """Recursively convert Decimal values to float for serialization."""
    if isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_float(i) for i in obj]
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    return obj


class ReportGenerator:
    """
    Generates formatted compliance reports with export capabilities.

    All reports can be returned as structured dicts, rendered to
    console-friendly text, or exported to CSV/JSON files.
    """

    def __init__(self, output_dir: Optional[str] = None) -> None:
        self.output_dir = Path(output_dir) if output_dir else Path("reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Tax liability summary
    # ------------------------------------------------------------------

    def tax_summary_report(
        self,
        batch_result: BatchResult,
        period_label: str = "",
    ) -> dict[str, Any]:
        """
        Generate a tax liability summary from batch calculation results.

        Returns a structured dict suitable for display or export.
        """
        state_details: list[dict[str, Any]] = []
        state_results: dict[str, list[TaxResult]] = {}

        for r in batch_result.results:
            if r.state not in state_results:
                state_results[r.state] = []
            state_results[r.state].append(r)

        for state_code in sorted(state_results):
            results = state_results[state_code]
            taxable = sum(r.taxable_amount for r in results)
            tax = sum(r.tax_amount for r in results)
            exempt = sum(
                r.taxable_amount for r in results if r.is_exempt
            )
            state_detail = {
                "state": state_code,
                "transaction_count": len(results),
                "taxable_amount": taxable,
                "tax_collected": tax,
                "exempt_amount": exempt,
                "effective_rate": (
                    float(tax / taxable) if taxable > 0 else 0.0
                ),
            }
            state_details.append(state_detail)

        return {
            "report_type": "tax_liability_summary",
            "period": period_label,
            "generated_date": date.today().isoformat(),
            "summary": {
                "total_transactions": batch_result.transaction_count,
                "total_taxable": batch_result.total_taxable,
                "total_tax": batch_result.total_tax,
                "total_exempt": batch_result.total_exempt,
                "exempt_transactions": batch_result.exempt_count,
                "overall_effective_rate": (
                    float(
                        batch_result.total_tax / batch_result.total_taxable
                    )
                    if batch_result.total_taxable > 0
                    else 0.0
                ),
            },
            "state_breakdown": state_details,
            "errors": batch_result.errors,
        }

    # ------------------------------------------------------------------
    # Nexus analysis report
    # ------------------------------------------------------------------

    def nexus_report(
        self, nexus_results: list[NexusStatus]
    ) -> dict[str, Any]:
        """Generate a nexus analysis report."""
        nexus_states = [n for n in nexus_results if n.has_nexus]
        approaching = [n for n in nexus_results if n.approaching_threshold]
        below = [
            n
            for n in nexus_results
            if not n.has_nexus and not n.approaching_threshold
        ]

        return {
            "report_type": "nexus_analysis",
            "generated_date": date.today().isoformat(),
            "summary": {
                "states_with_nexus": len(nexus_states),
                "states_approaching": len(approaching),
                "states_below_threshold": len(below),
                "total_states_analyzed": len(nexus_results),
            },
            "nexus_established": [
                {
                    "state": n.state_code,
                    "nexus_types": [t.value for t in n.nexus_types],
                    "revenue": n.revenue_in_state,
                    "transactions": n.transactions_in_state,
                    "details": n.details,
                }
                for n in nexus_states
            ],
            "approaching_threshold": [
                {
                    "state": n.state_code,
                    "revenue_pct": n.revenue_pct_of_threshold,
                    "transaction_pct": n.transaction_pct_of_threshold,
                    "revenue": n.revenue_in_state,
                    "details": n.details,
                }
                for n in approaching
            ],
            "below_threshold": [
                {
                    "state": n.state_code,
                    "revenue_pct": n.revenue_pct_of_threshold,
                    "revenue": n.revenue_in_state,
                }
                for n in below
            ],
        }

    # ------------------------------------------------------------------
    # Filing status report
    # ------------------------------------------------------------------

    def filing_status_report(
        self,
        deadlines: list[FilingDeadline],
        alerts: Optional[list[ComplianceAlert]] = None,
    ) -> dict[str, Any]:
        """Generate a filing deadline and compliance status report."""
        overdue = [d for d in deadlines if d.is_overdue]
        upcoming = [
            d
            for d in deadlines
            if not d.is_overdue and 0 <= d.days_until_due <= 30
        ]
        filed = [d for d in deadlines if d.status == "filed"]

        def _deadline_dict(d: FilingDeadline) -> dict[str, Any]:
            return {
                "state": d.state_code,
                "period": f"{d.period_start.isoformat()} to {d.period_end.isoformat()}",
                "due_date": d.due_date.isoformat(),
                "status": d.status,
                "days_until_due": d.days_until_due,
                "estimated_liability": d.estimated_liability,
            }

        report: dict[str, Any] = {
            "report_type": "filing_status",
            "generated_date": date.today().isoformat(),
            "summary": {
                "total_filings": len(deadlines),
                "overdue": len(overdue),
                "upcoming_30_days": len(upcoming),
                "filed": len(filed),
            },
            "overdue_filings": [_deadline_dict(d) for d in overdue],
            "upcoming_filings": [_deadline_dict(d) for d in upcoming],
        }

        if alerts:
            report["alerts"] = [
                {
                    "severity": a.severity,
                    "state": a.state_code,
                    "message": a.message,
                    "action": a.action_required,
                }
                for a in alerts
            ]

        return report

    # ------------------------------------------------------------------
    # Refund opportunity report
    # ------------------------------------------------------------------

    def refund_report(
        self,
        summary: RefundSummary,
        claims: Optional[list[RefundClaim]] = None,
    ) -> dict[str, Any]:
        """Generate a refund opportunity analysis report."""
        report: dict[str, Any] = {
            "report_type": "refund_analysis",
            "generated_date": date.today().isoformat(),
            "summary": {
                "transactions_reviewed": summary.total_transactions_reviewed,
                "overpayments_found": summary.overpayment_count,
                "total_overpayment": summary.total_overpayment,
                "estimated_recovery": summary.estimated_recovery,
                "recovery_rate_assumed": "85%",
            },
            "state_breakdown": {
                state: amount
                for state, amount in sorted(
                    summary.state_breakdown.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            },
            "reason_breakdown": {
                reason: amount
                for reason, amount in sorted(
                    summary.reason_breakdown.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            },
            "overpayment_details": [
                {
                    "transaction_id": r.transaction_id,
                    "date": r.transaction_date.isoformat(),
                    "state": r.state,
                    "sale_amount": r.sale_amount,
                    "tax_paid": r.tax_paid,
                    "tax_owed": r.tax_owed,
                    "overpayment": r.overpayment,
                    "reason": r.reason,
                    "eligible": r.refund_eligible,
                }
                for r in summary.records
            ],
            "warnings": summary.warnings,
        }

        if claims:
            report["refund_claims"] = [
                {
                    "state": c.state_code,
                    "period": (
                        f"{c.claim_period_start.isoformat()} to "
                        f"{c.claim_period_end.isoformat()}"
                    ),
                    "amount_requested": c.total_refund_requested,
                    "transaction_count": c.transaction_count,
                    "reasons": c.supporting_reasons,
                    "notes": c.filing_notes,
                }
                for c in claims
            ]

        return report

    # ------------------------------------------------------------------
    # Export methods
    # ------------------------------------------------------------------

    def to_json(
        self,
        report: dict[str, Any],
        filename: Optional[str] = None,
    ) -> str:
        """Export a report to JSON. Returns the JSON string."""
        serializable = _decimal_to_float(report)
        json_str = json.dumps(serializable, indent=2, cls=_DecimalEncoder)

        if filename:
            path = self.output_dir / filename
            path.write_text(json_str, encoding="utf-8")

        return json_str

    def to_csv(
        self,
        report: dict[str, Any],
        filename: Optional[str] = None,
        section: str = "state_breakdown",
    ) -> str:
        """
        Export a report section to CSV. Returns the CSV string.

        The section parameter specifies which list/dict in the report
        to export as rows.
        """
        data = report.get(section, [])
        if not data:
            return ""

        output = io.StringIO()

        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict):
                fieldnames = list(data[0].keys())
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for row in data:
                    writer.writerow(
                        {k: float(v) if isinstance(v, Decimal) else v for k, v in row.items()}
                    )
        elif isinstance(data, dict):
            writer = csv.writer(output)
            writer.writerow(["key", "value"])
            for k, v in data.items():
                writer.writerow([k, float(v) if isinstance(v, Decimal) else v])

        csv_str = output.getvalue()

        if filename:
            path = self.output_dir / filename
            path.write_text(csv_str, encoding="utf-8")

        return csv_str

    def export_transaction_details(
        self,
        results: list[TaxResult],
        filename: str = "transaction_details.csv",
    ) -> str:
        """Export individual transaction calculation results to CSV."""
        output = io.StringIO()
        fieldnames = [
            "transaction_id",
            "state",
            "city",
            "taxable_amount",
            "state_tax",
            "local_tax",
            "total_tax",
            "effective_rate",
            "is_exempt",
            "exemption_reason",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for r in results:
            writer.writerow(
                {
                    "transaction_id": r.transaction_id,
                    "state": r.state,
                    "city": r.city or "",
                    "taxable_amount": float(r.taxable_amount),
                    "state_tax": float(r.state_tax),
                    "local_tax": float(r.local_tax),
                    "total_tax": float(r.tax_amount),
                    "effective_rate": f"{r.effective_rate:.4%}",
                    "is_exempt": r.is_exempt,
                    "exemption_reason": r.exemption_reason,
                }
            )

        csv_str = output.getvalue()
        path = self.output_dir / filename
        path.write_text(csv_str, encoding="utf-8")
        return csv_str

    # ------------------------------------------------------------------
    # Console-formatted text output
    # ------------------------------------------------------------------

    def format_text(self, report: dict[str, Any]) -> str:
        """Format a report as human-readable text for console output."""
        lines: list[str] = []
        report_type = report.get("report_type", "report").replace("_", " ").title()
        lines.append(f"{'=' * 60}")
        lines.append(f"  {report_type}")
        lines.append(f"  Generated: {report.get('generated_date', '')}")
        if report.get("period"):
            lines.append(f"  Period: {report['period']}")
        lines.append(f"{'=' * 60}")
        lines.append("")

        summary = report.get("summary", {})
        if summary:
            lines.append("SUMMARY")
            lines.append("-" * 40)
            for key, value in summary.items():
                label = key.replace("_", " ").title()
                if isinstance(value, (float, Decimal)):
                    if "rate" in key:
                        lines.append(f"  {label}: {float(value):.2%}")
                    else:
                        lines.append(f"  {label}: ${float(value):,.2f}")
                else:
                    lines.append(f"  {label}: {value}")
            lines.append("")

        # State breakdown
        state_data = report.get("state_breakdown", [])
        if state_data:
            lines.append("STATE BREAKDOWN")
            lines.append("-" * 40)
            if isinstance(state_data, list):
                for sd in state_data:
                    state = sd.get("state", "??")
                    taxable = sd.get("taxable_amount", 0)
                    tax = sd.get("tax_collected", sd.get("tax", 0))
                    count = sd.get("transaction_count", "")
                    lines.append(
                        f"  {state}: ${float(taxable):>12,.2f} taxable | "
                        f"${float(tax):>10,.2f} tax | {count} txns"
                    )
            elif isinstance(state_data, dict):
                for state, amount in state_data.items():
                    lines.append(f"  {state}: ${float(amount):>12,.2f}")
            lines.append("")

        # Alerts
        alerts = report.get("alerts", [])
        if alerts:
            lines.append("ALERTS")
            lines.append("-" * 40)
            for a in alerts:
                sev = a.get("severity", "info").upper()
                lines.append(f"  [{sev}] {a.get('state', '')}: {a.get('message', '')}")
                lines.append(f"          Action: {a.get('action', '')}")
            lines.append("")

        # Overdue filings
        overdue = report.get("overdue_filings", [])
        if overdue:
            lines.append("OVERDUE FILINGS")
            lines.append("-" * 40)
            for o in overdue:
                lines.append(
                    f"  {o['state']}: {o['period']} | Due: {o['due_date']} | "
                    f"Est. liability: ${float(o.get('estimated_liability', 0)):,.2f}"
                )
            lines.append("")

        # Refund details
        if report.get("report_type") == "refund_analysis":
            reason_data = report.get("reason_breakdown", {})
            if reason_data:
                lines.append("OVERPAYMENT REASONS")
                lines.append("-" * 40)
                for reason, amount in reason_data.items():
                    lines.append(f"  {reason}: ${float(amount):>10,.2f}")
                lines.append("")

        # Warnings
        warnings = report.get("warnings", [])
        if warnings:
            lines.append("WARNINGS")
            lines.append("-" * 40)
            for w in warnings:
                lines.append(f"  * {w}")
            lines.append("")

        return "\n".join(lines)

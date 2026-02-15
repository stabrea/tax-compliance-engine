"""
Command-line interface for the Tax Compliance Engine.

Provides subcommands for tax calculation, compliance checking,
refund analysis, and report generation.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from tax_engine.rates import TaxRateDatabase, ExemptionCategory
from tax_engine.calculator import TaxCalculator, Transaction
from tax_engine.compliance import ComplianceChecker, FilingFrequency
from tax_engine.refund_analyzer import RefundAnalyzer
from tax_engine.report_generator import ReportGenerator

console = Console()


def _load_transactions_csv(
    path: str,
) -> list[tuple[Transaction, Decimal]]:
    """
    Load transactions from a CSV file.

    Expected columns: transaction_id, transaction_date, amount, state,
                      city, item_category, tax_paid
    """
    transactions: list[tuple[Transaction, Decimal]] = []
    csv_path = Path(path)
    if not csv_path.exists():
        console.print(f"[red]File not found: {path}[/red]")
        sys.exit(1)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            try:
                txn = Transaction(
                    transaction_id=row.get("transaction_id", str(i + 1)),
                    transaction_date=date.fromisoformat(
                        row["transaction_date"]
                    ),
                    amount=Decimal(row["amount"]),
                    state=row["state"].strip().upper(),
                    city=row.get("city", "").strip() or None,
                    item_category=row.get("item_category", "").strip() or None,
                )
                tax_paid = Decimal(row.get("tax_paid", "0"))
                transactions.append((txn, tax_paid))
            except (KeyError, ValueError) as e:
                console.print(
                    f"[yellow]Skipping row {i + 1}: {e}[/yellow]"
                )
    return transactions


# -----------------------------------------------------------------------
# Subcommand: calculate
# -----------------------------------------------------------------------


def cmd_calculate(args: argparse.Namespace) -> None:
    """Calculate sales tax for a single transaction or CSV batch."""
    db = TaxRateDatabase()
    calc = TaxCalculator(db)

    if args.file:
        data = _load_transactions_csv(args.file)
        transactions = [txn for txn, _ in data]
        batch = calc.calculate_batch(transactions)

        table = Table(
            title="Tax Calculation Results",
            box=box.ROUNDED,
            show_lines=True,
        )
        table.add_column("ID", style="dim")
        table.add_column("State")
        table.add_column("City")
        table.add_column("Amount", justify="right")
        table.add_column("Tax", justify="right", style="bold")
        table.add_column("Rate", justify="right")
        table.add_column("Exempt", justify="center")

        for r in batch.results:
            table.add_row(
                r.transaction_id[:12],
                r.state,
                r.city or "-",
                f"${r.taxable_amount:,.2f}",
                f"${r.tax_amount:,.2f}",
                f"{r.effective_rate:.2%}",
                "Y" if r.is_exempt else "",
            )

        console.print(table)
        console.print()
        console.print(
            Panel(
                f"[bold]Total Taxable:[/bold] ${batch.total_taxable:,.2f}\n"
                f"[bold]Total Tax:[/bold] ${batch.total_tax:,.2f}\n"
                f"[bold]Exempt Transactions:[/bold] {batch.exempt_count}",
                title="Batch Summary",
                border_style="green",
            )
        )

        if args.export_json:
            rg = ReportGenerator(args.output_dir or "reports")
            report = rg.tax_summary_report(batch, period_label=args.period or "")
            rg.to_json(report, args.export_json)
            console.print(f"[green]JSON exported to {args.export_json}[/green]")

    else:
        # Single transaction
        if not args.amount or not args.state:
            console.print("[red]Provide --amount and --state, or --file[/red]")
            sys.exit(1)

        txn = Transaction(
            transaction_id="cli-calc",
            transaction_date=date.today(),
            amount=Decimal(args.amount),
            state=args.state.upper(),
            city=args.city,
            item_category=args.category,
        )
        result = calc.calculate(txn)

        console.print(
            Panel(
                f"[bold]State:[/bold] {result.state}\n"
                f"[bold]City:[/bold] {result.city or 'N/A'}\n"
                f"[bold]Taxable Amount:[/bold] ${result.taxable_amount:,.2f}\n"
                f"[bold]State Tax:[/bold] ${result.state_tax:,.2f}\n"
                f"[bold]Local Tax:[/bold] ${result.local_tax:,.2f}\n"
                f"[bold]Total Tax:[/bold] ${result.tax_amount:,.2f}\n"
                f"[bold]Effective Rate:[/bold] {result.effective_rate:.2%}\n"
                f"[bold]Total w/ Tax:[/bold] ${result.total_with_tax:,.2f}\n"
                f"[bold]Exempt:[/bold] {'Yes - ' + result.exemption_reason if result.is_exempt else 'No'}",
                title="Tax Calculation",
                border_style="blue",
            )
        )

        for w in result.warnings:
            console.print(f"[yellow]Warning: {w}[/yellow]")


# -----------------------------------------------------------------------
# Subcommand: rates
# -----------------------------------------------------------------------


def cmd_rates(args: argparse.Namespace) -> None:
    """Display tax rates for a state or all states."""
    db = TaxRateDatabase()

    if args.state:
        state = db.get_state(args.state.upper())
        if not state:
            console.print(f"[red]Unknown state: {args.state}[/red]")
            sys.exit(1)

        console.print(
            Panel(
                f"[bold]State:[/bold] {state.state_name} ({state.state_code})\n"
                f"[bold]Base Rate:[/bold] {state.base_rate:.3%}\n"
                f"[bold]Avg Combined:[/bold] {state.avg_combined_rate:.3%}\n"
                f"[bold]Max Local:[/bold] {state.max_local_rate:.3%}\n"
                f"[bold]Local Taxes:[/bold] {'Yes' if state.has_local_taxes else 'No'}\n"
                f"[bold]Exemptions:[/bold] {', '.join(e.value for e in state.exemptions) or 'None'}\n"
                f"[bold]Notes:[/bold] {state.notes}",
                title=f"{state.state_name} Tax Profile",
                border_style="cyan",
            )
        )

        if state.local_rates:
            table = Table(title="Local Rates", box=box.SIMPLE)
            table.add_column("City")
            table.add_column("County")
            table.add_column("Rate", justify="right")
            table.add_column("Combined", justify="right")
            for local in state.local_rates:
                table.add_row(
                    local.jurisdiction,
                    local.county,
                    f"{local.rate:.3%}",
                    f"{state.base_rate + local.rate:.3%}",
                )
            console.print(table)

    else:
        # All states summary
        table = Table(
            title="US Sales Tax Rates - All States",
            box=box.ROUNDED,
        )
        table.add_column("State", style="bold")
        table.add_column("Name")
        table.add_column("Base Rate", justify="right")
        table.add_column("Avg Combined", justify="right")
        table.add_column("Local", justify="center")

        for state in db.all_states():
            style = "dim" if state.base_rate == 0 else ""
            table.add_row(
                state.state_code,
                state.state_name,
                f"{state.base_rate:.3%}" if state.base_rate > 0 else "None",
                f"{state.avg_combined_rate:.3%}"
                if state.avg_combined_rate > 0
                else "-",
                "Y" if state.has_local_taxes else "",
                style=style,
            )
        console.print(table)


# -----------------------------------------------------------------------
# Subcommand: compliance
# -----------------------------------------------------------------------


def cmd_compliance(args: argparse.Namespace) -> None:
    """Check compliance status: nexus thresholds and filing deadlines."""
    checker = ComplianceChecker()

    if args.file:
        data = _load_transactions_csv(args.file)
        state_revenues: dict[str, Decimal] = {}
        state_txns: dict[str, int] = {}
        for txn, _ in data:
            state_revenues[txn.state] = (
                state_revenues.get(txn.state, Decimal("0")) + txn.amount
            )
            state_txns[txn.state] = state_txns.get(txn.state, 0) + 1

        # Nexus analysis
        results = checker.check_nexus_all_states(state_revenues, state_txns)
        nexus_states = [r for r in results if r.has_nexus]
        approaching = [r for r in results if r.approaching_threshold]

        if nexus_states:
            table = Table(
                title="States with Economic Nexus",
                box=box.ROUNDED,
            )
            table.add_column("State", style="bold")
            table.add_column("Revenue", justify="right")
            table.add_column("Threshold", justify="right")
            table.add_column("% of Threshold", justify="right")
            table.add_column("Transactions", justify="right")

            for n in nexus_states:
                table.add_row(
                    n.state_code,
                    f"${n.revenue_in_state:,.2f}",
                    f"${n.revenue_threshold:,.2f}",
                    f"{n.revenue_pct_of_threshold:.1f}%",
                    str(n.transactions_in_state),
                )
            console.print(table)

        if approaching:
            table = Table(
                title="States Approaching Nexus Threshold",
                box=box.ROUNDED,
                border_style="yellow",
            )
            table.add_column("State", style="bold")
            table.add_column("Revenue", justify="right")
            table.add_column("% of Threshold", justify="right")

            for n in approaching:
                table.add_row(
                    n.state_code,
                    f"${n.revenue_in_state:,.2f}",
                    f"{n.revenue_pct_of_threshold:.1f}%",
                )
            console.print(table)

        # Compliance alerts
        registered = args.registered.split(",") if args.registered else []
        if registered:
            checker.register_states(registered)
        alerts = checker.generate_alerts(state_revenues, state_txns)

        if alerts:
            console.print()
            for alert in alerts:
                color = {
                    "critical": "red",
                    "warning": "yellow",
                    "info": "blue",
                }.get(alert.severity, "white")
                console.print(
                    Panel(
                        f"{alert.message}\n\n[bold]Action:[/bold] {alert.action_required}",
                        title=f"[{color}]{alert.severity.upper()}[/{color}] - {alert.state_code}",
                        border_style=color,
                    )
                )

        if args.export_json:
            rg = ReportGenerator(args.output_dir or "reports")
            report = rg.nexus_report(results)
            rg.to_json(report, args.export_json)
            console.print(f"[green]Report exported to {args.export_json}[/green]")

    else:
        console.print("[yellow]Provide --file with transaction data[/yellow]")


# -----------------------------------------------------------------------
# Subcommand: refund
# -----------------------------------------------------------------------


def cmd_refund(args: argparse.Namespace) -> None:
    """Analyze transactions for refund opportunities."""
    if not args.file:
        console.print("[red]Provide --file with transaction data[/red]")
        sys.exit(1)

    data = _load_transactions_csv(args.file)
    analyzer = RefundAnalyzer()

    min_overpayment = Decimal(args.minimum or "0.50")

    if args.quick:
        hits = analyzer.quick_scan(data, minimum_overpayment=min_overpayment)
        if not hits:
            console.print("[green]No significant overpayments found.[/green]")
            return

        table = Table(
            title="Quick Scan: Overpayments Found",
            box=box.ROUNDED,
        )
        table.add_column("Transaction", style="dim")
        table.add_column("State")
        table.add_column("Amount", justify="right")
        table.add_column("Tax Paid", justify="right")
        table.add_column("Tax Owed", justify="right")
        table.add_column("Overpayment", justify="right", style="bold green")
        table.add_column("Reason")

        for r in hits:
            table.add_row(
                r.transaction_id[:12],
                r.state,
                f"${r.sale_amount:,.2f}",
                f"${r.tax_paid:,.2f}",
                f"${r.tax_owed:,.2f}",
                f"${r.overpayment:,.2f}",
                r.reason[:40],
            )
        console.print(table)
        total = sum(r.overpayment for r in hits)
        console.print(f"\n[bold]Total overpayments: ${total:,.2f}[/bold]")

    else:
        summary = analyzer.analyze_batch(data)
        claims = analyzer.generate_refund_claims(summary)

        rg = ReportGenerator(args.output_dir or "reports")
        report = rg.refund_report(summary, claims)

        console.print(rg.format_text(report))

        if claims:
            console.print()
            table = Table(
                title="Refund Claims to File",
                box=box.ROUNDED,
                border_style="green",
            )
            table.add_column("State", style="bold")
            table.add_column("Period")
            table.add_column("Amount", justify="right", style="bold green")
            table.add_column("Transactions", justify="right")
            table.add_column("Reasons")

            for c in claims:
                table.add_row(
                    c.state_code,
                    f"{c.claim_period_start} to {c.claim_period_end}",
                    f"${c.total_refund_requested:,.2f}",
                    str(c.transaction_count),
                    "; ".join(c.supporting_reasons[:2]),
                )
            console.print(table)

        if args.export_json:
            rg.to_json(report, args.export_json)
            console.print(
                f"[green]Report exported to {args.export_json}[/green]"
            )


# -----------------------------------------------------------------------
# Subcommand: report
# -----------------------------------------------------------------------


def cmd_report(args: argparse.Namespace) -> None:
    """Generate a full compliance report from transaction data."""
    if not args.file:
        console.print("[red]Provide --file with transaction data[/red]")
        sys.exit(1)

    data = _load_transactions_csv(args.file)
    transactions = [txn for txn, _ in data]

    db = TaxRateDatabase()
    calc = TaxCalculator(db)
    checker = ComplianceChecker()
    analyzer = RefundAnalyzer(db, calc)
    rg = ReportGenerator(args.output_dir or "reports")

    # Tax calculation
    batch = calc.calculate_batch(transactions)
    tax_report = rg.tax_summary_report(batch, period_label=args.period or "")
    console.print(rg.format_text(tax_report))

    # Refund analysis
    summary = analyzer.analyze_batch(data)
    if summary.overpayment_count > 0:
        claims = analyzer.generate_refund_claims(summary)
        refund_rpt = rg.refund_report(summary, claims)
        console.print(rg.format_text(refund_rpt))

    # Export
    if args.export_json:
        rg.to_json(tax_report, f"tax_{args.export_json}")
        if summary.overpayment_count > 0:
            rg.to_json(refund_rpt, f"refund_{args.export_json}")
        console.print(f"[green]Reports exported.[/green]")

    if args.export_csv:
        rg.to_csv(tax_report, f"tax_{args.export_csv}", section="state_breakdown")
        rg.export_transaction_details(batch.results, f"details_{args.export_csv}")
        console.print(f"[green]CSV exported.[/green]")


# -----------------------------------------------------------------------
# Argument parser
# -----------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tax-engine",
        description="Sales Tax Compliance Engine - Multi-state tax calculation, compliance monitoring, and refund analysis",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # calculate
    calc_p = subparsers.add_parser("calculate", help="Calculate sales tax")
    calc_p.add_argument("--amount", help="Transaction amount")
    calc_p.add_argument("--state", help="Two-letter state code")
    calc_p.add_argument("--city", help="City name for local rate lookup")
    calc_p.add_argument("--category", help="Item category for exemption check")
    calc_p.add_argument("--file", "-f", help="CSV file with transactions")
    calc_p.add_argument("--period", help="Period label for reports")
    calc_p.add_argument("--export-json", help="Export results to JSON file")
    calc_p.add_argument("--output-dir", help="Output directory for exports")
    calc_p.set_defaults(func=cmd_calculate)

    # rates
    rates_p = subparsers.add_parser("rates", help="View tax rate database")
    rates_p.add_argument("--state", "-s", help="State code to look up")
    rates_p.set_defaults(func=cmd_rates)

    # compliance
    comp_p = subparsers.add_parser(
        "compliance", help="Check nexus and filing compliance"
    )
    comp_p.add_argument("--file", "-f", help="CSV file with transactions")
    comp_p.add_argument(
        "--registered",
        help="Comma-separated list of registered state codes",
    )
    comp_p.add_argument("--export-json", help="Export report to JSON")
    comp_p.add_argument("--output-dir", help="Output directory")
    comp_p.set_defaults(func=cmd_compliance)

    # refund
    refund_p = subparsers.add_parser(
        "refund", help="Analyze refund opportunities"
    )
    refund_p.add_argument("--file", "-f", required=True, help="CSV file with transactions")
    refund_p.add_argument(
        "--quick", "-q", action="store_true", help="Quick scan mode"
    )
    refund_p.add_argument(
        "--minimum", help="Minimum overpayment to report (default: $0.50)"
    )
    refund_p.add_argument("--export-json", help="Export report to JSON")
    refund_p.add_argument("--output-dir", help="Output directory")
    refund_p.set_defaults(func=cmd_refund)

    # report
    report_p = subparsers.add_parser(
        "report", help="Generate full compliance report"
    )
    report_p.add_argument("--file", "-f", required=True, help="CSV file with transactions")
    report_p.add_argument("--period", help="Report period label")
    report_p.add_argument("--export-json", help="Export to JSON filename")
    report_p.add_argument("--export-csv", help="Export to CSV filename")
    report_p.add_argument("--output-dir", help="Output directory")
    report_p.set_defaults(func=cmd_report)

    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)

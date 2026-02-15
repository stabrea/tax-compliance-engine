# Tax Compliance Engine

A sales tax compliance automation tool built from hands-on experience preparing multi-state sales tax returns, filing refund claims, and supporting audit responses as a Tax Associate Intern.

This project automates the core workflows I performed manually -- calculating tax liability across jurisdictions, identifying overpayments eligible for refund, monitoring economic nexus thresholds, and tracking filing deadlines. It reflects real-world compliance patterns, not textbook theory.

## Features

- **Multi-Jurisdiction Tax Calculation** -- Compute sales tax for transactions spanning all 50 US states + DC, with state base rates and city/county local overlays
- **Exemption Handling** -- Automatic application of category-based exemptions (grocery, clothing, prescription drugs, medical devices, manufacturing equipment, resale) by state
- **Economic Nexus Monitoring** -- Track revenue and transaction counts against post-Wayfair thresholds for every state; flag when you're approaching or have crossed a threshold
- **Filing Deadline Management** -- Generate monthly/quarterly/annual filing calendars by state, detect overdue returns, and issue compliance alerts
- **Refund Opportunity Analysis** -- Scan transaction history for overpayments caused by rate mismatches, incorrectly taxed exempt items, or tax collected in no-tax jurisdictions
- **Refund Claim Generation** -- Group eligible overpayments by state, check statute of limitations, and produce the data needed for refund filings
- **Report Generation** -- Tax liability summaries, nexus analysis, filing status, and refund reports with CSV/JSON export
- **Use Tax Calculation** -- Calculate use tax owed on out-of-state purchases with credit for tax already paid

## Tax Rate Coverage

Coverage for all 50 states + DC with state-level base rates and local rates for major cities:

| No State Sales Tax | Low Combined (<6%) | Moderate (6-8%) | High Combined (>8%) |
|---|---|---|---|
| AK*, DE, MT, NH, OR | CO, HI, ME, WI, WY, VA, DC | FL, GA, ID, IN, KY, MA, MD, MI, NC, NJ, NM, OH, PA, RI, SC, UT, VT, WV | AL, AZ, AR, CA, CT, IL, KS, LA, MN, MS, MO, NE, NV, NY, ND, OK, SD, TN, TX, WA |

*AK has no state tax but allows local taxes.

Local rate data included for 60+ major cities across all states with local tax authority.

## Installation

```bash
git clone https://github.com/taofikbishi/tax-compliance-engine.git
cd tax-compliance-engine
pip install -r requirements.txt
```

Or install as a package:

```bash
pip install -e .
```

## Usage

### Calculate Tax

Single transaction:

```bash
python main.py calculate --amount 500 --state TX --city Houston
```

```
State: TX
City: Houston
Taxable Amount: $500.00
State Tax: $31.25
Local Tax: $10.00
Total Tax: $41.25
Effective Rate: 8.25%
Total w/ Tax: $541.25
```

Batch from CSV:

```bash
python main.py calculate --file data/sample_transactions.csv
```

### View Tax Rates

```bash
# Single state
python main.py rates --state CA

# All states
python main.py rates
```

### Check Compliance

Analyze nexus exposure and filing obligations:

```bash
python main.py compliance --file data/sample_transactions.csv --registered TX,CA,NY
```

This will:
1. Calculate revenue and transaction counts per state
2. Compare against economic nexus thresholds
3. Flag states where nexus is established but you're not registered
4. Flag states where you're approaching the threshold

### Refund Analysis

Quick scan for overpayments:

```bash
python main.py refund --file data/sample_transactions.csv --quick
```

Full analysis with refund claim generation:

```bash
python main.py refund --file data/sample_transactions.csv --export-json refund_report.json
```

### Full Compliance Report

```bash
python main.py report --file data/sample_transactions.csv \
    --period "Q1 2024" \
    --export-json q1_report.json \
    --export-csv q1_report.csv
```

## Example: Refund Analysis Output

```
============================================================
  Refund Analysis
  Generated: 2024-07-15
============================================================

SUMMARY
----------------------------------------
  Transactions Reviewed: 57
  Overpayments Found: 8
  Total Overpayment: $47.32
  Estimated Recovery: $40.22
  Recovery Rate Assumed: 85%

STATE BREAKDOWN
----------------------------------------
  NY: $18.45
  CA: $12.80
  TX: $9.07
  IL: $7.00

OVERPAYMENT REASONS
----------------------------------------
  Rate mismatch: $35.52
  Exempt transaction taxed: $11.80
```

## CSV Input Format

The engine expects CSV files with these columns:

| Column | Required | Description |
|---|---|---|
| `transaction_id` | Yes | Unique identifier |
| `transaction_date` | Yes | ISO format (YYYY-MM-DD) |
| `amount` | Yes | Pre-tax sale amount |
| `state` | Yes | Two-letter state code |
| `city` | No | City name for local rate lookup |
| `item_category` | No | For exemption matching (grocery, clothing, prescription, etc.) |
| `tax_paid` | No | Actual tax collected (for refund analysis) |

## Architecture

```
tax_engine/
  __init__.py          # Package exports
  rates.py             # 50-state + DC rate database with local overlays
  calculator.py        # Tax calculation engine (single + batch, exemptions, use tax)
  compliance.py        # Nexus thresholds, filing deadlines, compliance alerts
  refund_analyzer.py   # Overpayment detection, SOL checks, claim generation
  report_generator.py  # Report formatting and CSV/JSON export
  cli.py               # argparse CLI with rich output
main.py                # Entry point
data/
  sample_transactions.csv  # 57 sample transactions across 25+ states
```

### Design Decisions

- **Decimal arithmetic** throughout for financial accuracy -- no floating point tax calculations
- **Dataclass-based models** for type safety and clean data flow between modules
- **Statute of limitations awareness** in refund analysis -- won't suggest claims for expired periods
- **Economic nexus thresholds** sourced from state revenue department publications, reflecting post-Wayfair standards
- **Filing frequency auto-detection** based on estimated annual liability, matching how states actually assign schedules

## Background

Built from experience as a Tax Associate Intern where I:

- Prepared and filed multi-state sales tax returns across 15+ jurisdictions
- Identified overpayment patterns and prepared refund filings recovering $50K+ for clients
- Supported audit responses by reconciling transaction-level data against filed returns
- Tracked economic nexus thresholds for e-commerce clients expanding into new states

This tool automates those workflows into a repeatable, auditable system.

## License

MIT License - see [LICENSE](LICENSE) for details.

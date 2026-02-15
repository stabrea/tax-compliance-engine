# Contributing to Tax Compliance Engine

Thank you for your interest in contributing. This guide covers setting up the development environment, running tests, and submitting changes.

## Development Setup

### Prerequisites

- Python 3.10 or later
- pip package manager
- Git

### Clone and Install

```bash
git clone https://github.com/stabrea/tax-compliance-engine.git
cd tax-compliance-engine

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Install the package in editable mode
pip install -e .
```

### Verify Setup

```bash
# Calculate tax for a single transaction
python main.py calculate --amount 100 --state TX --city Houston
```

## Running Tests

Tests live in the `tests/` directory and use `pytest`.

```bash
# Install test dependencies
pip install pytest

# Run the full test suite
pytest tests/ -v

# Run a specific test file
pytest tests/test_calculator.py -v

# Run with verbose output and full tracebacks
pytest tests/ -v --tb=long
```

All tests must pass before submitting a pull request.

## Code Style

- **Type hints**: All functions must have complete type annotations. Use `from __future__ import annotations` for modern syntax.
- **Docstrings**: Every public class and method needs a docstring. Follow the existing style used throughout the codebase.
- **Decimal arithmetic**: All financial calculations must use `decimal.Decimal`, never bare `float`. Use `ROUND_HALF_UP` for tax rounding.
- **Dataclasses**: Use `@dataclass` for structured data like `Transaction`, `TaxResult`, and `BatchResult`.
- **Imports**: Group imports in standard order -- stdlib, third-party, local -- separated by blank lines.
- **No `Any` types**: Avoid `typing.Any`. Use specific types or generics.
- **State codes**: Always use two-letter uppercase codes (e.g., `"TX"`, `"CA"`). Normalize with `.upper()` at entry points.

## Submitting Changes

1. **Fork** the repository and create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** in small, focused commits. Each commit should do one thing.

3. **Run the test suite** and confirm all tests pass:
   ```bash
   pytest tests/ -v
   ```

4. **Test with the sample dataset** to verify end-to-end behavior:
   ```bash
   python main.py calculate --file data/sample_transactions.csv
   ```

5. **Push** your branch and open a pull request against `main`.

6. In your PR description, explain:
   - What the change does
   - Why it is needed
   - How you tested it

## Updating Tax Rates

If you are updating tax rate data in `tax_engine/rates.py`:

- Cite the source (state revenue department URL or Tax Foundation publication)
- Include the effective date of the rate change
- Update both the base state rate and any affected local rates
- Run the rates test suite to confirm no regressions: `pytest tests/test_rates.py -v`

## Project Structure

```
tax_engine/
    __init__.py              # Package exports
    rates.py                 # 50-state + DC rate database with local overlays
    calculator.py            # Tax calculation engine (single, batch, use tax)
    compliance.py            # Nexus thresholds, filing deadlines, compliance alerts
    refund_analyzer.py       # Overpayment detection and refund claim generation
    report_generator.py      # Report formatting and CSV/JSON export
    cli.py                   # argparse CLI with rich output
tests/
    test_rates.py
    test_calculator.py
    test_compliance.py
    test_refund_analyzer.py
data/
    sample_transactions.csv  # 57 sample transactions across 25+ states
```

## Areas for Contribution

- Tax rate updates for new legislative sessions
- Additional local jurisdiction rates (currently covers 60+ major cities)
- Support for special tax districts (transit, tourism, stadium)
- Tax holiday detection and scheduling
- Integration with state e-filing APIs
- Marketplace facilitator rules
- International VAT/GST support
- Additional test coverage for edge cases and exemption combinations

## Questions

Open an issue if you have questions or want to discuss a feature before starting work.

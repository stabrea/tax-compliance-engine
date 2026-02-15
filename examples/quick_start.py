#!/usr/bin/env python3
"""
Quick Start Example
===================

Demonstrates basic usage of the TaxCalculator to compute sales tax
for a transaction in Texas (Houston) and print the result.

Usage:
    python examples/quick_start.py
"""

from datetime import date
from decimal import Decimal

from tax_engine.calculator import TaxCalculator, Transaction
from tax_engine.rates import TaxRateDatabase


def main() -> None:
    # Initialize the tax rate database and calculator
    db = TaxRateDatabase()
    calculator = TaxCalculator(db=db)

    # Create a sample transaction: $500 purchase in Houston, TX
    txn = Transaction(
        transaction_id="TXN-001",
        transaction_date=date.today(),
        amount=Decimal("500.00"),
        state="TX",
        city="Houston",
    )

    # Calculate tax
    result = calculator.calculate(txn)

    # Print the result
    print(f"Transaction:    {result.transaction_id}")
    print(f"State:          {result.state}")
    print(f"City:           {result.city}")
    print(f"Taxable Amount: ${result.taxable_amount:.2f}")
    print(f"State Tax:      ${result.state_tax:.2f}")
    print(f"Local Tax:      ${result.local_tax:.2f}")
    print(f"Total Tax:      ${result.tax_amount:.2f}")
    print(f"Effective Rate: {result.effective_rate:.2%}")
    print(f"Total w/ Tax:   ${result.total_with_tax:.2f}")

    if result.is_exempt:
        print(f"Exemption:      {result.exemption_reason}")

    if result.warnings:
        print(f"Warnings:       {', '.join(result.warnings)}")

    # Demonstrate an exempt transaction: grocery purchase in TX
    print("\n--- Exempt Transaction ---")
    grocery_txn = Transaction(
        transaction_id="TXN-002",
        transaction_date=date.today(),
        amount=Decimal("75.00"),
        state="TX",
        city="Austin",
        item_category="grocery",
    )

    grocery_result = calculator.calculate(grocery_txn)
    print(f"Transaction:    {grocery_result.transaction_id}")
    print(f"Item Category:  grocery")
    print(f"Exempt:         {grocery_result.is_exempt}")
    print(f"Reason:         {grocery_result.exemption_reason}")
    print(f"Tax:            ${grocery_result.tax_amount:.2f}")


if __name__ == "__main__":
    main()

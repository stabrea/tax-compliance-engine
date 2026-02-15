#!/usr/bin/env python3
"""
Tax Compliance Engine - Entry Point

A sales tax compliance automation tool for multi-state businesses.
Calculates tax liability, monitors nexus thresholds, identifies
refund opportunities, and generates compliance reports.

Usage:
    python main.py calculate --amount 500 --state TX --city Houston
    python main.py calculate --file data/sample_transactions.csv
    python main.py rates --state CA
    python main.py compliance --file data/sample_transactions.csv
    python main.py refund --file data/sample_transactions.csv --quick
    python main.py report --file data/sample_transactions.csv --export-json report.json
"""

from tax_engine.cli import main

if __name__ == "__main__":
    main()

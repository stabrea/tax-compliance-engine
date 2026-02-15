"""
Tax Compliance Engine
=====================

A sales tax compliance automation toolkit for multi-state transaction
processing, nexus analysis, refund identification, and filing management.

Modules:
    rates           - State and local sales tax rate database
    calculator      - Multi-jurisdiction tax calculation engine
    compliance      - Filing deadline tracking and nexus threshold monitoring
    refund_analyzer - Overpayment detection and refund filing preparation
    report_generator- Compliance reporting with CSV/JSON export
    cli             - Command-line interface
"""

__version__ = "1.0.0"
__author__ = "Taofik Bishi"

from tax_engine.rates import TaxRateDatabase
from tax_engine.calculator import TaxCalculator
from tax_engine.compliance import ComplianceChecker
from tax_engine.refund_analyzer import RefundAnalyzer
from tax_engine.report_generator import ReportGenerator

__all__ = [
    "TaxRateDatabase",
    "TaxCalculator",
    "ComplianceChecker",
    "RefundAnalyzer",
    "ReportGenerator",
]

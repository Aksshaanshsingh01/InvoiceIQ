"""
Tests for InvoiceIQ totals_parser.py

These tests verify:

    - Round off
    - Total amount
    - Received amount

for Purchase and Sale invoices.
"""

from pathlib import Path

from extraction.table_parser import parse_sections
from extraction.totals_parser import parse_totals


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SAMPLES_DIR = PROJECT_ROOT / "samples"

PURCHASE_PDF = SAMPLES_DIR / "Purchase Invoice 4.pdf"
SALE_PDF = SAMPLES_DIR / "Sale Invoice 4.pdf"


# ============================================================
# PURCHASE TOTALS TEST
# ============================================================

def test_purchase_totals():

    sections = parse_sections(
        PURCHASE_PDF
    )

    totals = parse_totals(
        sections.totals,
        "PURCHASE",
    )

    # --------------------------------------------------------
    # Round off
    # --------------------------------------------------------

    assert totals.round_off == 0.0

    # --------------------------------------------------------
    # Total amount
    # --------------------------------------------------------

    assert totals.total_amount == 76650.0

    # --------------------------------------------------------
    # Received amount
    # --------------------------------------------------------

    assert totals.received_amount == 0.0


# ============================================================
# SALE TOTALS TEST
# ============================================================

def test_sale_totals():

    sections = parse_sections(
        SALE_PDF
    )

    totals = parse_totals(
        sections.totals,
        "SALE",
    )

    # --------------------------------------------------------
    # Round off
    # --------------------------------------------------------

    assert totals.round_off == 0.50

    # --------------------------------------------------------
    # Total amount
    # --------------------------------------------------------

    assert totals.total_amount == 77963.0

    # --------------------------------------------------------
    # Received amount
    # --------------------------------------------------------

    assert totals.received_amount == 0.0

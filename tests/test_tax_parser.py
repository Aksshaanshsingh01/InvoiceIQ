"""
Tests for InvoiceIQ tax_parser.py

These tests verify tax-summary extraction for
Purchase and Sale invoices.
"""

from pathlib import Path

from extraction.table_parser import parse_sections
from extraction.tax_parser import parse_tax_summary


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SAMPLES_DIR = PROJECT_ROOT / "samples"

PURCHASE_PDF = SAMPLES_DIR / "Purchase Invoice 4.pdf"
SALE_PDF = SAMPLES_DIR / "Sale Invoice 4.pdf"


# ============================================================
# PURCHASE TAX TEST
# ============================================================

def test_purchase_tax_summary():

    sections = parse_sections(
        PURCHASE_PDF
    )

    summary = parse_tax_summary(
        sections.tax_summary,
        "PURCHASE",
    )

    # --------------------------------------------------------
    # Taxable value
    # --------------------------------------------------------

    assert summary.taxable_value == 73000.0

    # --------------------------------------------------------
    # Number of taxes
    # --------------------------------------------------------

    assert len(summary.taxes) == 2

    # --------------------------------------------------------
    # CGST
    # --------------------------------------------------------

    cgst = next(
        tax
        for tax in summary.taxes
        if tax.type == "CGST"
    )

    assert cgst.rate == 2.5

    assert cgst.amount == 1825.0

    # --------------------------------------------------------
    # SGST
    # --------------------------------------------------------

    sgst = next(
        tax
        for tax in summary.taxes
        if tax.type == "SGST"
    )

    assert sgst.rate == 2.5

    assert sgst.amount == 1825.0

    # --------------------------------------------------------
    # Total tax
    # --------------------------------------------------------

    assert summary.total_tax == 3650.0


# ============================================================
# SALE TAX TEST
# ============================================================

def test_sale_tax_summary():

    sections = parse_sections(
        SALE_PDF
    )

    summary = parse_tax_summary(
        sections.tax_summary,
        "SALE",
    )

    # --------------------------------------------------------
    # Taxable value
    # --------------------------------------------------------

    assert summary.taxable_value == 74250.0

    # --------------------------------------------------------
    # Number of taxes
    # --------------------------------------------------------

    assert len(summary.taxes) == 1

    # --------------------------------------------------------
    # IGST
    # --------------------------------------------------------

    igst = summary.taxes[0]

    assert igst.type == "IGST"

    assert igst.rate == 5.0

    assert igst.amount == 3712.50

    # --------------------------------------------------------
    # Total tax
    # --------------------------------------------------------

    assert summary.total_tax == 3712.50
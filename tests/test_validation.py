"""
Integration tests for the complete InvoiceIQ pipeline.

These tests verify:

    PDF
      ↓
    invoice_extractor
      ↓
    Invoice object
      ↓
    validators
      ↓
    VALID

The tests use real invoice PDFs rather than synthetic data.
"""

from pathlib import Path

from extraction.invoice_extractor import extract_invoice
from extraction.validators import validate_invoice


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

SAMPLES_DIR = PROJECT_ROOT / "samples"


PURCHASE_04 = (
    SAMPLES_DIR / "Purchase Invoice 4.pdf"
)

SALE_04 = (
    SAMPLES_DIR / "Sale Invoice 4.pdf"
)

PURCHASE_03 = (
    SAMPLES_DIR / "Purchase Invoice 03.pdf"
)

SALE_03 = (
    SAMPLES_DIR / "Sale Invoice 03.pdf"
)


# ============================================================
# HELPER
# ============================================================


def validate_pdf(pdf_path: Path):
    """
    Extract and validate one invoice.
    """

    invoice = extract_invoice(pdf_path)

    result = validate_invoice(invoice)

    return invoice, result


# ============================================================
# PURCHASE INVOICE 4
# ============================================================


def test_purchase_invoice_04_validation():

    invoice, result = validate_pdf(
        PURCHASE_04
    )

    assert result.is_valid, (
        f"Purchase Invoice 4 failed validation:\n"
        f"{result.errors}"
    )

    assert invoice.total_amount == 76650.0


# ============================================================
# SALE INVOICE 4
# ============================================================


def test_sale_invoice_04_validation():

    invoice, result = validate_pdf(
        SALE_04
    )

    assert result.is_valid, (
        f"Sale Invoice 4 failed validation:\n"
        f"{result.errors}"
    )

    assert invoice.total_amount == 77963.0


# ============================================================
# PURCHASE INVOICE 03
# ============================================================


def test_purchase_invoice_03_validation():

    invoice, result = validate_pdf(
        PURCHASE_03
    )

    assert result.is_valid, (
        f"Purchase Invoice 03 failed validation:\n"
        f"{result.errors}"
    )

    # --------------------------------------------------------
    # Multi-item verification
    # --------------------------------------------------------

    assert len(invoice.items) == 2

    # --------------------------------------------------------
    # Financial verification
    # --------------------------------------------------------

    assert invoice.total_tax == 7530.10

    # The invoice total is ₹0.10 lower than the
    # calculated taxable value + tax.
    assert invoice.round_off == -0.10

    assert invoice.total_amount == 158132.0


# ============================================================
# SALE INVOICE 03
# ============================================================


def test_sale_invoice_03_validation():

    invoice, result = validate_pdf(
        SALE_03
    )

    assert result.is_valid, (
        f"Sale Invoice 03 failed validation:\n"
        f"{result.errors}"
    )

    # --------------------------------------------------------
    # Multi-item verification
    # --------------------------------------------------------

    assert len(invoice.items) == 2

    # --------------------------------------------------------
    # Financial verification
    # --------------------------------------------------------

    assert invoice.total_tax == 7709.85

    assert invoice.round_off == 0.15

    assert invoice.total_amount == 161907.0


# ============================================================
# FILE EXISTENCE
# ============================================================


def test_all_real_invoices_exist():

    invoice_files = [
        PURCHASE_04,
        SALE_04,
        PURCHASE_03,
        SALE_03,
    ]

    for pdf_file in invoice_files:

        assert pdf_file.exists(), (
            f"Invoice PDF not found: {pdf_file}"
        )

"""
Tests for InvoiceIQ tax analytics.
"""

from pathlib import Path

from analytics.tax import get_tax_metrics
from database.db import initialize_database, insert_validated_invoice
from extraction.invoice_extractor import extract_invoice


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PURCHASE_03 = (
    PROJECT_ROOT
    / "samples"
    / "Purchase Invoice 03.pdf"
)

SALE_03 = (
    PROJECT_ROOT
    / "samples"
    / "Sale Invoice 03.pdf"
)


def build_test_database(database):
    """Create a database containing two invoices."""

    initialize_database(database)

    purchase = extract_invoice(PURCHASE_03)
    sale = extract_invoice(SALE_03)

    insert_validated_invoice(
        purchase,
        "VALID",
        database,
    )

    insert_validated_invoice(
        sale,
        "VALID",
        database,
    )


def test_get_tax_metrics(tmp_path):
    database = tmp_path / "test.db"

    build_test_database(database)

    metrics = get_tax_metrics(database)

    assert metrics == {
        "cgst": 3765.05,
        "sgst": 3765.05,
        "igst": 7709.85,
        "total_tax": 15239.95,
    }
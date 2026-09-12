"""
Tests for InvoiceIQ party analytics.
"""

from pathlib import Path

from analytics.parties import (
    get_supplier_metrics,
    get_customer_metrics,
    get_party_metrics,
)

from database.db import (
    initialize_database,
    insert_validated_invoice,
)

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


def test_get_supplier_metrics(tmp_path):
    database = tmp_path / "test.db"

    build_test_database(database)

    metrics = get_supplier_metrics(database)

    assert metrics == {
        "supplier_count": 1,
        "suppliers": [
            {
                "supplier": "KGSDF INDUSTRIES PVT LTD",
                "invoice_count": 1,
                "total_amount": 158132.0,
            }
        ],
    }


def test_get_customer_metrics(tmp_path):
    database = tmp_path / "test.db"

    build_test_database(database)

    metrics = get_customer_metrics(database)

    assert metrics == {
        "customer_count": 1,
        "customers": [
            {
                "customer": "IRAA GLOBAL (OPC) PRIVATE LIMITED",
                "invoice_count": 1,
                "total_amount": 161907.0,
            }
        ],
    }


def test_get_party_metrics(tmp_path):
    database = tmp_path / "test.db"

    build_test_database(database)

    metrics = get_party_metrics(database)

    assert metrics["suppliers"]["supplier_count"] == 1
    assert metrics["customers"]["customer_count"] == 1

    assert (
        metrics["suppliers"]["suppliers"][0]["total_amount"]
        == 158132.0
    )

    assert (
        metrics["customers"]["customers"][0]["total_amount"]
        == 161907.0
    )

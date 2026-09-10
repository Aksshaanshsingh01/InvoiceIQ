from analytics.dashboard import get_dashboard_metrics

from database.db import initialize_database, insert_validated_invoice
from extraction.invoice_extractor import extract_invoice

from pathlib import Path


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


def test_dashboard_metrics(tmp_path):
    database = tmp_path / "test.db"

    build_test_database(database)

    metrics = get_dashboard_metrics(database)

    assert metrics == {
        "financial": {
            "total_sales": 161907.0,
            "total_purchases": 158132.0,
            "total_tax": 15239.95,
            "outstanding_amount": 158132.0,
            "paid_invoice_count": 0,
            "unpaid_invoice_count": 1,
        },
        "invoices": {
            "total_invoice_count": 2,
            "sales_invoice_count": 1,
            "purchase_invoice_count": 1,
            "paid_invoice_count": 0,
            "unpaid_invoice_count": 1,
        },
        "tax": {
            "cgst": 3765.05,
            "sgst": 3765.05,
            "igst": 7709.85,
            "total_tax": 15239.95,
        },
        "parties": {
            "suppliers": {
                "supplier_count": 1,
                "suppliers": [
                    {
                        "supplier": "KGSDF INDUSTRIES PVT LTD",
                        "invoice_count": 1,
                        "total_amount": 158132.0,
                    }
                ],
            },
            "customers": {
                "customer_count": 1,
                "customers": [
                    {
                        "customer": "IRAA GLOBAL (OPC) PRIVATE LIMITED",
                        "invoice_count": 1,
                        "total_amount": 161907.0,
                    }
                ],
            },
        },
    }
"""
Tests for InvoiceIQ database queries.
"""

from pathlib import Path

from extraction.invoice_extractor import (
    extract_invoice,
)

from database.db import (
    initialize_database,
    insert_validated_invoice,
)

from database.queries import (
    get_invoice_by_id,
    get_invoice_by_number,
    get_invoices_by_seller,
    get_invoices_by_buyer,
    get_invoices_by_type,
    get_invoices_by_date_range,
    get_unpaid_invoices,
    get_fully_paid_invoices,
    search_items,
    get_items_by_hsn,
    get_total_sales,
    get_total_purchases,
    get_total_tax,
    get_tax_summary,
    get_seller_summary,
    get_financial_summary,
)


PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

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


def build_test_database(
    database,
):
    """Create a database containing two invoices."""

    initialize_database(
        database
    )

    purchase = extract_invoice(
        PURCHASE_03
    )

    sale = extract_invoice(
        SALE_03
    )

    purchase_id = insert_validated_invoice(
        purchase,
        "VALID",
        database,
    )

    sale_id = insert_validated_invoice(
        sale,
        "VALID",
        database,
    )

    return purchase_id, sale_id


# ============================================================
# Basic retrieval
# ============================================================


def test_get_invoice_by_id(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    purchase_id, _ = build_test_database(
        database
    )

    invoice = get_invoice_by_id(
        purchase_id,
        database,
    )

    assert invoice is not None

    assert (
        invoice["invoice_number"]
        == "KGSDF/YGEPL/26-27/03"
    )


def test_get_invoice_by_number(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    build_test_database(
        database
    )

    invoices = get_invoice_by_number(
        "YGEPL/26-27/4",
        database,
    )

    assert len(invoices) == 1

    assert (
        invoices[0]["invoice_type"]
        == "SALE"
    )


# ============================================================
# Seller / Buyer
# ============================================================


def test_get_invoices_by_seller(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    build_test_database(
        database
    )

    invoices = get_invoices_by_seller(
        "Yara Green Energy Pvt Ltd",
        database,
    )

    assert len(invoices) == 1

    assert (
        invoices[0]["invoice_type"]
        == "SALE"
    )


def test_get_invoices_by_buyer(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    build_test_database(
        database
    )

    invoices = get_invoices_by_buyer(
        "Yara Green Energy Private Limited",
        database,
    )

    assert len(invoices) == 1

    assert (
        invoices[0]["invoice_type"]
        == "PURCHASE"
    )


# ============================================================
# Type
# ============================================================


def test_get_invoices_by_type(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    build_test_database(
        database
    )

    purchases = get_invoices_by_type(
        "purchase",
        database,
    )

    sales = get_invoices_by_type(
        "sale",
        database,
    )

    assert len(purchases) == 1

    assert len(sales) == 1


# ============================================================
# Date
# ============================================================


def test_get_invoices_by_date_range(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    build_test_database(
        database
    )

    invoices = get_invoices_by_date_range(
        "24/08/2026",
        "24/08/2026",
        database,
    )

    assert len(invoices) == 2


# ============================================================
# Payment
# ============================================================


def test_get_unpaid_invoices(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    build_test_database(
        database
    )

    invoices = get_unpaid_invoices(
        database
    )

    assert len(invoices) == 1


def test_get_fully_paid_invoices(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    build_test_database(
        database
    )

    invoices = get_fully_paid_invoices(
        database
    )

    assert len(invoices) == 0


# ============================================================
# Item Search
# ============================================================


def test_search_items(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    build_test_database(
        database
    )

    items = search_items(
        "sawdust",
        database,
    )

    assert len(items) == 4


def test_get_items_by_hsn(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    build_test_database(
        database
    )

    items = get_items_by_hsn(
        "44013100",
        database,
    )

    assert len(items) == 4


# ============================================================
# Financial aggregations
# ============================================================


def test_total_sales(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    build_test_database(
        database
    )

    assert (
        get_total_sales(database)
        == 161907.0
    )


def test_total_purchases(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    build_test_database(
        database
    )

    assert (
        get_total_purchases(database)
        == 158132.0
    )


def test_total_tax(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    build_test_database(
        database
    )

    assert (
        get_total_tax(database)
        == 15239.95
    )


# ============================================================
# Tax summary
# ============================================================


def test_tax_summary(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    build_test_database(
        database
    )

    summary = get_tax_summary(
        database
    )

    summary_by_type = {
        row["tax_type"]: row["total_amount"]
        for row in summary
    }

    assert (
        summary_by_type["CGST"]
        == 3765.05
    )

    assert (
        summary_by_type["SGST"]
        == 3765.05
    )

    assert (
        summary_by_type["IGST"]
        == 7709.85
    )


# ============================================================
# Seller summary
# ============================================================


def test_seller_summary(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    build_test_database(
        database
    )

    summary = get_seller_summary(
        database
    )

    assert len(summary) == 2


# ============================================================
# Financial summary
# ============================================================


def test_financial_summary(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    build_test_database(
        database
    )

    summary = get_financial_summary(
        database
    )

    assert summary == {
        "sales": 161907.0,
        "purchases": 158132.0,
        "tax": 15239.95,
    }

"""
Tests for the InvoiceIQ SQLite database layer.
"""

import sqlite3

from extraction.invoice_extractor import (
    extract_invoice,
)

from database.db import (
    initialize_database,
    insert_validated_invoice,
    invoice_exists,
    get_all_invoices,
    get_invoice_items,
    get_invoice_taxes,
    delete_invoice,
    get_database_summary,
)


# ============================================================
# Test database initialization
# ============================================================


def test_database_initialization(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    initialize_database(
        database
    )

    summary = get_database_summary(
        database
    )

    assert summary == {
        "invoices": 0,
        "items": 0,
        "taxes": 0,
    }


# ============================================================
# Test invoice insertion
# ============================================================


def test_insert_multi_item_invoice(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    initialize_database(
        database
    )

    invoice = extract_invoice(
        "samples/Purchase Invoice 03.pdf"
    )

    invoice_id = insert_validated_invoice(
        invoice,
        "VALID",
        database,
    )

    assert invoice_id > 0

    # --------------------------------------------------------
    # Invoice
    # --------------------------------------------------------

    invoices = get_all_invoices(
        database
    )

    assert len(invoices) == 1

    stored_invoice = invoices[0]

    assert (
        stored_invoice["invoice_number"]
        == "KGSDF/YGEPL/26-27/03"
    )

    assert (
        stored_invoice["invoice_type"]
        == "PURCHASE"
    )

    assert (
        stored_invoice["total_amount"]
        == 158132.0
    )

    assert (
        stored_invoice["validation_status"]
        == "VALID"
    )

    # --------------------------------------------------------
    # Items
    # --------------------------------------------------------

    items = get_invoice_items(
        invoice_id,
        database,
    )

    assert len(items) == 2

    assert (
        items[0]["material_name"]
        == "SAW DUST PELLETS PREMIUM"
    )

    assert (
        items[1]["material_name"]
        == "SAW DUST BRIQUETTE PREMIUM"
    )

    assert (
        items[0]["quantity"]
        == 2.63
    )

    assert (
        items[1]["quantity"]
        == 11.75
    )

    # --------------------------------------------------------
    # Taxes
    # --------------------------------------------------------

    taxes = get_invoice_taxes(
        invoice_id,
        database,
    )

    assert len(taxes) == 2

    assert (
        taxes[0]["tax_type"]
        == "CGST"
    )

    assert (
        taxes[1]["tax_type"]
        == "SGST"
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    summary = get_database_summary(
        database
    )

    assert summary == {
        "invoices": 1,
        "items": 2,
        "taxes": 2,
    }


# ============================================================
# Test duplicate protection
# ============================================================


def test_duplicate_invoice_protection(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    initialize_database(
        database
    )

    invoice = extract_invoice(
        "samples/Purchase Invoice 03.pdf"
    )

    insert_validated_invoice(
        invoice,
        "VALID",
        database,
    )

    assert invoice_exists(
        invoice.invoice_number,
        invoice.seller_gstin,
        database,
    )

    # --------------------------------------------------------
    # Duplicate insert should fail
    # --------------------------------------------------------

    try:

        insert_validated_invoice(
            invoice,
            "VALID",
            database,
        )

    except sqlite3.IntegrityError:

        pass

    else:

        raise AssertionError(
            "Duplicate invoice was inserted."
        )


# ============================================================
# Test delete + cascade
# ============================================================


def test_delete_invoice_cascade(
    tmp_path,
):

    database = (
        tmp_path / "test.db"
    )

    initialize_database(
        database
    )

    invoice = extract_invoice(
        "samples/Purchase Invoice 03.pdf"
    )

    invoice_id = insert_validated_invoice(
        invoice,
        "VALID",
        database,
    )

    summary = get_database_summary(
        database
    )

    assert summary == {
        "invoices": 1,
        "items": 2,
        "taxes": 2,
    }

    deleted = delete_invoice(
        invoice_id,
        database,
    )

    assert deleted is True

    summary = get_database_summary(
        database
    )

    assert summary == {
        "invoices": 0,
        "items": 0,
        "taxes": 0,
    }
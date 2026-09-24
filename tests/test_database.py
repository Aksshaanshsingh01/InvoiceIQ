"""
Tests for the InvoiceIQ SQLite database layer.
"""

import pytest

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
    record_payment,
    get_payment_history,
    delete_payment,
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

    assert isinstance(invoice_id, str)
    assert invoice_id

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
        invoice.invoice_type,
        invoice.invoice_date,
        invoice.seller_gstin,
        invoice.buyer_gstin,
        database,
    )

    # --------------------------------------------------------
    # Duplicate insert should fail
    # --------------------------------------------------------

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        insert_validated_invoice(
            invoice,
            "VALID",
            database,
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

# ============================================================
# Test payment recording
# ============================================================


def test_record_payment():
    """
    Test recording multiple payments against a Firestore invoice.
    """

    database = "firestore"

    invoice = extract_invoice(
        "samples/Purchase Invoice 03.pdf"
    )

    # Use a unique invoice number so the test does not
    # collide with an existing Firestore document.
    original_invoice_number = invoice.invoice_number

    invoice.invoice_number = (
        f"{original_invoice_number}-TEST-PAYMENT"
    )

    try:

        invoice_id = insert_validated_invoice(
            invoice,
            "VALID",
            database,
        )

        # ----------------------------------------------------
        # First payment
        # ----------------------------------------------------

        updated = record_payment(
            invoice_id,
            10000,
            database,
        )

        assert (
            updated["received_amount"]
            == 10000
        )

        assert (
            updated["payment_status"]
            == "PARTIALLY_PAID"
        )

        assert (
            updated["paid_at"]
            is None
        )

        # ----------------------------------------------------
        # Verify payment transaction exists
        # ----------------------------------------------------

        payments = get_payment_history(
            invoice_id,
            database,
        )

        assert len(payments) == 1

        assert (
            payments[0]["payment_amount"]
            == 10000
        )

        # ----------------------------------------------------
        # Second payment - complete invoice
        # ----------------------------------------------------

        remaining_amount = (
            invoice.total_amount - 10000
        )

        updated = record_payment(
            invoice_id,
            remaining_amount,
            database,
        )

        assert (
            updated["received_amount"]
            == invoice.total_amount
        )

        assert (
            updated["payment_status"]
            == "PAID"
        )

        assert (
            updated["paid_at"]
            is not None
        )

        # ----------------------------------------------------
        # Verify both transactions exist
        # ----------------------------------------------------

        payments = get_payment_history(
            invoice_id,
            database,
        )

        assert len(payments) == 2

    finally:

        # ----------------------------------------------------
        # Cleanup payment transactions
        # ----------------------------------------------------

        payments = get_payment_history(
            invoice_id,
            database,
        )

        for payment in payments:
            delete_payment(
                invoice_id,
                payment["id"],
                database,
            )

        # ----------------------------------------------------
        # Cleanup invoice
        # ----------------------------------------------------

        delete_invoice(
            invoice_id,
            database,
        )


# ============================================================
# Test payment cannot exceed outstanding amount
# ============================================================


def test_record_payment_cannot_exceed_outstanding():

    """
    Verify that a payment larger than the outstanding
    invoice amount is rejected.
    """

    database = "firestore"

    invoice = extract_invoice(
        "samples/Purchase Invoice 03.pdf"
    )

    original_invoice_number = invoice.invoice_number

    invoice.invoice_number = (
        f"{original_invoice_number}-TEST-OVERPAY"
    )

    try:

        invoice_id = insert_validated_invoice(
            invoice,
            "VALID",
            database,
        )

        # ----------------------------------------------------
        # Record initial payment
        # ----------------------------------------------------

        record_payment(
            invoice_id,
            10000,
            database,
        )

        outstanding = (
            invoice.total_amount - 10000
        )

        # ----------------------------------------------------
        # Attempt to overpay
        # ----------------------------------------------------

        with pytest.raises(
            ValueError,
            match="outstanding amount",
        ):

            record_payment(
                invoice_id,
                outstanding + 1,
                database,
            )

    finally:

        # ----------------------------------------------------
        # Cleanup payment transactions
        # ----------------------------------------------------

        payments = get_payment_history(
            invoice_id,
            database,
        )

        for payment in payments:
            delete_payment(
                invoice_id,
                payment["id"],
                database,
            )

        # ----------------------------------------------------
        # Cleanup invoice
        # ----------------------------------------------------

        delete_invoice(
            invoice_id,
            database,
        )
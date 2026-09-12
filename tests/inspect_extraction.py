"""
Tests for the InvoiceIQ extraction engine.

These tests verify that the information extracted from
our sample Purchase and Sale invoices is correct.
"""

from pathlib import Path

from extraction.invoice_extractor import extract_invoice


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

SAMPLES_DIR = PROJECT_ROOT / "samples"

PURCHASE_PDF = (
    SAMPLES_DIR / "Purchase Invoice 4.pdf"
)

SALE_PDF = (
    SAMPLES_DIR / "Sale Invoice 4.pdf"
)


# ============================================================
# Purchase Invoice
# ============================================================

def test_purchase_invoice():

    invoice = extract_invoice(
        PURCHASE_PDF
    )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    assert invoice.invoice_type == "PURCHASE"

    assert invoice.invoice_number == (
        "KGSDF/YGEPL/26-27/04"
    )

    assert invoice.invoice_date == (
        "24/08/2026"
    )

    assert invoice.due_date == (
        "24/08/2026"
    )

    # --------------------------------------------------------
    # Parties
    # --------------------------------------------------------

    assert invoice.seller == (
        "KGSDF INDUSTRIES PVT LTD"
    )

    assert invoice.buyer == (
        "Yara Green Energy Private Limited"
    )

    # --------------------------------------------------------
    # GSTIN
    # --------------------------------------------------------

    assert invoice.seller_gstin == (
        "09AAKCK2797D1Z6"
    )

    assert invoice.buyer_gstin == (
        "09AABCY6613M1ZV"
    )

    # --------------------------------------------------------
    # Items
    # --------------------------------------------------------

    assert len(invoice.items) == 1

    item = invoice.items[0]

    assert item.material_name == (
        "SAW DUST PELLETS PREMIUM"
    )

    assert item.hsn == "44013100"

    assert item.quantity == 5.0

    assert item.unit == "TON"

    assert item.rate == 14600.0

    assert item.taxable_value == 73000.0

    # Item should NOT contain invoice-level taxes.
    assert not hasattr(item, "taxes")

    # --------------------------------------------------------
    # Invoice Taxes
    # --------------------------------------------------------

    assert len(invoice.taxes) == 2

    cgst = next(
        tax
        for tax in invoice.taxes
        if tax.type == "CGST"
    )

    sgst = next(
        tax
        for tax in invoice.taxes
        if tax.type == "SGST"
    )

    assert cgst.rate == 2.5
    assert cgst.amount == 1825.0

    assert sgst.rate == 2.5
    assert sgst.amount == 1825.0

    # --------------------------------------------------------
    # Totals
    # --------------------------------------------------------

    assert invoice.total_tax == 3650.0

    assert invoice.round_off == 0.0

    assert invoice.total_amount == 76650.0


# ============================================================
# Sale Invoice
# ============================================================

def test_sale_invoice():

    invoice = extract_invoice(
        SALE_PDF
    )

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    assert invoice.invoice_type == "SALE"

    assert invoice.invoice_number == (
        "YGEPL/26-27/4"
    )

    assert invoice.invoice_date == (
        "25/08/2026"
    )

    assert invoice.due_date == (
        "14/09/2026"
    )

    # --------------------------------------------------------
    # Parties
    # --------------------------------------------------------

    assert invoice.seller == (
        "Yara Green Energy Pvt Ltd"
    )

    assert invoice.buyer == (
        "IRAA GLOBAL (OPC) PRIVATE LIMITED"
    )

    # --------------------------------------------------------
    # GSTIN
    # --------------------------------------------------------

    assert invoice.seller_gstin == (
        "09AABCY6613M1ZV"
    )

    assert invoice.buyer_gstin == (
        "07AAICI6650D1ZM"
    )

    # --------------------------------------------------------
    # Items
    # --------------------------------------------------------

    assert len(invoice.items) == 1

    item = invoice.items[0]

    assert item.material_name == (
        "Sawdust Premium Pellets"
    )

    assert item.hsn == "44013100"

    assert item.quantity == 5.0

    assert item.unit == "TON"

    assert item.rate == 14850.0

    assert item.taxable_value == 74250.0

    assert not hasattr(item, "taxes")

    # --------------------------------------------------------
    # Invoice Taxes
    # --------------------------------------------------------

    assert len(invoice.taxes) == 1

    igst = invoice.taxes[0]

    assert igst.type == "IGST"

    assert igst.rate == 5.0

    assert igst.amount == 3712.50

    # --------------------------------------------------------
    # Totals
    # --------------------------------------------------------

    assert invoice.total_tax == 3712.50

    assert invoice.round_off == 0.50

    assert invoice.total_amount == 77963.0


# ============================================================
# File Existence
# ============================================================

def test_sample_files_exist():

    assert PURCHASE_PDF.exists(), (
        f"Purchase PDF not found: "
        f"{PURCHASE_PDF}"
    )

    assert SALE_PDF.exists(), (
        f"Sale PDF not found: "
        f"{SALE_PDF}"
    )

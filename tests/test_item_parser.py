"""
Tests for InvoiceIQ item_parser.py

These tests verify that item-level information is correctly
extracted from Purchase and Sale invoices.

They also verify multi-item extraction independently from
the PDF layer.
"""

from pathlib import Path
from types import SimpleNamespace

from extraction.item_parser import (
    parse_items,
)
from extraction.table_parser import (
    TableSection,
    parse_sections,
)


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SAMPLES_DIR = PROJECT_ROOT / "samples"

PURCHASE_PDF = (
    SAMPLES_DIR
    / "Purchase Invoice 4.pdf"
)

SALE_PDF = (
    SAMPLES_DIR
    / "Sale Invoice 4.pdf"
)


# ============================================================
# PURCHASE ITEM TEST
# ============================================================

def test_purchase_items():

    sections = parse_sections(
        PURCHASE_PDF
    )

    items = parse_items(
        sections.item_table
    )

    assert len(items) == 1

    item = items[0]

    assert item.material_name == (
        "SAW DUST PELLETS PREMIUM"
    )

    assert item.hsn == "44013100"

    assert item.quantity == 5.0

    assert item.unit == "TON"

    assert item.rate == 14600.0

    assert item.tax_rate == 5.0

    assert item.tax_amount == 3650.0

    assert item.amount == 76650.0


# ============================================================
# SALE ITEM TEST
# ============================================================

def test_sale_items():

    sections = parse_sections(
        SALE_PDF
    )

    items = parse_items(
        sections.item_table
    )

    assert len(items) == 1

    item = items[0]

    assert item.material_name == (
        "Sawdust Premium Pellets"
    )

    assert item.hsn == "44013100"

    assert item.quantity == 5.0

    assert item.unit == "TON"

    assert item.rate == 14850.0

    assert item.tax_rate == 5.0

    assert item.tax_amount == 3712.50

    assert item.amount == 77962.50


# ============================================================
# MULTI-ITEM TEST
# ============================================================

def test_multi_item_extraction():

    """
    Verify that item_parser.py can correctly extract
    multiple consecutive item rows.

    This test intentionally bypasses PDF extraction.

    Why?

    We want to test the item parser itself independently
    from table_parser.py and PyMuPDF.

    The input below represents the flattened line structure
    that table_parser.py provides to item_parser.py.
    """

    section = SimpleNamespace(
        lines=[
            # ------------------------------------------------
            # Headers
            # ------------------------------------------------

            "S.NO.",
            "ITEMS",
            "HSN",
            "QTY.",
            "RATE",
            "TAX",
            "AMOUNT",

            # ------------------------------------------------
            # Item 1
            # ------------------------------------------------

            "1",
            "Sawdust Premium Pellets",
            "44013100",
            "5 TON",
            "14,850",
            "3,712.5",
            "(5%)",
            "77,962.5",

            # ------------------------------------------------
            # Item 2
            # ------------------------------------------------

            "2",
            "Wood Pellets Premium",
            "44013100",
            "8 TON",
            "13,500",
            "5,400",
            "(5%)",
            "113,400",

            # ------------------------------------------------
            # Item 3
            # ------------------------------------------------

            "3",
            "Biomass Fuel Pellets",
            "44013100",
            "3 TON",
            "12,900",
            "1,935",
            "(5%)",
            "40,635",
        ],
    )

    items = parse_items(
        section
    )

    # --------------------------------------------------------
    # Number of items
    # --------------------------------------------------------

    assert len(items) == 3

    # ========================================================
    # ITEM 1
    # ========================================================

    item = items[0]

    assert item.material_name == (
        "Sawdust Premium Pellets"
    )

    assert item.hsn == "44013100"

    assert item.quantity == 5.0

    assert item.unit == "TON"

    assert item.rate == 14850.0

    assert item.tax_rate == 5.0

    assert item.tax_amount == 3712.50

    assert item.amount == 77962.50

    # ========================================================
    # ITEM 2
    # ========================================================

    item = items[1]

    assert item.material_name == (
        "Wood Pellets Premium"
    )

    assert item.hsn == "44013100"

    assert item.quantity == 8.0

    assert item.unit == "TON"

    assert item.rate == 13500.0

    assert item.tax_rate == 5.0

    assert item.tax_amount == 5400.0

    assert item.amount == 113400.0

    # ========================================================
    # ITEM 3
    # ========================================================

    item = items[2]

    assert item.material_name == (
        "Biomass Fuel Pellets"
    )

    assert item.hsn == "44013100"

    assert item.quantity == 3.0

    assert item.unit == "TON"

    assert item.rate == 12900.0

    assert item.tax_rate == 5.0

    assert item.tax_amount == 1935.0

    assert item.amount == 40635.0

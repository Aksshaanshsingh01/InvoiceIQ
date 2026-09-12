"""
Tests for the InvoiceIQ JSON exporter.
"""

from pathlib import Path
import json

from extraction.invoice_extractor import extract_invoice
from extraction.exporter import (
    invoice_to_export_dict,
    export_invoice_json,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

SAMPLES_DIR = PROJECT_ROOT / "samples"


PURCHASE_03 = (
    SAMPLES_DIR / "Purchase Invoice 03.pdf"
)


# ============================================================
# Invoice -> Export Dictionary
# ============================================================


def test_invoice_to_export_dict():

    invoice = extract_invoice(
        PURCHASE_03
    )

    data = invoice_to_export_dict(
        invoice
    )

    # --------------------------------------------------------
    # Basic structure
    # --------------------------------------------------------

    assert isinstance(data, dict)

    assert data["invoice_type"] == "PURCHASE"

    assert (
        data["invoice_number"]
        == "KGSDF/YGEPL/26-27/03"
    )

    # --------------------------------------------------------
    # Items
    # --------------------------------------------------------

    assert len(data["items"]) == 2

    assert (
        data["items"][0]["material_name"]
        == "SAW DUST PELLETS PREMIUM"
    )

    assert (
        data["items"][1]["material_name"]
        == "SAW DUST BRIQUETTE PREMIUM"
    )

    # --------------------------------------------------------
    # Taxes
    # --------------------------------------------------------

    assert len(data["taxes"]) == 2

    # --------------------------------------------------------
    # Totals
    # --------------------------------------------------------

    assert data["total_tax"] == 7530.10

    assert data["round_off"] == -0.10

    assert data["total_amount"] == 158132.0

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    assert "validation" in data

    assert data["validation"]["status"] == "VALID"

    assert data["validation"]["is_valid"] is True

    assert data["validation"]["errors"] == []


# ============================================================
# JSON File Export
# ============================================================


def test_export_invoice_json(tmp_path):

    invoice = extract_invoice(
        PURCHASE_03
    )

    output_file = (
        tmp_path / "invoice.json"
    )

    result = export_invoice_json(
        invoice,
        output_file,
    )

    # --------------------------------------------------------
    # File exists
    # --------------------------------------------------------

    assert result.exists()

    assert result == output_file

    # --------------------------------------------------------
    # File contains valid JSON
    # --------------------------------------------------------

    with output_file.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    # --------------------------------------------------------
    # Verify exported values
    # --------------------------------------------------------

    assert (
        data["invoice_number"]
        == "KGSDF/YGEPL/26-27/03"
    )

    assert len(data["items"]) == 2

    assert data["total_amount"] == 158132.0

    assert data["validation"]["is_valid"] is True

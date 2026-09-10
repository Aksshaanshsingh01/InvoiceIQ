from pathlib import Path

from database.db import initialize_database
from database.queries import get_invoice_by_id
from extraction.invoice_extractor import extract_invoice
from services.invoice_service import process_invoice


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PURCHASE_03 = (
    PROJECT_ROOT
    / "samples"
    / "Purchase Invoice 03.pdf"
)


def test_process_invoice_success(tmp_path):
    database = tmp_path / "test.db"

    initialize_database(database)

    result = process_invoice(
        PURCHASE_03,
        database,
    )

    assert result["success"] is True
    assert result["status"] == "PROCESSED"
    assert result["invoice_number"] == (
        "KGSDF/YGEPL/26-27/03"
    )
    assert result["validation_status"] == "VALID"

    invoice_id = result["invoice_id"]

    invoice = get_invoice_by_id(
        invoice_id,
        database,
    )

    assert invoice is not None

    assert invoice["invoice_number"] == (
        "KGSDF/YGEPL/26-27/03"
    )

    assert invoice["total_amount"] == 158132.0


def test_process_invoice_duplicate(tmp_path):
    database = tmp_path / "test.db"

    initialize_database(database)

    first_result = process_invoice(
        PURCHASE_03,
        database,
    )

    assert first_result["success"] is True

    second_result = process_invoice(
        PURCHASE_03,
        database,
    )

    assert second_result["success"] is False
    assert second_result["status"] == "DUPLICATE"

    assert second_result["invoice_number"] == (
        "KGSDF/YGEPL/26-27/03"
    )

    assert (
        second_result["existing_invoice_id"]
        == first_result["invoice_id"]
    )


def test_process_invoice_validation_failure(
    tmp_path,
    monkeypatch,
):
    database = tmp_path / "test.db"

    initialize_database(database)

    invoice = extract_invoice(
        PURCHASE_03
    )

    # Make the extracted invoice invalid.
    # Quantity × rate will no longer match
    # the extracted taxable value.
    invoice.items[0].quantity = 999999.0

    def mock_extract_invoice(pdf_path):
        return invoice

    monkeypatch.setattr(
        "services.invoice_service.extract_invoice",
        mock_extract_invoice,
    )

    result = process_invoice(
        PURCHASE_03,
        database,
    )

    assert result["success"] is False
    assert result["status"] == (
        "VALIDATION_FAILED"
    )

    assert result["invoice_number"] == (
        "KGSDF/YGEPL/26-27/03"
    )

    assert len(result["errors"]) > 0

    assert result["warnings"] == []

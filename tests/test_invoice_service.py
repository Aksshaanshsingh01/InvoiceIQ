from pathlib import Path

from extraction.invoice_extractor import extract_invoice
from services.invoice_service import process_invoice


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PURCHASE_03 = (
    PROJECT_ROOT
    / "samples"
    / "Purchase Invoice 03.pdf"
)


def test_process_invoice_success(monkeypatch):
    captured_invoice = {}

    def mock_insert_validated_invoice(
        invoice,
        validation_status,
        database_path,
    ):
        captured_invoice["invoice"] = invoice
        captured_invoice["validation_status"] = validation_status
        return "test-invoice-id"

    monkeypatch.setattr(
        "services.invoice_service.insert_validated_invoice",
        mock_insert_validated_invoice,
    )

    monkeypatch.setattr(
        "services.invoice_service.invoice_exists",
        lambda **kwargs: False,
    )

    result = process_invoice(
        PURCHASE_03,
        source_filename="Purchase Invoice 03.pdf",
    )

    assert result["success"] is True
    assert result["status"] == "PROCESSED"
    assert result["invoice_number"] == (
        "KGSDF/YGEPL/26-27/03"
    )
    assert result["validation_status"] == "VALID"
    assert result["invoice_id"] == "test-invoice-id"

    invoice = captured_invoice["invoice"]

    assert invoice.invoice_number == (
        "KGSDF/YGEPL/26-27/03"
    )
    assert invoice.total_amount == 158132.0
    assert invoice.source_filename == (
        "Purchase Invoice 03.pdf"
    )

    assert captured_invoice["validation_status"] == "VALID"


def test_process_invoice_duplicate(monkeypatch):
    existing_invoice_id = "existing-invoice-id"

    monkeypatch.setattr(
        "services.invoice_service.invoice_exists",
        lambda **kwargs: True,
    )

    monkeypatch.setattr(
        "services.invoice_service.get_all_invoices",
        lambda database_path: [
            {
                "id": existing_invoice_id,
                "invoice_number": "KGSDF/YGEPL/26-27/03",
                "invoice_type": "PURCHASE",
                "invoice_date": "24/08/2026",
                "seller_gstin": "09AAKCK2797D1Z6",
                "buyer_gstin": "09AABCY6613M1ZV",
            }
        ],
    )

    result = process_invoice(
        PURCHASE_03,
        source_filename="Purchase Invoice 03.pdf",
    )

    assert result["success"] is False
    assert result["status"] == "DUPLICATE"
    assert result["invoice_number"] == (
        "KGSDF/YGEPL/26-27/03"
    )
    assert result["existing_invoice_id"] == (
        existing_invoice_id
    )


def test_process_invoice_validation_failure(monkeypatch):
    invoice = extract_invoice(
        PURCHASE_03,
        source_filename="Purchase Invoice 03.pdf",
    )

    # Make the extracted invoice invalid.
    invoice.items[0].quantity = 999999.0

    def mock_extract_invoice(
        pdf_path,
        source_filename=None,
    ):
        return invoice

    monkeypatch.setattr(
        "services.invoice_service.extract_invoice",
        mock_extract_invoice,
    )

    result = process_invoice(
        PURCHASE_03,
        source_filename="Purchase Invoice 03.pdf",
    )

    assert result["success"] is False
    assert result["status"] == "VALIDATION_FAILED"
    assert result["invoice_number"] == (
        "KGSDF/YGEPL/26-27/03"
    )
    assert len(result["errors"]) > 0
    assert result["warnings"] == []

from __future__ import annotations

from pathlib import Path

from extraction.invoice_extractor import extract_invoice
from extraction.validators import validate_invoice

from database.db import (
    DEFAULT_DATABASE,
    insert_validated_invoice,
    invoice_exists,
    get_all_invoices,
)


class InvoiceProcessingError(Exception):
    """
    Raised when an uploaded file is a valid file type
    but cannot be processed as a valid InvoiceIQ invoice.
    """
    pass


def process_invoice(
    pdf_path: str | Path,
    database_path: str | Path = DEFAULT_DATABASE,
) -> dict:
    pdf_path = Path(pdf_path)

    # --------------------------------------------------------
    # 1. Extract invoice
    # --------------------------------------------------------
    try:
        invoice = extract_invoice(pdf_path)

    except Exception as exc:
        # Extraction/parsing failures are bad input,
        # not server failures.
        raise InvoiceProcessingError(
            str(exc)
        ) from exc

    # --------------------------------------------------------
    # 2. Validate extracted invoice
    # --------------------------------------------------------
    validation_result = validate_invoice(invoice)

    if not validation_result.is_valid:
        return {
            "success": False,
            "status": "VALIDATION_FAILED",
            "invoice_number": invoice.invoice_number,
            "errors": validation_result.errors,
            "warnings": validation_result.warnings,
        }

    # --------------------------------------------------------
    # 3. Duplicate check
    #
    # Invoice identity is:
    #   invoice number
    #   + invoice type
    #   + invoice date
    #   + seller GSTIN
    #   + buyer GSTIN
    #
    # This allows legitimate invoices to reuse an invoice
    # number across different dates/transactions.
    # --------------------------------------------------------
    if invoice_exists(
        invoice_number=invoice.invoice_number,
        invoice_type=invoice.invoice_type,
        invoice_date=invoice.invoice_date,
        seller_gstin=invoice.seller_gstin,
        buyer_gstin=invoice.buyer_gstin,
        database_path=database_path,
    ):
        existing_invoices = get_all_invoices(
            database_path
        )

        existing_invoice_id = next(
            (
                existing["id"]
                for existing in existing_invoices
                if (
                    existing["invoice_number"]
                    == invoice.invoice_number
                    and existing["invoice_type"]
                    == invoice.invoice_type
                    and existing["invoice_date"]
                    == invoice.invoice_date
                    and existing["seller_gstin"]
                    == invoice.seller_gstin
                    and existing["buyer_gstin"]
                    == invoice.buyer_gstin
                )
            ),
            None,
        )

        return {
            "success": False,
            "status": "DUPLICATE",
            "invoice_number": invoice.invoice_number,
            "existing_invoice_id": existing_invoice_id,
        }

    # --------------------------------------------------------
    # 4. Store validated invoice
    # --------------------------------------------------------
    invoice_id = insert_validated_invoice(
        invoice,
        "VALID",
        database_path,
    )

    # --------------------------------------------------------
    # 5. Success
    # --------------------------------------------------------
    return {
        "success": True,
        "status": "PROCESSED",
        "invoice_id": invoice_id,
        "invoice_number": invoice.invoice_number,
        "validation_status": "VALID",
    }
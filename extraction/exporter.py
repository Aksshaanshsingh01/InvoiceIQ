"""
InvoiceIQ - Export Layer

Converts validated Invoice objects into JSON.

Responsibilities:
    1. Convert Invoice -> dictionary
    2. Validate before export
    3. Export one invoice to JSON
    4. Export multiple invoices to JSON
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

from .invoice_extractor import Invoice, extract_invoice
from .validators import validate_invoice


# ============================================================
# INVOICE -> DICTIONARY
# ============================================================


def invoice_to_dict(
    invoice: Invoice,
) -> dict:
    """
    Convert an Invoice dataclass into a plain dictionary.

    dataclasses.asdict() also converts nested:
        Item
        Tax

    objects automatically.
    """

    return asdict(invoice)


# ============================================================
# VALIDATED INVOICE -> DICTIONARY
# ============================================================


def invoice_to_export_dict(
    invoice: Invoice,
) -> dict:
    """
    Convert an Invoice into the structured JSON representation
    used by InvoiceIQ.

    Validation information is included in the exported data.
    """

    result = validate_invoice(invoice)

    data = invoice_to_dict(invoice)

    data["validation"] = {
        "status": result.status,
        "is_valid": result.is_valid,
        "errors": result.errors,
        "warnings": result.warnings,
    }

    return data


# ============================================================
# EXPORT ONE INVOICE
# ============================================================


def export_invoice_json(
    invoice: Invoice,
    output_path: str | Path,
) -> Path:
    """
    Export one Invoice object to JSON.

    The invoice is exported even when validation fails.
    The validation result is included in the JSON so that
    downstream systems can decide how to handle it.
    """

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = invoice_to_export_dict(
        invoice
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return output_path


# ============================================================
# EXTRACT + EXPORT
# ============================================================


def extract_and_export_json(
    pdf_path: str | Path,
    output_path: str | Path,
) -> Path:
    """
    Extract an invoice from a PDF and export it as JSON.
    """

    invoice = extract_invoice(
        pdf_path
    )

    return export_invoice_json(
        invoice,
        output_path,
    )


# ============================================================
# BATCH EXPORT
# ============================================================


def export_invoices_json(
    invoices: list[Invoice],
    output_path: str | Path,
) -> Path:
    """
    Export multiple Invoice objects into one JSON file.

    The JSON structure is:

        {
            "invoice_count": ...,
            "invoices": [...]
        }
    """

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    exported_invoices = [
        invoice_to_export_dict(invoice)
        for invoice in invoices
    ]

    data = {
        "invoice_count": len(
            exported_invoices
        ),
        "invoices": exported_invoices,
    }

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return output_path


# ============================================================
# COMMAND LINE TEST
# ============================================================


if __name__ == "__main__":

    import sys

    # --------------------------------------------------------
    # Usage
    # --------------------------------------------------------

    if len(sys.argv) != 3:

        print(
            "Usage:"
        )

        print(
            "python -m extraction.exporter "
            "<input.pdf> <output.json>"
        )

        sys.exit(1)

    input_pdf = Path(
        sys.argv[1]
    )

    output_json = Path(
        sys.argv[2]
    )

    # --------------------------------------------------------
    # Extract
    # --------------------------------------------------------

    print(
        f"Processing: {input_pdf.name}"
    )

    invoice = extract_invoice(
        input_pdf
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    validation = validate_invoice(
        invoice
    )

    print(
        f"Validation: {validation.status}"
    )

    if validation.errors:

        print("\nErrors:")

        for error in validation.errors:

            print(
                f"  ❌ {error}"
            )

    if validation.warnings:

        print("\nWarnings:")

        for warning in validation.warnings:

            print(
                f"  ⚠️  {warning}"
            )

    # --------------------------------------------------------
    # Export
    # --------------------------------------------------------

    output = export_invoice_json(
        invoice,
        output_json,
    )

    print(
        f"\n✅ JSON exported:"
    )

    print(
        output
    )

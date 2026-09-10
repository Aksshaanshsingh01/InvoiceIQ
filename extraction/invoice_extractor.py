"""
InvoiceIQ - Invoice Extraction Engine

Main orchestration layer for the InvoiceIQ extraction system.

Responsibilities:
    1. Extract raw PDF text
    2. Extract invoice metadata
    3. Identify seller / buyer
    4. Identify GSTINs
    5. Detect invoice type
    6. Parse item table using item_parser.py
    7. Parse tax summary using tax_parser.py
    8. Parse totals using totals_parser.py
    9. Reconcile / derive round-off
    10. Convert parser-specific models into canonical
        Invoice / Item / Tax models

Supported current layouts:
    - Purchase invoice: CGST + SGST
    - Sale invoice: IGST

The parser modules are responsible for their own sections.
This file acts as the central orchestration layer.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import re
import sys
from typing import Optional

import pymupdf

from .table_parser import parse_sections
from .item_parser import parse_items
from .tax_parser import parse_tax_summary
from .totals_parser import parse_totals


# ============================================================
# CONFIGURATION
# ============================================================

RECONCILIATION_TOLERANCE = 0.02


# ============================================================
# DATA MODELS
# ============================================================


@dataclass
class Tax:
    """
    Represents one invoice-level tax component.
    """

    type: str
    rate: float
    amount: float


@dataclass
class Item:
    """
    Represents one invoice line item.

    This is the canonical Item model used by the
    rest of InvoiceIQ.
    """

    material_name: str
    hsn: str
    quantity: float
    unit: str
    rate: float
    taxable_value: float


@dataclass
class Invoice:
    """
    Represents the complete structured invoice.

    This is the canonical Invoice model used by:
        - validators
        - Excel exporter
        - dashboard
        - API / UI layer
    """

    # --------------------------------------------------------
    # Invoice metadata
    # --------------------------------------------------------

    invoice_type: str
    invoice_number: str
    invoice_date: str
    due_date: str

    # --------------------------------------------------------
    # Parties
    # --------------------------------------------------------

    seller: str
    buyer: str

    seller_gstin: Optional[str]
    buyer_gstin: Optional[str]

    # --------------------------------------------------------
    # Line items
    # --------------------------------------------------------

    items: list[Item]

    # --------------------------------------------------------
    # Invoice-level taxes
    # --------------------------------------------------------

    taxes: list[Tax]

    # --------------------------------------------------------
    # Totals
    # --------------------------------------------------------

    round_off: float
    total_tax: float
    total_amount: float
    received_amount: float

    # --------------------------------------------------------
    # Source
    # --------------------------------------------------------

    source_file: str


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================


def extract_text(
    pdf_path: str | Path,
) -> str:
    """
    Extract text from all pages of a PDF using PyMuPDF.
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    document = pymupdf.open(pdf_path)

    try:

        pages = [
            page.get_text("text")
            for page in document
        ]

        return "\n".join(pages)

    finally:

        document.close()


# ============================================================
# LINE CLEANING
# ============================================================


def clean_lines(
    text: str,
) -> list[str]:
    """
    Normalize extracted PDF text into useful non-empty lines.
    """

    text = text.replace(
        "\xa0",
        " ",
    )

    lines: list[str] = []

    for line in text.splitlines():

        line = re.sub(
            r"\s+",
            " ",
            line,
        ).strip()

        if line:
            lines.append(line)

    return lines


# ============================================================
# GENERIC HELPERS
# ============================================================


def money(
    value: str | None,
) -> float:
    """
    Convert a monetary string into float.

    Kept for backwards compatibility with code that may
    import this helper from invoice_extractor.py.
    """

    if not value:
        return 0.0

    value = (
        value
        .replace("₹", "")
        .replace(",", "")
        .strip()
    )

    return float(value)


def percentage(
    value: str | None,
) -> float:
    """
    Convert a percentage string into float.

    Kept for backwards compatibility.
    """

    if not value:
        return 0.0

    return float(
        value
        .replace("%", "")
        .strip()
    )


def normalize_name(
    value: str,
) -> str:
    """
    Normalize whitespace without aggressively modifying
    the original invoice text.
    """

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


# ============================================================
# ROUND-OFF RECONCILIATION
# ============================================================


def calculate_derived_round_off(
    items: list[Item],
    total_tax: float,
    total_amount: float,
) -> float:
    """
    Derive the round-off required to reconcile the invoice.

    Formula:

        Round Off =
            Total Amount
            - Total Taxable Value
            - Total Tax

    Example:

        Taxable Value = 150602.00
        Total Tax     =   7530.10
        Total Amount  = 158132.00

        Round Off =
            158132.00
            -150602.00
            -  7530.10
            ----------
                -0.10
    """

    taxable_value = round(
        sum(
            item.taxable_value
            for item in items
        ),
        2,
    )

    derived_round_off = round(
        total_amount
        - taxable_value
        - total_tax,
        2,
    )

    return derived_round_off


def resolve_round_off(
    parsed_round_off: float,
    items: list[Item],
    total_tax: float,
    total_amount: float,
) -> float:
    """
    Resolve the final round-off value.

    Rules:

    1. Calculate the round-off implied by the invoice totals.

    2. If the parser already extracted a non-zero
       round-off, preserve that explicit value.

    3. If the parser extracted zero, but the invoice
       requires a non-zero adjustment, use the derived
       value.

    4. If both values are effectively zero, return zero.

    IMPORTANT:
        This function does not silently replace a non-zero
        explicit round-off with a derived value.
    """

    parsed_round_off = round(
        parsed_round_off,
        2,
    )

    derived_round_off = calculate_derived_round_off(
        items=items,
        total_tax=total_tax,
        total_amount=total_amount,
    )

    # --------------------------------------------------------
    # Case 1:
    # Explicit round-off exists.
    #
    # Preserve it.
    # --------------------------------------------------------

    if abs(parsed_round_off) > RECONCILIATION_TOLERANCE:

        return parsed_round_off

    # --------------------------------------------------------
    # Case 2:
    # No explicit round-off was extracted.
    #
    # If the invoice totals imply an adjustment, use it.
    # --------------------------------------------------------

    if abs(derived_round_off) > RECONCILIATION_TOLERANCE:

        return derived_round_off

    # --------------------------------------------------------
    # Case 3:
    # No adjustment required.
    # --------------------------------------------------------

    return 0.0


# ============================================================
# INVOICE METADATA
# ============================================================


def extract_invoice_number(
    lines: list[str],
) -> str:
    """
    Extract invoice number.

    Handles the current Purchase layout where the invoice
    number wraps across two lines.
    """

    for index, line in enumerate(lines):

        if line.lower() == "invoice no.":

            if index + 1 >= len(lines):
                break

            value = lines[index + 1]

            # Purchase invoice number can wrap:
            #
            # KGSDF/YGEPL/26-
            # 27/04

            if (
                index + 2 < len(lines)
                and re.fullmatch(
                    r"[\d/]+",
                    lines[index + 2],
                )
            ):

                value += lines[index + 2]

            return value.replace(
                " ",
                "",
            )

    raise ValueError(
        "Invoice number not found."
    )


def extract_date_after_label(
    lines: list[str],
    label: str,
) -> str:
    """
    Extract the line immediately following a label.
    """

    for index, line in enumerate(lines):

        if line.lower() == label.lower():

            if index + 1 < len(lines):

                return lines[index + 1]

    raise ValueError(
        f"{label} not found."
    )


# ============================================================
# PARTIES
# ============================================================


def extract_seller(
    lines: list[str],
) -> str:
    """
    Current sample layouts place the seller/company name
    at the beginning of the document.
    """

    if not lines:

        raise ValueError(
            "Could not determine seller."
        )

    return lines[0]


def extract_buyer(
    lines: list[str],
) -> str:
    """
    Extract buyer from the Bill To section.
    """

    for index, line in enumerate(lines):

        if line.lower() == "bill to":

            if index + 1 < len(lines):

                return lines[index + 1]

    raise ValueError(
        "Buyer / Bill To party not found."
    )


def extract_gstins(
    lines: list[str],
) -> tuple[Optional[str], Optional[str]]:
    """
    Extract GSTINs.

    For the current layouts:

        First GSTIN  -> seller
        Second GSTIN -> buyer

    IMPORTANT:
        This is based on the current invoice layouts.
    """

    gstins: list[str] = []

    pattern = r"\b\d{2}[A-Z0-9]{13}\b"

    for line in lines:

        matches = re.findall(
            pattern,
            line.upper(),
        )

        gstins.extend(matches)

    seller_gstin = (
        gstins[0]
        if len(gstins) >= 1
        else None
    )

    buyer_gstin = (
        gstins[1]
        if len(gstins) >= 2
        else None
    )

    return (
        seller_gstin,
        buyer_gstin,
    )


# ============================================================
# INVOICE TYPE
# ============================================================


def detect_invoice_type(text: str) -> str:
    """
    Detect invoice type.

    Priority:
    1. Explicit SALE / PURCHASE label
    2. IGST -> SALE
    3. CGST + SGST -> PURCHASE
    """

    upper = text.upper()

    # Explicit invoice type
    if re.search(r"\bSALE\b", upper):
        return "SALE"

    if re.search(r"\bPURCHASE\b", upper):
        return "PURCHASE"

    # Tax-based fallback
    if "IGST" in upper:
        return "SALE"

    if "CGST" in upper and "SGST" in upper:
        return "PURCHASE"

    return "UNKNOWN"

    # --------------------------------------------------------
    # 1. Explicit invoice type indicators
    # --------------------------------------------------------

    sale_patterns = [
        r"\bSALE\s+INVOICE\b",
        r"\bSALES\s+INVOICE\b",
        r"\bINVOICE\s+TYPE\s*[:\-]?\s*SALE\b",
        r"\bTYPE\s*[:\-]?\s*SALE\b",
        r"\bSALE\b",
    ]

    purchase_patterns = [
        r"\bPURCHASE\s+INVOICE\b",
        r"\bPURCHASE\s+INVOICE\b",
        r"\bINVOICE\s+TYPE\s*[:\-]?\s*PURCHASE\b",
        r"\bTYPE\s*[:\-]?\s*PURCHASE\b",
        r"\bPURCHASE\b",
    ]

    # Explicit SALE
    for pattern in sale_patterns:
        if re.search(pattern, upper):
            return "SALE"

    # Explicit PURCHASE
    for pattern in purchase_patterns:
        if re.search(pattern, upper):
            return "PURCHASE"

    # --------------------------------------------------------
    # 2. Fall back to tax structure
    # --------------------------------------------------------

    if "IGST" in upper:
        return "SALE"

    if "CGST" in upper and "SGST" in upper:
        return "PURCHASE"

    # --------------------------------------------------------
    # 3. Unknown
    # --------------------------------------------------------

    return "UNKNOWN"


# ============================================================
# CONVERT PARSED ITEMS
# ============================================================


def convert_items(
    parsed_items,
) -> list[Item]:
    """
    Convert ParsedItem objects produced by item_parser.py
    into canonical Invoice Item objects.
    """

    items: list[Item] = []

    for parsed_item in parsed_items:

        taxable_value = round(
            parsed_item.quantity
            * parsed_item.rate,
            2,
        )

        items.append(
            Item(
                material_name=normalize_name(
                    parsed_item.material_name
                ),
                hsn=str(
                    parsed_item.hsn
                ),
                quantity=float(
                    parsed_item.quantity
                ),
                unit=str(
                    parsed_item.unit
                ),
                rate=float(
                    parsed_item.rate
                ),
                taxable_value=taxable_value,
            )
        )

    return items


# ============================================================
# CONVERT PARSED TAXES
# ============================================================


def convert_taxes(
    parsed_taxes,
) -> list[Tax]:
    """
    Convert ParsedTax objects produced by tax_parser.py
    into canonical Invoice Tax objects.
    """

    taxes: list[Tax] = []

    for parsed_tax in parsed_taxes:

        taxes.append(
            Tax(
                type=str(
                    parsed_tax.type
                ).upper(),
                rate=float(
                    parsed_tax.rate
                ),
                amount=round(
                    float(
                        parsed_tax.amount
                    ),
                    2,
                ),
            )
        )

    return taxes


# ============================================================
# MAIN EXTRACTION PIPELINE
# ============================================================


def extract_invoice(
    pdf_path: str | Path,
) -> Invoice:
    """
    Main InvoiceIQ extraction pipeline.

    Pipeline:

        PDF
         ↓
        Raw text
         ↓
        Metadata extraction
         ↓
        table_parser
         ↓
        ┌──────────────┬──────────────┬──────────────┐
        ↓              ↓              ↓
        items          taxes          totals
        ↓              ↓              ↓
        item_parser    tax_parser     totals_parser
        └──────────────┴──────────────┴──────────────┘
                       ↓
                Round-off reconciliation
                       ↓
                 Canonical Invoice
    """

    pdf_path = Path(pdf_path)

    # --------------------------------------------------------
    # 1. Extract raw PDF text
    # --------------------------------------------------------

    raw_text = extract_text(
        pdf_path
    )

    # --------------------------------------------------------
    # 2. Normalize lines
    # --------------------------------------------------------

    lines = clean_lines(
        raw_text
    )

    # --------------------------------------------------------
    # 3. Detect invoice type
    # --------------------------------------------------------

    invoice_type = detect_invoice_type(
        raw_text
    )

    if invoice_type == "UNKNOWN":

        raise ValueError(
            "Could not determine invoice type."
        )

    # --------------------------------------------------------
    # 4. Extract invoice metadata
    # --------------------------------------------------------

    invoice_number = extract_invoice_number(
        lines
    )

    invoice_date = extract_date_after_label(
        lines,
        "Invoice Date",
    )

    due_date = extract_date_after_label(
        lines,
        "Due Date",
    )

    # --------------------------------------------------------
    # 5. Extract parties
    # --------------------------------------------------------

    seller = extract_seller(
        lines
    )

    buyer = extract_buyer(
        lines
    )

    seller_gstin, buyer_gstin = extract_gstins(
        lines
    )

    # --------------------------------------------------------
    # 6. Parse invoice sections
    # --------------------------------------------------------

    sections = parse_sections(
        pdf_path
    )

    # --------------------------------------------------------
    # 7. Parse items
    # --------------------------------------------------------

    parsed_items = parse_items(
        sections.item_table
    )

    items = convert_items(
        parsed_items
    )

    if not items:

        raise ValueError(
            "No invoice items were extracted."
        )

    # --------------------------------------------------------
    # 8. Parse taxes
    # --------------------------------------------------------

    tax_summary = parse_tax_summary(
        sections.tax_summary,
        invoice_type,
    )

    taxes = convert_taxes(
        tax_summary.taxes
    )

    # --------------------------------------------------------
    # 9. Parse totals
    # --------------------------------------------------------

    parsed_totals = parse_totals(
        sections.totals,
        invoice_type,
    )

    # --------------------------------------------------------
    # 10. Total tax
    # --------------------------------------------------------

    total_tax = round(
        tax_summary.total_tax,
        2,
    )

    # --------------------------------------------------------
    # 11. Total amount
    # --------------------------------------------------------

    total_amount = round(
        parsed_totals.total_amount,
        2,
    )

    # --------------------------------------------------------
    # 12. Resolve round-off
    #
    # This is important for invoices where the PDF does
    # not explicitly expose a Round Off field.
    # --------------------------------------------------------

    round_off = resolve_round_off(
        parsed_round_off=parsed_totals.round_off,
        items=items,
        total_tax=total_tax,
        total_amount=total_amount,
    )

    # --------------------------------------------------------
    # 13. Construct canonical Invoice
    # --------------------------------------------------------

    return Invoice(
        invoice_type=invoice_type,

        invoice_number=invoice_number,

        invoice_date=invoice_date,

        due_date=due_date,

        seller=seller,

        buyer=buyer,

        seller_gstin=seller_gstin,

        buyer_gstin=buyer_gstin,

        items=items,

        taxes=taxes,

        round_off=round(
            round_off,
            2,
        ),

        total_tax=total_tax,

        total_amount=total_amount,

        received_amount=round(
            parsed_totals.received_amount,
            2,
        ),

        source_file=str(
            pdf_path
        ),
    )


# ============================================================
# SERIALIZATION
# ============================================================


def invoice_to_dict(
    invoice: Invoice,
) -> dict:
    """
    Convert Invoice dataclass into a dictionary.

    Useful for:
        - JSON
        - APIs
        - debugging
        - frontend communication
    """

    return asdict(
        invoice
    )


# ============================================================
# COMMAND LINE INTERFACE
# ============================================================


if __name__ == "__main__":

    if len(sys.argv) != 2:

        print(
            "Usage: "
            "python -m extraction.invoice_extractor "
            "<invoice.pdf>"
        )

        sys.exit(1)

    invoice = extract_invoice(
        sys.argv[1]
    )

    print(
        json.dumps(
            invoice_to_dict(invoice),
            indent=2,
            ensure_ascii=False,
        )
    ) 
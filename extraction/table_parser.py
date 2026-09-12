"""
InvoiceIQ - Invoice Table Parser

Responsible for identifying logical sections inside an invoice.

This module currently supports the two known invoice layouts:

1. Purchase Invoice
2. Sale Invoice

It separates the document into:

    - Item table
    - Tax summary
    - Totals

It does NOT extract individual invoice fields yet.

The output of this module will later be consumed by the
item parser, tax parser, and invoice extraction engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import pymupdf


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class TableSection:
    """
    Represents one logical section of an invoice.
    """

    start: int
    end: int
    lines: list[str]


@dataclass
class InvoiceSections:
    """
    Contains the important logical sections of an invoice.
    """

    item_table: TableSection
    tax_summary: TableSection
    totals: TableSection


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================

def extract_text(
    pdf_path: str | Path,
) -> str:
    """
    Extract raw text from a PDF using PyMuPDF.
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found: {pdf_path}"
        )

    document = pymupdf.open(pdf_path)

    try:
        pages: list[str] = []

        for page in document:
            pages.append(
                page.get_text("text")
            )

        return "\n".join(pages)

    finally:
        document.close()


# ============================================================
# LINE NORMALIZATION
# ============================================================

def clean_lines(
    text: str,
) -> list[str]:
    """
    Normalize PDF text into clean, non-empty lines.
    """

    lines: list[str] = []

    for line in text.splitlines():

        line = (
            line
            .replace("\xa0", " ")
            .strip()
        )

        if not line:
            continue

        lines.append(line)

    return lines


# ============================================================
# SEARCH HELPERS
# ============================================================

def find_line(
    lines: list[str],
    target: str,
    start: int = 0,
) -> int | None:
    """
    Find the first exact line matching target.

    Matching is case-insensitive.
    """

    target = target.strip().lower()

    for index in range(
        start,
        len(lines),
    ):

        if (
            lines[index]
            .strip()
            .lower()
            == target
        ):
            return index

    return None


def find_last_line(
    lines: list[str],
    target: str,
) -> int | None:
    """
    Find the last exact line matching target.
    """

    target = target.strip().lower()

    for index in range(
        len(lines) - 1,
        -1,
        -1,
    ):

        if (
            lines[index]
            .strip()
            .lower()
            == target
        ):
            return index

    return None


# ============================================================
# PURCHASE SECTION DETECTION
# ============================================================

def detect_purchase_sections(
    lines: list[str],
) -> InvoiceSections:
    """
    Detect logical sections in the current Purchase invoice.

    Current structure:

        Items
        HSN No.
        Qty.
        Rate
        Tax
        Total
        ...
        SUBTOTAL
        ...
        Taxable Amount
        ₹ 73,000
        CGST @2.5%
        ₹ 1,825
        SGST @2.5%
        ₹ 1,825
        Total Amount
        ₹ 76,650
        Received Amount
        ₹ 0
    """

    # ========================================================
    # ITEM TABLE
    # ========================================================

    items_header = find_line(
        lines,
        "Items",
    )

    if items_header is None:
        raise ValueError(
            "Purchase item table header not found."
        )

    subtotal = find_line(
        lines,
        "SUBTOTAL",
        items_header + 1,
    )

    if subtotal is None:
        raise ValueError(
            "Purchase item table end "
            "(SUBTOTAL) not found."
        )

    item_table = TableSection(
        start=items_header,
        end=subtotal,
        lines=lines[
            items_header:subtotal
        ],
    )

    # ========================================================
    # TAX SUMMARY
    # ========================================================

    taxable_amount = find_line(
        lines,
        "Taxable Amount",
        subtotal + 1,
    )

    if taxable_amount is None:
        raise ValueError(
            "Purchase tax summary header "
            "not found."
        )

    total_amount = find_line(
        lines,
        "Total Amount",
        taxable_amount + 1,
    )

    if total_amount is None:
        raise ValueError(
            "Purchase Total Amount section "
            "not found."
        )

    tax_summary = TableSection(
        start=taxable_amount,
        end=total_amount,
        lines=lines[
            taxable_amount:total_amount
        ],
    )

    # ========================================================
    # TOTALS
    # ========================================================

    received_amount = find_line(
        lines,
        "Received Amount",
        total_amount + 1,
    )

    if received_amount is None:

        # Keep the section valid even if the invoice
        # does not contain a Received Amount field.
        totals_end = len(lines)

    else:

        totals_end = received_amount + 1

    totals = TableSection(
        start=total_amount,
        end=totals_end,
        lines=lines[
            total_amount:totals_end
        ],
    )

    # ========================================================
    # RETURN
    # ========================================================

    return InvoiceSections(
        item_table=item_table,
        tax_summary=tax_summary,
        totals=totals,
    )


# ============================================================
# SALE SECTION DETECTION
# ============================================================

def detect_sale_sections(lines: list[str]) -> InvoiceSections:
    """Detect sections in Sale invoices, including reordered PDF text."""

    items_header = _find_any_line(lines, {"S.NO.", "S.NO", "S NO.", "S NO"})
    if items_header is None:
        raise ValueError("Sale item table header not found.")

    total = find_line(lines, "TOTAL", items_header + 1)
    if total is None:
        total = _find_case_insensitive_contains(lines, "TOTAL")
    if total is None:
        raise ValueError("Sale TOTAL section not found.")

    round_off = find_line(lines, "Round Off", items_header + 1)
    tax_summary_header = _find_any_line(lines, {"HSN/SAC", "HSN / SAC", "HSN SAC"}, items_header + 1)
    tax_summary_end = None
    if tax_summary_header is not None:
        tax_summary_end = _find_any_line(
            lines,
            {"Total Amount (in words)", "TOTAL AMOUNT (IN WORDS)"},
            tax_summary_header + 1,
        )

    # A Sale PDF can place the tax-summary header before the actual item
    # values. Therefore HSN/SAC is NOT used as the item-table boundary.
    # Keep the whole area up to TOTAL so item_parser can recover the
    # item from the reordered text.
    item_table_end = total
    item_table = TableSection(
        start=items_header,
        end=item_table_end,
        lines=lines[items_header:item_table_end],
    )

    totals_start = round_off if round_off is not None and round_off < total else total
    received_amount = _find_any_line(lines, {"RECEIVED AMOUNT", "Received Amount"}, total + 1)
    totals_end = (received_amount + 1) if received_amount is not None else len(lines)
    totals = TableSection(
        start=totals_start,
        end=totals_end,
        lines=lines[totals_start:totals_end],
    )

    if tax_summary_header is None:
        # Some valid Sale PDFs have no HSN/SAC summary header. Keep a
        # minimal section rather than failing section detection.
        tax_summary = TableSection(start=total, end=total, lines=[])
    else:
        end = tax_summary_end if tax_summary_end is not None else total
        if end < tax_summary_header:
            end = total
        tax_summary = TableSection(
            start=tax_summary_header,
            end=end,
            lines=lines[tax_summary_header:end],
        )

    return InvoiceSections(item_table=item_table, tax_summary=tax_summary, totals=totals)


def _find_any_line(lines: list[str], targets: set[str], start: int = 0) -> int | None:
    normalized = {target.strip().lower() for target in targets}
    for i in range(start, len(lines)):
        if lines[i].strip().lower() in normalized:
            return i
    return None


def _find_case_insensitive_contains(lines: list[str], target: str, start: int = 0) -> int | None:
    target = target.lower()
    for i in range(start, len(lines)):
        if target in lines[i].lower():
            return i
    return None


# ============================================================
# INVOICE LAYOUT DETECTION
# ============================================================

def detect_invoice_layout(lines: list[str]) -> str:
    """Detect Purchase/Sale using tolerant header matching."""
    normalized = [re.sub(r"\s+", " ", line.strip()).upper() for line in lines]

    # Strongest signal: Sale table header.
    if any(line in {"S.NO.", "S.NO", "S NO.", "S NO"} for line in normalized):
        return "SALE"

    # Purchase templates use an Items header and typically HSN No./Qty.
    if any(line in {"ITEMS", "ITEM"} for line in normalized):
        return "PURCHASE"

    # Fallback for minor PDF extraction differences.
    has_hsn_no = any("HSN NO" in line for line in normalized)
    has_qty = any(line in {"QTY.", "QTY", "QUANTITY"} for line in normalized)
    if has_hsn_no and has_qty:
        return "PURCHASE"

    # Last-resort document-level signals.
    if any(line == "SALE" or line.startswith("SALE ") for line in normalized):
        return "SALE"
    if any(line == "PURCHASE" or line.startswith("PURCHASE ") for line in normalized):
        return "PURCHASE"

    return "UNKNOWN"


# ============================================================
# MAIN SECTION PARSER
# ============================================================

def parse_sections(
    pdf_path: str | Path,
) -> InvoiceSections:
    """
    Extract PDF text and identify its logical sections.
    """

    text = extract_text(
        pdf_path
    )

    lines = clean_lines(
        text
    )

    invoice_layout = detect_invoice_layout(
        lines
    )

    if invoice_layout == "PURCHASE":

        return detect_purchase_sections(
            lines
        )

    if invoice_layout == "SALE":

        return detect_sale_sections(
            lines
        )

    raise ValueError(
        "Unknown invoice layout. "
        "Could not identify Purchase or Sale "
        "invoice structure."
    )


# ============================================================
# DEBUG DISPLAY
# ============================================================

def print_section(
    title: str,
    section: TableSection,
) -> None:
    """
    Print one parsed section.
    """

    print("\n")
    print("=" * 80)
    print(title)
    print("=" * 80)

    print(
        f"Lines {section.start} → {section.end}"
    )

    print("-" * 80)

    for line in section.lines:
        print(line)


def print_invoice_sections(
    pdf_path: str | Path,
) -> None:
    """
    Parse and display all invoice sections.
    """

    print("\n")
    print("#" * 80)
    print(
        f"FILE: {Path(pdf_path).name}"
    )
    print("#" * 80)

    sections = parse_sections(
        pdf_path
    )

    print_section(
        "ITEM TABLE",
        sections.item_table,
    )

    print_section(
        "TAX SUMMARY",
        sections.tax_summary,
    )

    print_section(
        "TOTALS",
        sections.totals,
    )


# ============================================================
# STANDALONE DEBUGGER
# ============================================================

if __name__ == "__main__":

    project_root = (
        Path(__file__)
        .resolve()
        .parent
        .parent
    )

    sample_files = [
        (
            project_root
            / "samples"
            / "Purchase Invoice 4.pdf"
        ),
        (
            project_root
            / "samples"
            / "Sale Invoice 4.pdf"
        ),
    ]

    for pdf_file in sample_files:

        try:

            print_invoice_sections(
                pdf_file
            )

        except Exception as error:

            print("\n")
            print(
                f"❌ Failed to parse "
                f"{pdf_file.name}"
            )

            print(
                f"Reason: {error}"
            )

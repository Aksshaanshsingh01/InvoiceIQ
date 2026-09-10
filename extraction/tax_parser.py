"""
InvoiceIQ - Tax Parser

Parses the tax-summary section produced by table_parser.py.

Supported layouts:

1. Purchase Invoice
2. Sale Invoice

Purchase example:

    Taxable Amount
    ₹ 73,000
    CGST @2.5%
    ₹ 1,825
    SGST @2.5%
    ₹ 1,825

Sale example:

    HSN/SAC
    Taxable Value
    IGST
    Rate
    Amount
    Total Tax Amount
    44013100
    74,250
    5%
    3,712.5
    ₹ 3,712.5

The parser normalizes both layouts into the same
internal representation.

This module does NOT modify invoice_extractor.py.
"""


from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .table_parser import (
    TableSection,
    parse_sections,
)


# ============================================================
# DATA MODELS
# ============================================================


@dataclass
class ParsedTax:
    """
    Represents one tax component.

    Examples:

        CGST @ 2.5% = ₹1,825
        SGST @ 2.5% = ₹1,825
        IGST @ 5%   = ₹3,712.50
    """

    type: str
    rate: float
    amount: float


@dataclass
class ParsedTaxSummary:
    """
    Represents the normalized tax summary of an invoice.
    """

    taxable_value: float
    taxes: list[ParsedTax]
    total_tax: float


# ============================================================
# MONEY
# ============================================================


def parse_money(
    value: str,
) -> float:
    """
    Convert a formatted monetary string into float.

    Examples:

        "₹ 73,000"  -> 73000.0
        "₹ 1,825"   -> 1825.0
        "3,712.5"   -> 3712.5
    """

    value = (
        value
        .replace("₹", "")
        .replace(",", "")
        .strip()
    )

    return float(value)


def is_money(
    value: str,
) -> bool:
    """
    Check whether a line represents a monetary value.
    """

    return bool(
        re.fullmatch(
            r"₹?\s*"
            r"[\d,]+"
            r"(?:\.\d+)?",
            value.strip(),
        )
    )


# ============================================================
# PERCENTAGE
# ============================================================


def parse_percentage(
    value: str,
) -> float:
    """
    Convert a percentage string into float.

    Examples:

        "5%"       -> 5.0
        "(5%)"     -> 5.0
        "2.5%"     -> 2.5
        "(2.5%)"   -> 2.5
    """

    value = (
        value
        .replace("(", "")
        .replace(")", "")
        .replace("%", "")
        .strip()
    )

    return float(value)


def is_percentage(
    value: str,
) -> bool:
    """
    Check whether a line represents a percentage.
    """

    return bool(
        re.fullmatch(
            r"\(?\s*"
            r"\d+(?:\.\d+)?"
            r"%\s*\)?",
            value.strip(),
        )
    )


# ============================================================
# PURCHASE TAX PARSER
# ============================================================


def parse_purchase_tax_summary(
    section: TableSection,
) -> ParsedTaxSummary:
    """
    Parse Purchase invoice tax summary.

    Expected structure:

        Taxable Amount
        ₹ 73,000
        CGST @2.5%
        ₹ 1,825
        SGST @2.5%
        ₹ 1,825
    """

    lines = [
        line.strip()
        for line in section.lines
        if line.strip()
    ]

    if not lines:
        raise ValueError(
            "Purchase tax summary is empty."
        )

    # --------------------------------------------------------
    # Taxable value
    # --------------------------------------------------------

    taxable_index = None

    for index, line in enumerate(lines):

        if line.lower() == "taxable amount":

            taxable_index = index
            break

    if taxable_index is None:
        raise ValueError(
            "Purchase taxable amount "
            "label not found."
        )

    taxable_value = None

    for line in lines[
        taxable_index + 1:
    ]:

        if is_money(line):

            taxable_value = parse_money(
                line
            )

            break

    if taxable_value is None:
        raise ValueError(
            "Purchase taxable amount "
            "value not found."
        )

    # --------------------------------------------------------
    # Individual taxes
    # --------------------------------------------------------

    taxes: list[ParsedTax] = []

    index = taxable_index + 2

    while index < len(lines):

        line = lines[index]

        # Example:
        #
        # CGST @2.5%
        # SGST @2.5%

        match = re.fullmatch(
            r"(CGST|SGST|IGST)"
            r"\s*@\s*"
            r"(\d+(?:\.\d+)?)"
            r"%",
            line,
            flags=re.IGNORECASE,
        )

        if match:

            tax_type = (
                match.group(1)
                .upper()
            )

            tax_rate = float(
                match.group(2)
            )

            tax_amount = None

            # Find the monetary value immediately
            # following the tax label.
            for candidate in lines[
                index + 1:
                index + 3
            ]:

                if is_money(candidate):

                    tax_amount = parse_money(
                        candidate
                    )

                    break

            if tax_amount is None:
                raise ValueError(
                    f"Purchase {tax_type}: "
                    f"tax amount not found."
                )

            taxes.append(
                ParsedTax(
                    type=tax_type,
                    rate=tax_rate,
                    amount=tax_amount,
                )
            )

        index += 1

    if not taxes:
        raise ValueError(
            "No Purchase taxes found."
        )

    # --------------------------------------------------------
    # Total tax
    # --------------------------------------------------------

    total_tax = round(
        sum(
            tax.amount
            for tax in taxes
        ),
        2,
    )

    return ParsedTaxSummary(
        taxable_value=taxable_value,
        taxes=taxes,
        total_tax=total_tax,
    )


# ============================================================
# SALE TAX PARSER
# ============================================================


def parse_sale_tax_summary(
    section: TableSection,
) -> ParsedTaxSummary:
    """
    Parse Sale invoice tax summary.

    Expected structure:

        HSN/SAC
        Taxable Value
        IGST
        Rate
        Amount
        Total Tax Amount

        44013100
        74,250
        5%
        3,712.5
        ₹ 3,712.5
    """

    lines = [
        line.strip()
        for line in section.lines
        if line.strip()
    ]

    if not lines:
        raise ValueError(
            "Sale tax summary is empty."
        )

    # --------------------------------------------------------
    # Locate "Total Tax Amount"
    # --------------------------------------------------------

    total_tax_label_index = None

    for index, line in enumerate(lines):

        if (
            line.lower()
            == "total tax amount"
        ):

            total_tax_label_index = index
            break

    if total_tax_label_index is None:
        raise ValueError(
            "Sale 'Total Tax Amount' "
            "label not found."
        )

    # --------------------------------------------------------
    # Values occur after the headers.
    #
    # Current structure:
    #
    # 44013100
    # 74,250
    # 5%
    # 3,712.5
    # ₹ 3,712.5
    # --------------------------------------------------------

    value_lines = lines[
        total_tax_label_index + 1:
    ]

    if not value_lines:
        raise ValueError(
            "Sale tax summary contains "
            "no values."
        )

    # --------------------------------------------------------
    # HSN
    # --------------------------------------------------------

    hsn_index = None

    for index, line in enumerate(
        value_lines
    ):

        if re.fullmatch(
            r"\d{6,8}",
            line,
        ):

            hsn_index = index
            break

    if hsn_index is None:
        raise ValueError(
            "Sale tax-summary HSN "
            "not found."
        )

    # --------------------------------------------------------
    # Taxable value
    # --------------------------------------------------------

    taxable_value = None

    for line in value_lines[
        hsn_index + 1:
    ]:

        if is_money(line):

            taxable_value = parse_money(
                line
            )

            break

    if taxable_value is None:
        raise ValueError(
            "Sale taxable value "
            "not found."
        )

    # --------------------------------------------------------
    # Tax rate
    # --------------------------------------------------------

    rate_index = None
    tax_rate = None

    for index, line in enumerate(
        value_lines[
            hsn_index + 1:
        ],
        start=hsn_index + 1,
    ):

        if is_percentage(line):

            tax_rate = parse_percentage(
                line
            )

            rate_index = index

            break

    if tax_rate is None:
        raise ValueError(
            "Sale tax rate not found."
        )

    # --------------------------------------------------------
    # Tax amount
    # --------------------------------------------------------

    tax_amount = None

    for line in value_lines[
        rate_index + 1:
    ]:

        if is_money(line):

            tax_amount = parse_money(
                line
            )

            break

    if tax_amount is None:
        raise ValueError(
            "Sale tax amount not found."
        )

    # --------------------------------------------------------
    # Current Sale layout uses IGST.
    #
    # Later we can expand this to support CGST/SGST
    # Sale invoices as well.
    # --------------------------------------------------------

    tax = ParsedTax(
        type="IGST",
        rate=tax_rate,
        amount=tax_amount,
    )

    return ParsedTaxSummary(
        taxable_value=taxable_value,
        taxes=[tax],
        total_tax=round(
            tax_amount,
            2,
        ),
    )


# ============================================================
# MAIN TAX PARSER
# ============================================================


def parse_tax_summary(
    section: TableSection,
    invoice_type: str,
) -> ParsedTaxSummary:
    """
    Parse a tax summary according to invoice type.
    """

    invoice_type = (
        invoice_type
        .strip()
        .upper()
    )

    if invoice_type == "PURCHASE":

        return parse_purchase_tax_summary(
            section
        )

    if invoice_type == "SALE":

        return parse_sale_tax_summary(
            section
        )

    raise ValueError(
        f"Unsupported invoice type: "
        f"{invoice_type}"
    )


# ============================================================
# DEBUG DISPLAY
# ============================================================


def print_tax_summary(
    summary: ParsedTaxSummary,
) -> None:
    """
    Print a parsed tax summary.
    """

    print("\n")
    print("=" * 80)
    print("PARSED TAX SUMMARY")
    print("=" * 80)

    print(
        f"Taxable Value : "
        f"₹{summary.taxable_value:.2f}"
    )

    print(
        f"Total Tax     : "
        f"₹{summary.total_tax:.2f}"
    )

    print(
        "\nTaxes:"
    )

    for index, tax in enumerate(
        summary.taxes,
        start=1,
    ):

        print(
            f"  Tax {index}"
        )

        print(
            f"    Type   : "
            f"{tax.type}"
        )

        print(
            f"    Rate   : "
            f"{tax.rate}%"
        )

        print(
            f"    Amount : "
            f"₹{tax.amount:.2f}"
        )

    print("=" * 80)


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

        print("\n")
        print("#" * 80)
        print(
            f"FILE: {pdf_file.name}"
        )
        print("#" * 80)

        try:

            sections = parse_sections(
                pdf_file
            )

            # ------------------------------------------------
            # Determine layout from item-table header.
            # ------------------------------------------------

            first_line = (
                sections
                .item_table
                .lines[0]
                .strip()
                .upper()
            )

            if first_line == "S.NO.":

                invoice_type = "SALE"

            else:

                invoice_type = "PURCHASE"

            # ------------------------------------------------
            # Parse tax summary.
            # ------------------------------------------------

            summary = parse_tax_summary(
                sections.tax_summary,
                invoice_type,
            )

            print_tax_summary(
                summary
            )

        except Exception as error:

            print(
                f"\n❌ Failed to parse "
                f"{pdf_file.name}"
            )

            print(
                f"Reason: {error}"
            )
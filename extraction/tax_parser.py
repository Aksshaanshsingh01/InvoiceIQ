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

    Supports both:

    1. IGST sale layout

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

    2. CGST + SGST sale layout

        HSN/SAC
        Taxable Value
        CGST
        Rate
        Amount
        SGST
        Rate
        Amount
        Total Tax Amount

        44013100
        1,81,955
        2.5%
        4,548.88
        2.5%
        4,548.88
        ₹ 9,097.75
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
        if line.lower() == "total tax amount":
            total_tax_label_index = index
            break

    if total_tax_label_index is None:
        raise ValueError(
            "Sale 'Total Tax Amount' "
            "label not found."
        )

    # --------------------------------------------------------
    # Identify tax columns from the header
    #
    # The tax types appear BEFORE "Total Tax Amount".
    # This prevents us from assuming that every sale uses IGST.
    # --------------------------------------------------------

    header_lines = lines[:total_tax_label_index]

    tax_types: list[str] = []

    for line in header_lines:
        match = re.fullmatch(
            r"(CGST|SGST|IGST)",
            line,
            flags=re.IGNORECASE,
        )

        if match:
            tax_type = match.group(1).upper()

            if tax_type not in tax_types:
                tax_types.append(tax_type)

    if not tax_types:
        raise ValueError(
            "Sale tax type not found."
        )

    # --------------------------------------------------------
    # Values occur after "Total Tax Amount"
    #
    # Example:
    #
    # 44013100
    # 1,81,955
    # 2.5%
    # 4,548.88
    # 2.5%
    # 4,548.88
    # ₹ 9,097.75
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

    for index, line in enumerate(value_lines):
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

    for line in value_lines[hsn_index + 1:]:
        if is_money(line):
            taxable_value = parse_money(line)
            break

    if taxable_value is None:
        raise ValueError(
            "Sale taxable value "
            "not found."
        )

    # --------------------------------------------------------
    # Extract all tax rates and amounts
    #
    # We intentionally collect the percentage/money pairs
    # instead of assuming there is only one tax.
    # --------------------------------------------------------

    tax_values = value_lines[hsn_index + 1:]

    tax_pairs: list[tuple[float, float]] = []

    index = 0

    while index < len(tax_values):
        line = tax_values[index]

        if is_percentage(line):
            tax_rate = parse_percentage(line)

            tax_amount = None

            for candidate in tax_values[index + 1:]:
                if is_money(candidate):
                    tax_amount = parse_money(candidate)
                    break

                # Stop if another percentage appears before
                # finding an amount.
                if is_percentage(candidate):
                    break

            if tax_amount is not None:
                tax_pairs.append(
                    (tax_rate, tax_amount)
                )

        index += 1

    if not tax_pairs:
        raise ValueError(
            "Sale tax rate/amount "
            "not found."
        )

    # --------------------------------------------------------
    # Match tax types to tax pairs
    # --------------------------------------------------------

    if len(tax_pairs) < len(tax_types):
        raise ValueError(
            "Sale tax summary contains "
            f"{len(tax_types)} tax types but only "
            f"{len(tax_pairs)} tax values."
        )

    taxes: list[ParsedTax] = []

    for tax_type, (tax_rate, tax_amount) in zip(
        tax_types,
        tax_pairs,
    ):
        taxes.append(
            ParsedTax(
                type=tax_type,
                rate=tax_rate,
                amount=tax_amount,
            )
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
# MAIN TAX PARSER
# ============================================================

def parse_tax_summary(
    section: TableSection,
    invoice_type: str,
) -> ParsedTaxSummary:

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

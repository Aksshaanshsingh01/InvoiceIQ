"""
InvoiceIQ - Totals Parser

Parses the totals section produced by table_parser.py.

Supports:
    1. Purchase invoices
    2. Sale invoices

Handles:
    - Round off
    - Positive round off
    - Negative round off
    - Total amount
    - Received amount
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
# DATA MODEL
# ============================================================


@dataclass
class ParsedTotals:
    """
    Represents the financial totals of an invoice.
    """

    round_off: float
    total_amount: float
    received_amount: float


# ============================================================
# MONEY HELPERS
# ============================================================


def parse_money(
    value: str,
) -> float:
    """
    Convert a monetary value into float.

    Examples:

        "₹ 76,650" -> 76650.0
        "₹ 0.5"    -> 0.5
        "77,963"   -> 77963.0
        "0"        -> 0.0
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

    Supports both positive and negative values.

    Examples:

        ₹ 76,650
        ₹ 0.5
        77,963
        -₹ 0.1
        ₹ -0.1
        -0.1
    """

    return bool(
        re.fullmatch(
            r"-?\s*"
            r"₹?\s*"
            r"-?\s*"
            r"[\d,]+"
            r"(?:\.\d+)?",
            value.strip(),
        )
    )


def parse_signed_money(
    value: str,
) -> float:
    """
    Parse money while preserving its sign.

    Examples:

        "₹ 0.5"  -> 0.5
        "-₹ 0.1" -> -0.1
        "₹ -0.1" -> -0.1
        "-0.1"   -> -0.1
    """

    value = value.strip()

    negative = "-" in value

    value = (
        value
        .replace("₹", "")
        .replace(",", "")
        .replace("-", "")
        .strip()
    )

    amount = float(value)

    if negative:
        return -amount

    return amount


def extract_round_off(
    lines: list[str],
    label_index: int,
) -> float:
    """
    Extract the round-off value from the lines following
    the 'Round Off' label.

    Important:
        Standalone '-' values are treated as PDF table
        placeholders, NOT as negative signs.

    Examples:

        Round Off
        -
        -
        -
        ₹ 0.5

        -> +0.50

    Explicit negative values are also supported:

        Round Off
        -₹ 0.1

        -> -0.10

    or:

        Round Off
        ₹ -0.1

        -> -0.10
    """

    for index in range(
        label_index + 1,
        min(label_index + 10, len(lines)),
    ):

        line = lines[index].strip()

        # ----------------------------------------------------
        # Stop when we reach the next totals section.
        # ----------------------------------------------------

        if line.lower() in {
            "total",
            "total amount",
            "received amount",
        }:
            break

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Ignore standalone "-", "–", "—".
        #
        # In the Sale invoice these are table placeholders.
        # They do NOT mean the round-off is negative.
        # ----------------------------------------------------

        if line in {
            "-",
            "–",
            "—",
        }:
            continue

        # ----------------------------------------------------
        # Find the actual monetary value.
        # ----------------------------------------------------

        if is_money(line):

            return round(
                parse_signed_money(line),
                2,
            )

    # --------------------------------------------------------
    # No round-off value found.
    # --------------------------------------------------------

    return 0.0

# ============================================================
# PURCHASE TOTALS
# ============================================================


def parse_purchase_totals(
    section: TableSection,
) -> ParsedTotals:
    """
    Parse totals from a Purchase invoice.

    Supported examples:

        Total Amount
        ₹ 76,650
        Received Amount
        ₹ 0

    And:

        Round Off
        -
        ₹ 0.1
        Total Amount
        ₹ 158,132
    """

    lines = [
        line.strip()
        for line in section.lines
        if line.strip()
    ]

    if not lines:
        raise ValueError(
            "Purchase totals section is empty."
        )

    # ========================================================
    # TOTAL AMOUNT
    # ========================================================

    total_index = None

    for index, line in enumerate(lines):

        if line.lower() == "total amount":

            total_index = index
            break

    if total_index is None:

        raise ValueError(
            "Purchase 'Total Amount' label not found."
        )

    total_amount = None

    for line in lines[
        total_index + 1:
    ]:

        if is_money(line):

            total_amount = parse_money(line)
            break

    if total_amount is None:

        raise ValueError(
            "Purchase total amount value not found."
        )

    # ========================================================
    # RECEIVED AMOUNT
    # ========================================================

    received_index = None

    for index, line in enumerate(
        lines[
            total_index + 1:
        ],
        start=total_index + 1,
    ):

        if line.lower() == "received amount":

            received_index = index
            break

    if received_index is None:

        raise ValueError(
            "Purchase 'Received Amount' "
            "label not found."
        )

    received_amount = None

    for line in lines[
        received_index + 1:
    ]:

        if is_money(line):

            received_amount = parse_money(line)
            break

    if received_amount is None:

        received_amount = 0.0

    # ========================================================
    # ROUND OFF
    # ========================================================

    round_off_index = None

    for index, line in enumerate(lines):

        if line.lower() == "round off":

            round_off_index = index
            break

    if round_off_index is None:

        round_off = 0.0

    else:

        round_off = extract_round_off(
            lines,
            round_off_index,
        )

    # ========================================================
    # RETURN
    # ========================================================

    return ParsedTotals(
        round_off=round(
            round_off,
            2,
        ),
        total_amount=round(
            total_amount,
            2,
        ),
        received_amount=round(
            received_amount,
            2,
        ),
    )


# ============================================================
# SALE TOTALS
# ============================================================


def parse_sale_totals(
    section: TableSection,
) -> ParsedTotals:
    """
    Parse totals from a Sale invoice.

    Supports both Sale invoice variants:

    1. Invoices with an explicit Round Off section:

        Round Off
        -
        -
        -
        ₹ 0.5
        TOTAL
        ...
        ₹ 77,963
        RECEIVED AMOUNT
        ₹ 0

    2. Invoices without a Round Off section:

        TOTAL
        ...
        ₹ 77,963
        RECEIVED AMOUNT
        ₹ 0

    Standalone '-' values in the Round Off area are PDF table
    placeholders and are NOT interpreted as negative values.
    """

    lines = [
        line.strip()
        for line in section.lines
        if line.strip()
    ]

    if not lines:
        raise ValueError(
            "Sale totals section is empty."
        )

    # ========================================================
    # ROUND OFF
    # ========================================================

    round_off_index = None

    for index, line in enumerate(lines):
        if line.lower() == "round off":
            round_off_index = index
            break

    if round_off_index is None:
        round_off = 0.0
    else:
        round_off = extract_round_off(
            lines,
            round_off_index,
        )

    # ========================================================
    # TOTAL
    # ========================================================

    # Search for TOTAL after Round Off when present; otherwise
    # search from the beginning of the totals section.
    total_search_start = (
        round_off_index + 1
        if round_off_index is not None
        else 0
    )

    total_index = None

    for index, line in enumerate(
        lines[total_search_start:],
        start=total_search_start,
    ):
        if line.lower() == "total":
            total_index = index
            break

    if total_index is None:
        raise ValueError(
            "Sale 'TOTAL' label not found."
        )

    # ========================================================
    # RECEIVED AMOUNT
    # ========================================================

    received_index = None

    for index, line in enumerate(
        lines[total_index + 1:],
        start=total_index + 1,
    ):
        if line.lower() == "received amount":
            received_index = index
            break

    if received_index is None:
        raise ValueError(
            "Sale 'RECEIVED AMOUNT' section not found."
        )

    # ========================================================
    # TOTAL AMOUNT
    # ========================================================

    total_candidates: list[float] = []

    for line in lines[total_index + 1:received_index]:
        if is_money(line):
            total_candidates.append(
                parse_money(line)
            )

    if not total_candidates:
        raise ValueError(
            "Sale total amount value not found."
        )

    # The final monetary value before RECEIVED AMOUNT is
    # the invoice total. This handles the multi-line TOTAL
    # layout used by the Sale invoices.
    total_amount = total_candidates[-1]

    # ========================================================
    # RECEIVED AMOUNT
    # ========================================================

    received_amount = None

    for line in lines[received_index + 1:]:
        if is_money(line):
            received_amount = parse_money(line)
            break

    # Sale invoices may omit the value after the label.
    # Treat that case as zero rather than failing.
    if received_amount is None:
        received_amount = 0.0

    # ========================================================
    # RETURN
    # ========================================================

    return ParsedTotals(
        round_off=round(
            round_off,
            2,
        ),
        total_amount=round(
            total_amount,
            2,
        ),
        received_amount=round(
            received_amount,
            2,
        ),
    )


# ============================================================
# MAIN TOTALS PARSER
# ============================================================


def parse_totals(
    section: TableSection,
    invoice_type: str,
) -> ParsedTotals:
    """
    Parse totals according to invoice type.
    """

    invoice_type = (
        invoice_type
        .strip()
        .upper()
    )

    if invoice_type == "PURCHASE":

        return parse_purchase_totals(
            section
        )

    if invoice_type == "SALE":

        return parse_sale_totals(
            section
        )

    raise ValueError(
        f"Unsupported invoice type: "
        f"{invoice_type}"
    )


# ============================================================
# DEBUG DISPLAY
# ============================================================


def print_totals(
    totals: ParsedTotals,
) -> None:
    """
    Print parsed totals.
    """

    print("\n")
    print("=" * 80)
    print("PARSED TOTALS")
    print("=" * 80)

    print(
        f"Round Off       : "
        f"₹{totals.round_off:.2f}"
    )

    print(
        f"Total Amount    : "
        f"₹{totals.total_amount:.2f}"
    )

    print(
        f"Received Amount : "
        f"₹{totals.received_amount:.2f}"
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
        (
            project_root
            / "samples"
            / "Purchase Invoice 03.pdf"
        ),
        (
            project_root
            / "samples"
            / "Sale Invoice 03.pdf"
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
            # Determine invoice type.
            # ------------------------------------------------

            item_lines = (
                sections
                .item_table
                .lines
            )

            if (
                item_lines
                and item_lines[0]
                .strip()
                .upper()
                == "S.NO."
            ):

                invoice_type = "SALE"

            else:

                invoice_type = "PURCHASE"

            # ------------------------------------------------
            # Display raw totals section.
            # ------------------------------------------------

            print(
                "\nRAW TOTALS SECTION:"
            )

            print("-" * 80)

            for line in (
                sections
                .totals
                .lines
            ):

                print(
                    repr(line)
                )

            # ------------------------------------------------
            # Parse totals.
            # ------------------------------------------------

            totals = parse_totals(
                sections.totals,
                invoice_type,
            )

            print_totals(
                totals
            )

        except Exception as error:

            print(
                f"\n❌ Failed to parse "
                f"{pdf_file.name}"
            )

            print(
                f"Reason: {error}"
            )
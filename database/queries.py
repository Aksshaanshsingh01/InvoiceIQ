"""
InvoiceIQ - Database Query Layer

Provides read-only business queries over the SQLite database.

This layer sits above database.db and should contain:
    - retrieval queries
    - filtering
    - aggregations
    - reporting queries

It should NOT handle PDF extraction or insertion.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .db import (
    DEFAULT_DATABASE,
    get_connection,
)


# ============================================================
# Invoice Retrieval
# ============================================================


def get_invoice_by_id(
    invoice_id: int,
    database_path: str | Path = DEFAULT_DATABASE,
) -> sqlite3.Row | None:
    """Return one invoice by database ID."""

    with get_connection(database_path) as connection:

        return connection.execute(
            """
            SELECT *
            FROM invoices
            WHERE id = ?
            """,
            (invoice_id,),
        ).fetchone()


def get_invoice_by_number(
    invoice_number: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[sqlite3.Row]:
    """
    Return invoices matching an invoice number.

    Returns a list because invoice numbers are not globally
    unique across different sellers.
    """

    with get_connection(database_path) as connection:

        return connection.execute(
            """
            SELECT *
            FROM invoices
            WHERE invoice_number = ?
            ORDER BY id
            """,
            (invoice_number,),
        ).fetchall()


# ============================================================
# Seller / Buyer Queries
# ============================================================


def get_invoices_by_seller(
    seller: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[sqlite3.Row]:
    """Return invoices belonging to a seller."""

    with get_connection(database_path) as connection:

        return connection.execute(
            """
            SELECT *
            FROM invoices
            WHERE LOWER(seller) = LOWER(?)
            ORDER BY invoice_date, id
            """,
            (seller,),
        ).fetchall()


def get_invoices_by_buyer(
    buyer: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[sqlite3.Row]:
    """Return invoices belonging to a buyer."""

    with get_connection(database_path) as connection:

        return connection.execute(
            """
            SELECT *
            FROM invoices
            WHERE LOWER(buyer) = LOWER(?)
            ORDER BY invoice_date, id
            """,
            (buyer,),
        ).fetchall()


def get_invoices_by_seller_gstin(
    seller_gstin: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[sqlite3.Row]:
    """Return invoices using seller GSTIN."""

    with get_connection(database_path) as connection:

        return connection.execute(
            """
            SELECT *
            FROM invoices
            WHERE seller_gstin = ?
            ORDER BY invoice_date, id
            """,
            (seller_gstin,),
        ).fetchall()


# ============================================================
# Invoice Type
# ============================================================


def get_invoices_by_type(
    invoice_type: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[sqlite3.Row]:
    """
    Return invoices by type.

    Examples:
        PURCHASE
        SALE
    """

    normalized_type = invoice_type.upper()

    with get_connection(database_path) as connection:

        return connection.execute(
            """
            SELECT *
            FROM invoices
            WHERE invoice_type = ?
            ORDER BY invoice_date, id
            """,
            (normalized_type,),
        ).fetchall()


# ============================================================
# Date Range
# ============================================================


def get_invoices_by_date_range(
    start_date: str,
    end_date: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[sqlite3.Row]:
    """
    Return invoices between two dates.

    Dates are expected in:

        DD/MM/YYYY

    Because the current extraction model stores invoice dates
    in that format, comparison is normalized inside SQLite.
    """

    with get_connection(database_path) as connection:

        return connection.execute(
            """
            SELECT *
            FROM invoices
            WHERE
                substr(invoice_date, 7, 4)
                || substr(invoice_date, 4, 2)
                || substr(invoice_date, 1, 2)
                BETWEEN
                substr(?, 7, 4)
                || substr(?, 4, 2)
                || substr(?, 1, 2)
                AND
                substr(?, 7, 4)
                || substr(?, 4, 2)
                || substr(?, 1, 2)
            ORDER BY
                substr(invoice_date, 7, 4),
                substr(invoice_date, 4, 2),
                substr(invoice_date, 1, 2),
                id
            """,
            (
                start_date,
                start_date,
                start_date,
                end_date,
                end_date,
                end_date,
            ),
        ).fetchall()


# ============================================================
# Payment Queries
# ============================================================


def get_unpaid_invoices(
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[sqlite3.Row]:
    """
    Return purchase invoices whose received amount is less
    than the invoice total.

    Payment tracking is currently supported for purchase
    invoices because the current purchase layout provides
    a Received Amount field. Sales invoices are not treated
    as unpaid when payment information is not tracked.
    """

    with get_connection(database_path) as connection:

        return connection.execute(
            """
            SELECT *
            FROM invoices
            WHERE invoice_type = 'PURCHASE'
              AND received_amount < total_amount
            ORDER BY invoice_date, id
            """
        ).fetchall()


def get_fully_paid_invoices(
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[sqlite3.Row]:
    """
    Return purchase invoices whose full amount was received.

    Sales invoices are excluded because payment tracking is
    not currently treated as a supported sales-side field.
    """

    with get_connection(database_path) as connection:

        return connection.execute(
            """
            SELECT *
            FROM invoices
            WHERE invoice_type = 'PURCHASE'
              AND received_amount >= total_amount
            ORDER BY invoice_date, id
            """
        ).fetchall()


# ============================================================
# Item Search
# ============================================================


def search_items(material_name, database_path=DEFAULT_DATABASE):
    """
    Search invoice items by material name.

    Matching is:
    - case-insensitive
    - whitespace-insensitive

    Example:
        "sawdust" matches:
        "Sawdust Briquette"
        "Sawdust Premium Pellets"
        "SAW DUST PELLETS PREMIUM"
        "SAW DUST BRIQUETTE PREMIUM"
    """

    search_term = material_name.lower().replace(" ", "")

    with get_connection(database_path) as connection:
        return connection.execute(
            """
            SELECT
                items.*,
                invoices.invoice_number,
                invoices.invoice_type,
                invoices.invoice_date,
                invoices.seller,
                invoices.buyer
            FROM items
            JOIN invoices
                ON invoices.id = items.invoice_id
            WHERE REPLACE(
                LOWER(items.material_name),
                ' ',
                ''
            ) LIKE ?
            ORDER BY
                invoices.invoice_date,
                invoices.id,
                items.item_number
            """,
            (f"%{search_term}%",),
        ).fetchall()


def get_items_by_hsn(
    hsn: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[sqlite3.Row]:
    """Return all invoice items using a particular HSN."""

    with get_connection(database_path) as connection:

        return connection.execute(
            """
            SELECT
                items.*,
                invoices.invoice_number,
                invoices.invoice_type,
                invoices.invoice_date,
                invoices.seller,
                invoices.buyer
            FROM items

            JOIN invoices
                ON invoices.id = items.invoice_id

            WHERE items.hsn = ?

            ORDER BY
                invoices.invoice_date,
                invoices.id,
                items.item_number
            """,
            (hsn,),
        ).fetchall()


# ============================================================
# Financial Aggregations
# ============================================================


def get_total_sales(
    database_path: str | Path = DEFAULT_DATABASE,
) -> float:
    """Return total value of all sales invoices."""

    with get_connection(database_path) as connection:

        value = connection.execute(
            """
            SELECT COALESCE(
                SUM(total_amount),
                0
            )
            FROM invoices
            WHERE invoice_type = 'SALE'
            """
        ).fetchone()[0]

    return float(value)


def get_total_purchases(
    database_path: str | Path = DEFAULT_DATABASE,
) -> float:
    """Return total value of all purchase invoices."""

    with get_connection(database_path) as connection:

        value = connection.execute(
            """
            SELECT COALESCE(
                SUM(total_amount),
                0
            )
            FROM invoices
            WHERE invoice_type = 'PURCHASE'
            """
        ).fetchone()[0]

    return float(value)


def get_total_tax(
    database_path: str | Path = DEFAULT_DATABASE,
) -> float:
    """Return total tax across all invoices."""

    with get_connection(database_path) as connection:

        value = connection.execute(
            """
            SELECT COALESCE(
                SUM(total_tax),
                0
            )
            FROM invoices
            """
        ).fetchone()[0]

    return float(value)


# ============================================================
# Tax Summary
# ============================================================


def get_tax_summary(
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[sqlite3.Row]:
    """
    Return tax totals grouped by tax type.

    Example:

        CGST
        SGST
        IGST
    """

    with get_connection(database_path) as connection:

        return connection.execute(
            """
            SELECT
                tax_type,
                COUNT(*) AS tax_count,
                SUM(amount) AS total_amount
            FROM taxes
            GROUP BY tax_type
            ORDER BY tax_type
            """
        ).fetchall()


# ============================================================
# Seller Summary
# ============================================================


def get_seller_summary(
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[sqlite3.Row]:
    """
    Return invoice count and total value grouped by seller.
    """

    with get_connection(database_path) as connection:

        return connection.execute(
            """
            SELECT
                seller,
                seller_gstin,
                COUNT(*) AS invoice_count,
                SUM(total_amount) AS total_amount
            FROM invoices
            GROUP BY
                seller,
                seller_gstin
            ORDER BY total_amount DESC
            """
        ).fetchall()


# ============================================================
# Database-wide Statistics
# ============================================================


def get_financial_summary(
    database_path: str | Path = DEFAULT_DATABASE,
) -> dict[str, float]:
    """
    Return high-level financial statistics.
    """

    return {
        "sales": get_total_sales(
            database_path
        ),
        "purchases": get_total_purchases(
            database_path
        ),
        "tax": get_total_tax(
            database_path
        ),
    }


# ============================================================
# COMMAND LINE TEST
# ============================================================


if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("InvoiceIQ Database Query Layer")
    print("=" * 60)

    summary = get_financial_summary()

    print(
        f"\nTotal Sales     : "
        f"â‚¹{summary['sales']:.2f}"
    )

    print(
        f"Total Purchases : "
        f"â‚¹{summary['purchases']:.2f}"
    )

    print(
        f"Total Tax       : "
        f"â‚¹{summary['tax']:.2f}"
    )

    print("\n" + "=" * 60)

"""
InvoiceIQ - Firestore Query Layer

Read-only business queries over Firestore.

The public function names and return shapes are kept compatible with
InvoiceIQ's existing API and analytics layers.

Firestore stores items and taxes inside each invoice document, so joins
and SQL aggregations are replaced by in-Python filtering/aggregation.
For the current portfolio/demo scale this keeps the implementation
simple and avoids unnecessary Firestore composite indexes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .db import (
    DEFAULT_DATABASE,
    get_all_invoices,
    get_invoice_by_id as _get_invoice_by_id,
)


# ============================================================
# Helpers
# ============================================================

def _date_key(value: str | None) -> str:
    """Convert DD/MM/YYYY to YYYYMMDD for reliable sorting/comparison."""
    if not value:
        return ""

    try:
        day, month, year = value.split("/")
        return f"{year}{month}{day}"
    except ValueError:
        return value


def _sort_invoices(
    invoices: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(
        invoices,
        key=lambda invoice: (
            _date_key(invoice.get("invoice_date")),
            str(invoice.get("id", "")),
        ),
    )


def _copy_invoice(invoice: dict[str, Any]) -> dict[str, Any]:
    """
    Return a normal dictionary.

    This mirrors dict(sqlite3.Row) from the old implementation.
    """
    return dict(invoice)


def _all_invoices(
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    return [
        _copy_invoice(invoice)
        for invoice in get_all_invoices(database_path)
    ]


# ============================================================
# Invoice Retrieval
# ============================================================

def get_invoice_by_id(
    invoice_id: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> dict[str, Any] | None:
    """Return one invoice by Firestore document ID."""
    invoice = _get_invoice_by_id(
        str(invoice_id),
        database_path,
    )

    if invoice is None:
        return None

    return _copy_invoice(invoice)


def get_invoice_by_number(
    invoice_number: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    """
    Return invoices matching an invoice number.

    Returns a list because invoice numbers are not globally unique.
    """
    term = (invoice_number or "").strip().lower()

    invoices = [
        invoice
        for invoice in _all_invoices(database_path)
        if str(
            invoice.get("invoice_number") or ""
        ).strip().lower() == term
    ]

    return _sort_invoices(invoices)


# ============================================================
# Seller / Buyer Queries
# ============================================================

def get_invoices_by_seller(
    seller: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    """Return invoices belonging to a seller, case-insensitively."""
    term = (seller or "").strip().lower()

    invoices = [
        invoice
        for invoice in _all_invoices(database_path)
        if str(invoice.get("seller") or "").strip().lower() == term
    ]

    return _sort_invoices(invoices)


def get_invoices_by_buyer(
    buyer: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    """Return invoices belonging to a buyer, case-insensitively."""
    term = (buyer or "").strip().lower()

    invoices = [
        invoice
        for invoice in _all_invoices(database_path)
        if str(invoice.get("buyer") or "").strip().lower() == term
    ]

    return _sort_invoices(invoices)


def get_invoices_by_seller_gstin(
    seller_gstin: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    """Return invoices using a seller GSTIN."""
    term = (seller_gstin or "").strip().upper()

    invoices = [
        invoice
        for invoice in _all_invoices(database_path)
        if str(
            invoice.get("seller_gstin") or ""
        ).strip().upper() == term
    ]

    return _sort_invoices(invoices)


# ============================================================
# Invoice Type
# ============================================================

def get_invoices_by_type(
    invoice_type: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    """Return invoices by type: SALE or PURCHASE."""
    normalized_type = (invoice_type or "").upper()

    invoices = [
        invoice
        for invoice in _all_invoices(database_path)
        if invoice.get("invoice_type") == normalized_type
    ]

    return _sort_invoices(invoices)


# ============================================================
# Date Range
# ============================================================

def get_invoices_by_date_range(
    start_date: str,
    end_date: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    """
    Return invoices between two DD/MM/YYYY dates, inclusive.
    """
    start_key = _date_key(start_date)
    end_key = _date_key(end_date)

    invoices = [
        invoice
        for invoice in _all_invoices(database_path)
        if start_key
        <= _date_key(invoice.get("invoice_date"))
        <= end_key
    ]

    return _sort_invoices(invoices)


# ============================================================
# Payment Queries
# ============================================================

def get_unpaid_invoices(
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    """
    Return purchase invoices whose received amount is less
    than the invoice total.

    Sales invoices are excluded because InvoiceIQ currently
    tracks payment status only on purchases.
    """
    invoices = [
        invoice
        for invoice in _all_invoices(database_path)
        if invoice.get("invoice_type") == "PURCHASE"
        and float(invoice.get("received_amount") or 0)
        < float(invoice.get("total_amount") or 0)
    ]

    return _sort_invoices(invoices)


def get_fully_paid_invoices(
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    """
    Return purchase invoices whose full amount was received.
    """
    invoices = [
        invoice
        for invoice in _all_invoices(database_path)
        if invoice.get("invoice_type") == "PURCHASE"
        and float(invoice.get("received_amount") or 0)
        >= float(invoice.get("total_amount") or 0)
    ]

    return _sort_invoices(invoices)


# ============================================================
# Item Search
# ============================================================

def search_items(
    material_name: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    """
    Search invoice items by material name.

    Matching is:
        - case-insensitive
        - whitespace-insensitive

    The returned item includes invoice metadata, matching the
    old SQL JOIN result.
    """
    search_term = (
        material_name or ""
    ).lower().replace(" ", "")

    results = []

    for invoice in _all_invoices(database_path):
        for item in invoice.get("items") or []:
            normalized_material = (
                str(item.get("material_name") or "")
                .lower()
                .replace(" ", "")
            )

            if search_term not in normalized_material:
                continue

            result = dict(item)

            result.update(
                {
                    "invoice_number": invoice.get("invoice_number"),
                    "invoice_type": invoice.get("invoice_type"),
                    "invoice_date": invoice.get("invoice_date"),
                    "seller": invoice.get("seller"),
                    "buyer": invoice.get("buyer"),
                }
            )

            results.append(result)

    return sorted(
        results,
        key=lambda item: (
            _date_key(item.get("invoice_date")),
            str(item.get("invoice_id", "")),
            int(item.get("item_number", 0)),
        ),
    )


def get_items_by_hsn(
    hsn: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    """Return all invoice items using a particular HSN."""
    normalized_hsn = str(hsn or "").strip()

    results = []

    for invoice in _all_invoices(database_path):
        for item in invoice.get("items") or []:
            if str(item.get("hsn") or "").strip() != normalized_hsn:
                continue

            result = dict(item)

            result.update(
                {
                    "invoice_number": invoice.get("invoice_number"),
                    "invoice_type": invoice.get("invoice_type"),
                    "invoice_date": invoice.get("invoice_date"),
                    "seller": invoice.get("seller"),
                    "buyer": invoice.get("buyer"),
                }
            )

            results.append(result)

    return sorted(
        results,
        key=lambda item: (
            _date_key(item.get("invoice_date")),
            str(item.get("invoice_id", "")),
            int(item.get("item_number", 0)),
        ),
    )


# ============================================================
# Financial Aggregations
# ============================================================

def get_total_sales(
    database_path: str | Path = DEFAULT_DATABASE,
) -> float:
    """Return total value of all sales invoices."""
    return float(
        sum(
            float(invoice.get("total_amount") or 0)
            for invoice in _all_invoices(database_path)
            if invoice.get("invoice_type") == "SALE"
        )
    )


def get_total_purchases(
    database_path: str | Path = DEFAULT_DATABASE,
) -> float:
    """Return total value of all purchase invoices."""
    return float(
        sum(
            float(invoice.get("total_amount") or 0)
            for invoice in _all_invoices(database_path)
            if invoice.get("invoice_type") == "PURCHASE"
        )
    )


def get_total_tax(
    database_path: str | Path = DEFAULT_DATABASE,
) -> float:
    """Return total tax across all invoices."""
    return float(
        sum(
            float(invoice.get("total_tax") or 0)
            for invoice in _all_invoices(database_path)
        )
    )


# ============================================================
# Tax Summary
# ============================================================

def get_tax_summary(
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    """
    Return tax totals grouped by tax type.

    Example:
        CGST
        SGST
        IGST
    """
    grouped: dict[str, dict[str, Any]] = {}

    for invoice in _all_invoices(database_path):
        for tax in invoice.get("taxes") or []:
            tax_type = str(
                tax.get("tax_type") or ""
            ).upper()

            if tax_type not in grouped:
                grouped[tax_type] = {
                    "tax_type": tax_type,
                    "tax_count": 0,
                    "total_amount": 0.0,
                }

            grouped[tax_type]["tax_count"] += 1
            grouped[tax_type]["total_amount"] += float(
                tax.get("amount") or 0
            )

    return [
        {
            "tax_type": row["tax_type"],
            "tax_count": row["tax_count"],
            "total_amount": round(
                row["total_amount"],
                2,
            ),
        }
        for row in sorted(
            grouped.values(),
            key=lambda row: row["tax_type"],
        )
    ]


# ============================================================
# Seller Summary
# ============================================================

def get_seller_summary(
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    """Return invoice count and total value grouped by seller."""
    grouped: dict[tuple[str, str], dict[str, Any]] = {}

    for invoice in _all_invoices(database_path):
        key = (
            invoice.get("seller") or "",
            invoice.get("seller_gstin") or "",
        )

        if key not in grouped:
            grouped[key] = {
                "seller": key[0],
                "seller_gstin": key[1],
                "invoice_count": 0,
                "total_amount": 0.0,
            }

        grouped[key]["invoice_count"] += 1
        grouped[key]["total_amount"] += float(
            invoice.get("total_amount") or 0
        )

    results = [
        {
            "seller": row["seller"],
            "seller_gstin": row["seller_gstin"],
            "invoice_count": row["invoice_count"],
            "total_amount": round(
                row["total_amount"],
                2,
            ),
        }
        for row in grouped.values()
    ]

    return sorted(
        results,
        key=lambda row: row["total_amount"],
        reverse=True,
    )


# ============================================================
# Database-wide Statistics
# ============================================================

def get_financial_summary(
    database_path: str | Path = DEFAULT_DATABASE,
) -> dict[str, float]:
    """Return high-level financial statistics."""
    return {
        "sales": get_total_sales(database_path),
        "purchases": get_total_purchases(database_path),
        "tax": get_total_tax(database_path),
    }


# ============================================================
# COMMAND LINE TEST
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("InvoiceIQ Firestore Query Layer")
    print("=" * 60)

    summary = get_financial_summary()

    print(
        f"\nTotal Sales     : ₹{summary['sales']:.2f}"
    )

    print(
        f"Total Purchases : ₹{summary['purchases']:.2f}"
    )

    print(
        f"Total Tax       : ₹{summary['tax']:.2f}"
    )

    print("\n" + "=" * 60)

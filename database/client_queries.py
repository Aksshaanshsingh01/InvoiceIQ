"""Client-level search and aggregation queries for InvoiceIQ."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .db import DEFAULT_DATABASE, get_connection


def _invoice_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def get_client_summary(
    gstin: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> dict | None:
    """Return client identity, invoice history, and aggregated metrics."""
    gstin = (gstin or "").strip()
    if not gstin:
        return None

    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM invoices
            WHERE seller_gstin = ?
               OR buyer_gstin = ?
            ORDER BY invoice_date, id
            """,
            (gstin, gstin),
        ).fetchall()

    if not rows:
        return None

    names = []
    for row in rows:
        if row["seller_gstin"] == gstin and row["seller"]:
            names.append(row["seller"])
        if row["buyer_gstin"] == gstin and row["buyer"]:
            names.append(row["buyer"])

    client_name = names[0] if names else gstin
    invoices = [_invoice_dict(row) for row in rows]

    return {
        "name": client_name,
        "gstin": gstin,
        "invoice_count": len(invoices),
        "sales_count": sum(1 for row in invoices if row["invoice_type"] == "SALE"),
        "purchase_count": sum(1 for row in invoices if row["invoice_type"] == "PURCHASE"),
        "total_value": round(sum(float(row["total_amount"] or 0) for row in invoices), 2),
        "sales_value": round(sum(float(row["total_amount"] or 0) for row in invoices if row["invoice_type"] == "SALE"), 2),
        "purchase_value": round(sum(float(row["total_amount"] or 0) for row in invoices if row["invoice_type"] == "PURCHASE"), 2),
        "total_tax": round(sum(float(row["total_tax"] or 0) for row in invoices), 2),
        "invoices": invoices,
    }


def search_clients(
    search_term: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict]:
    """
    Unified search by client name, GSTIN, or invoice number.

    Name/GSTIN searches return the complete invoice history for the
    matching client. Invoice-number searches return only matching
    invoices so unrelated client history is not shown.
    """
    term = (search_term or "").strip()
    if not term:
        return []

    pattern = f"%{term}%"

    with get_connection(database_path) as connection:

        # Invoice number has priority when it matches.
        invoice_rows = connection.execute(
            """
            SELECT *
            FROM invoices
            WHERE invoice_number LIKE ? COLLATE NOCASE
            ORDER BY invoice_date, id
            """,
            (pattern,),
        ).fetchall()

        if invoice_rows:
            grouped = {}

            for row in invoice_rows:
                invoice = _invoice_dict(row)

                # Use the seller as the client identity for invoice-number
                # searches, which is consistent for both SALE and PURCHASE
                # invoices in the current application.
                gstin = (
                    invoice.get("seller_gstin")
                    or invoice.get("buyer_gstin")
                )

                if not gstin:
                    continue

                if gstin not in grouped:
                    name = (
                        invoice.get("seller")
                        if invoice.get("seller_gstin") == gstin
                        else invoice.get("buyer")
                    ) or gstin

                    grouped[gstin] = {
                        "name": name,
                        "gstin": gstin,
                        "invoice_count": 0,
                        "sales_count": 0,
                        "purchase_count": 0,
                        "total_value": 0.0,
                        "sales_value": 0.0,
                        "purchase_value": 0.0,
                        "total_tax": 0.0,
                        "invoices": [],
                    }

                result = grouped[gstin]
                result["invoices"].append(invoice)

                amount = float(invoice.get("total_amount") or 0)
                tax = float(invoice.get("total_tax") or 0)

                result["invoice_count"] += 1
                result["total_value"] += amount
                result["total_tax"] += tax

                if invoice.get("invoice_type") == "SALE":
                    result["sales_count"] += 1
                    result["sales_value"] += amount
                elif invoice.get("invoice_type") == "PURCHASE":
                    result["purchase_count"] += 1
                    result["purchase_value"] += amount

            results = list(grouped.values())

            for result in results:
                result["total_value"] = round(result["total_value"], 2)
                result["sales_value"] = round(result["sales_value"], 2)
                result["purchase_value"] = round(result["purchase_value"], 2)
                result["total_tax"] = round(result["total_tax"], 2)

            return results

        # No invoice-number match: search client name or GSTIN.
        candidates = connection.execute(
            """
            SELECT DISTINCT seller_gstin AS gstin
            FROM invoices
            WHERE seller_gstin IS NOT NULL
              AND (
                    seller LIKE ? COLLATE NOCASE
                    OR seller_gstin LIKE ? COLLATE NOCASE
              )

            UNION

            SELECT DISTINCT buyer_gstin AS gstin
            FROM invoices
            WHERE buyer_gstin IS NOT NULL
              AND (
                    buyer LIKE ? COLLATE NOCASE
                    OR buyer_gstin LIKE ? COLLATE NOCASE
              )
            """,
            (pattern, pattern, pattern, pattern),
        ).fetchall()

    results = []

    for candidate in candidates:
        summary = get_client_summary(
            candidate["gstin"],
            database_path,
        )
        if summary:
            results.append(summary)

    results.sort(
        key=lambda item: (
            -item["invoice_count"],
            item["name"].lower(),
        )
    )

    return results


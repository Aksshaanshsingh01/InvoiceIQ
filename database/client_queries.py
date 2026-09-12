"""
InvoiceIQ - Firestore Client Query Layer

Provides client-level search and aggregation over Firestore.

Search supports:
    - client name
    - GSTIN
    - invoice number

A GSTIN is treated as the client-level identifier. All invoices where
that GSTIN appears as either seller or buyer are included in the client's
history.

Invoice-number searches have priority and return only the matching
invoice(s), grouped by the relevant client GSTIN.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .db import DEFAULT_DATABASE, get_all_invoices


# ============================================================
# Helpers
# ============================================================

def _date_key(value: str | None) -> str:
    """Convert DD/MM/YYYY into YYYYMMDD for sorting."""
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


def _invoice_dict(invoice: dict[str, Any]) -> dict[str, Any]:
    """Return a normal dictionary, matching the old sqlite Row behavior."""
    return dict(invoice)


def _all_invoices(
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    return [
        _invoice_dict(invoice)
        for invoice in get_all_invoices(database_path)
    ]


# ============================================================
# Client Summary
# ============================================================

def get_client_summary(
    gstin: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> dict[str, Any] | None:
    """
    Return client identity, invoice history, and aggregated metrics.

    A client is identified by GSTIN. The GSTIN can occur as either:
        seller_gstin
        buyer_gstin
    """
    gstin = (gstin or "").strip()

    if not gstin:
        return None

    invoices = [
        invoice
        for invoice in _all_invoices(database_path)
        if str(invoice.get("seller_gstin") or "").strip() == gstin
        or str(invoice.get("buyer_gstin") or "").strip() == gstin
    ]

    if not invoices:
        return None

    invoices = _sort_invoices(invoices)

    names: list[str] = []

    for invoice in invoices:
        if (
            invoice.get("seller_gstin") == gstin
            and invoice.get("seller")
        ):
            names.append(str(invoice["seller"]))

        if (
            invoice.get("buyer_gstin") == gstin
            and invoice.get("buyer")
        ):
            names.append(str(invoice["buyer"]))

    client_name = names[0] if names else gstin

    sales = [
        invoice
        for invoice in invoices
        if invoice.get("invoice_type") == "SALE"
    ]

    purchases = [
        invoice
        for invoice in invoices
        if invoice.get("invoice_type") == "PURCHASE"
    ]

    sales_value = sum(
        float(invoice.get("total_amount") or 0)
        for invoice in sales
    )

    purchase_value = sum(
        float(invoice.get("total_amount") or 0)
        for invoice in purchases
    )

    total_value = sum(
        float(invoice.get("total_amount") or 0)
        for invoice in invoices
    )

    total_tax = sum(
        float(invoice.get("total_tax") or 0)
        for invoice in invoices
    )

    return {
        "name": client_name,
        "gstin": gstin,
        "invoice_count": len(invoices),
        "sales_count": len(sales),
        "purchase_count": len(purchases),
        "total_value": round(total_value, 2),
        "sales_value": round(sales_value, 2),
        "purchase_value": round(purchase_value, 2),
        "total_tax": round(total_tax, 2),
        "invoices": [
            _invoice_dict(invoice)
            for invoice in invoices
        ],
    }


# ============================================================
# Unified Client / GSTIN / Invoice Search
# ============================================================

def search_clients(
    search_term: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    """
    Unified search by:

        1. Invoice number
        2. Client name
        3. GSTIN

    Invoice-number matches have priority.

    Example:
        search_clients("YGEPL/26-27/4")

    returns only invoices matching that invoice number.

    Example:
        search_clients("Yara Green Energy")

    returns the complete history for the matching GSTIN(s).
    """
    term = (search_term or "").strip()

    if not term:
        return []

    normalized = term.lower()

    all_invoices = _all_invoices(database_path)

    # --------------------------------------------------------
    # 1. Invoice number search
    # --------------------------------------------------------

    invoice_matches = [
        invoice
        for invoice in all_invoices
        if normalized
        in str(
            invoice.get("invoice_number") or ""
        ).lower()
    ]

    if invoice_matches:

        grouped: dict[str, dict[str, Any]] = {}

        for invoice in _sort_invoices(invoice_matches):

            seller_gstin = str(
                invoice.get("seller_gstin") or ""
            ).strip()

            buyer_gstin = str(
                invoice.get("buyer_gstin") or ""
            ).strip()

            # Prefer seller GSTIN for the group identity because
            # this mirrors InvoiceIQ's invoice-centric identity.
            gstin = seller_gstin or buyer_gstin

            if not gstin:
                continue

            if gstin not in grouped:

                if seller_gstin == gstin:
                    client_name = (
                        invoice.get("seller")
                        or gstin
                    )
                else:
                    client_name = (
                        invoice.get("buyer")
                        or gstin
                    )

                grouped[gstin] = {
                    "name": client_name,
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

            result["invoices"].append(
                _invoice_dict(invoice)
            )

            amount = float(
                invoice.get("total_amount") or 0
            )

            tax = float(
                invoice.get("total_tax") or 0
            )

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
            result["total_value"] = round(
                result["total_value"],
                2,
            )

            result["sales_value"] = round(
                result["sales_value"],
                2,
            )

            result["purchase_value"] = round(
                result["purchase_value"],
                2,
            )

            result["total_tax"] = round(
                result["total_tax"],
                2,
            )

        return results

    # --------------------------------------------------------
    # 2. Client name / GSTIN search
    # --------------------------------------------------------

    matching_gstins: set[str] = set()

    for invoice in all_invoices:

        seller = str(
            invoice.get("seller") or ""
        )

        buyer = str(
            invoice.get("buyer") or ""
        )

        seller_gstin = str(
            invoice.get("seller_gstin") or ""
        )

        buyer_gstin = str(
            invoice.get("buyer_gstin") or ""
        )

        if (
            normalized in seller.lower()
            or normalized in seller_gstin.lower()
        ):
            if seller_gstin:
                matching_gstins.add(
                    seller_gstin
                )

        if (
            normalized in buyer.lower()
            or normalized in buyer_gstin.lower()
        ):
            if buyer_gstin:
                matching_gstins.add(
                    buyer_gstin
                )

    results = []

    for gstin in matching_gstins:

        summary = get_client_summary(
            gstin,
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


# ============================================================
# Command Line Test
# ============================================================

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("InvoiceIQ Firestore Client Query Layer")
    print("=" * 60)

    invoices = _all_invoices()

    print(
        f"\nInvoices available: {len(invoices)}"
    )

    if invoices:

        first_invoice = invoices[0]

        seller_gstin = (
            first_invoice.get("seller_gstin")
        )

        buyer_gstin = (
            first_invoice.get("buyer_gstin")
        )

        if seller_gstin:

            result = search_clients(
                seller_gstin
            )

            print(
                f"\nGSTIN search: {seller_gstin}"
            )
            print(
                f"Clients found: {len(result)}"
            )

            for client in result:
                print(
                    f"  {client['name']} | "
                    f"{client['gstin']} | "
                    f"{client['invoice_count']} invoices"
                )

        invoice_number = (
            first_invoice.get("invoice_number")
        )

        if invoice_number:

            result = search_clients(
                invoice_number
            )

            print(
                f"\nInvoice search: {invoice_number}"
            )
            print(
                f"Matches: {sum(len(item['invoices']) for item in result)}"
            )

    print("\n" + "=" * 60)

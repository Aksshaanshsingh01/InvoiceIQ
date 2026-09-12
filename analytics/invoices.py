"""
Invoice-level analytics for InvoiceIQ.
"""

from database.queries import (
    get_invoices_by_type,
    get_unpaid_invoices,
    get_fully_paid_invoices,
)


def get_invoice_metrics(database_path):
    """
    Return invoice-level metrics for the InvoiceIQ dashboard.
    """

    sales = get_invoices_by_type(
        "SALE",
        database_path,
    )

    purchases = get_invoices_by_type(
        "PURCHASE",
        database_path,
    )

    unpaid = get_unpaid_invoices(
        database_path,
    )

    paid = get_fully_paid_invoices(
        database_path,
    )

    return {
        "total_invoice_count": len(sales) + len(purchases),
        "sales_invoice_count": len(sales),
        "purchase_invoice_count": len(purchases),
        "paid_invoice_count": len(paid),
        "unpaid_invoice_count": len(unpaid),
    }

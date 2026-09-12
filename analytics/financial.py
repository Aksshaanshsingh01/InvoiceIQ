"""
Financial analytics for InvoiceIQ.
"""

from database.queries import (
    get_total_sales,
    get_total_purchases,
    get_total_tax,
    get_unpaid_invoices,
    get_fully_paid_invoices,
)


def get_financial_metrics(database_path):
    """
    Return the main financial metrics for the dashboard.
    """

    unpaid_invoices = get_unpaid_invoices(database_path)
    paid_invoices = get_fully_paid_invoices(database_path)

    total_sales = get_total_sales(database_path)
    total_purchases = get_total_purchases(database_path)
    total_tax = get_total_tax(database_path)

    outstanding_amount = sum(
        float(invoice["total_amount"] or 0)
        - float(invoice["received_amount"] or 0)
        for invoice in unpaid_invoices
    )

    return {
        "total_sales": total_sales,
        "total_purchases": total_purchases,
        "total_tax": total_tax,
        "outstanding_amount": outstanding_amount,
        "paid_invoice_count": len(paid_invoices),
        "unpaid_invoice_count": len(unpaid_invoices),
    }

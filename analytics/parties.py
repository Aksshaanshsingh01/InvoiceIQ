"""
Party analytics for InvoiceIQ.

Provides supplier and customer summaries.
"""

from database.queries import get_invoices_by_type


def get_supplier_metrics(database_path):
    """
    Return supplier-level purchase summaries.
    """

    purchase_invoices = get_invoices_by_type(
        "PURCHASE",
        database_path,
    )

    suppliers = {}

    for invoice in purchase_invoices:
        supplier = invoice["seller"]

        if supplier not in suppliers:
            suppliers[supplier] = {
                "supplier": supplier,
                "invoice_count": 0,
                "total_amount": 0.0,
            }

        suppliers[supplier]["invoice_count"] += 1
        suppliers[supplier]["total_amount"] += float(
            invoice["total_amount"] or 0
        )

    supplier_list = sorted(
        suppliers.values(),
        key=lambda item: item["total_amount"],
        reverse=True,
    )

    return {
        "supplier_count": len(supplier_list),
        "suppliers": supplier_list,
    }


def get_customer_metrics(database_path):
    """
    Return customer-level sales summaries.
    """

    sale_invoices = get_invoices_by_type(
        "SALE",
        database_path,
    )

    customers = {}

    for invoice in sale_invoices:
        customer = invoice["buyer"]

        if customer not in customers:
            customers[customer] = {
                "customer": customer,
                "invoice_count": 0,
                "total_amount": 0.0,
            }

        customers[customer]["invoice_count"] += 1
        customers[customer]["total_amount"] += float(
            invoice["total_amount"] or 0
        )

    customer_list = sorted(
        customers.values(),
        key=lambda item: item["total_amount"],
        reverse=True,
    )

    return {
        "customer_count": len(customer_list),
        "customers": customer_list,
    }


def get_party_metrics(database_path):
    """
    Return combined supplier and customer analytics.
    """

    return {
        "suppliers": get_supplier_metrics(database_path),
        "customers": get_customer_metrics(database_path),
    }

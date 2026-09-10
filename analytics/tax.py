"""
Tax analytics for InvoiceIQ.
"""

from database.queries import get_tax_summary


def get_tax_metrics(database_path):
    """
    Return tax-related metrics for the InvoiceIQ dashboard.
    """

    tax_summary = get_tax_summary(database_path)

    tax_by_type = {
        row["tax_type"]: float(row["total_amount"] or 0)
        for row in tax_summary
    }

    cgst = tax_by_type.get("CGST", 0.0)
    sgst = tax_by_type.get("SGST", 0.0)
    igst = tax_by_type.get("IGST", 0.0)

    return {
        "cgst": cgst,
        "sgst": sgst,
        "igst": igst,
        "total_tax": cgst + sgst + igst,
    }
from analytics.financial import get_financial_metrics
from analytics.invoices import get_invoice_metrics
from analytics.tax import get_tax_metrics
from analytics.parties import get_party_metrics


def get_dashboard_metrics(database_path):
    financial = get_financial_metrics(database_path)
    invoices = get_invoice_metrics(database_path)
    tax = get_tax_metrics(database_path)
    parties = get_party_metrics(database_path)

    return {
        "financial": financial,
        "invoices": invoices,
        "tax": tax,
        "parties": parties,
    }
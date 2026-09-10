import requests

API_BASE_URL = "http://127.0.0.1:8000"


def get_dashboard():
    response = requests.get(f"{API_BASE_URL}/dashboard", timeout=10)
    response.raise_for_status()
    return response.json()


def get_invoices():
    response = requests.get(f"{API_BASE_URL}/invoices", timeout=10)
    response.raise_for_status()
    return response.json()


def get_invoice(invoice_id):
    response = requests.get(f"{API_BASE_URL}/invoices/{invoice_id}", timeout=10)
    response.raise_for_status()
    return response.json()


def search_invoices(
    invoice_number=None,
    seller=None,
    buyer=None,
    seller_gstin=None,
    invoice_type=None,
    start_date=None,
    end_date=None,
):
    params = {}
    if invoice_number:
        params["invoice_number"] = invoice_number
    if seller:
        params["seller"] = seller
    if buyer:
        params["buyer"] = buyer
    if seller_gstin:
        params["seller_gstin"] = seller_gstin
    if invoice_type:
        params["invoice_type"] = invoice_type
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    response = requests.get(
        f"{API_BASE_URL}/invoices/search",
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def search_clients(query):
    response = requests.get(
        f"{API_BASE_URL}/clients/search",
        params={"q": query},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def upload_invoice(file_name, file_content):
    response = requests.post(
        f"{API_BASE_URL}/invoices/upload",
        files={"file": (file_name, file_content, "application/pdf")},
        timeout=60,
    )
    return response

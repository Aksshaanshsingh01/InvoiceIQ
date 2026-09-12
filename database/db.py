"""
InvoiceIQ - Firestore Database Layer

Firestore replacement for the original SQLite database layer.

Document structure:

    invoices/
        {invoice_id}
            invoice metadata
            items: [...]
            taxes: [...]

Invoice identity:
    invoice_number
    + invoice_type
    + invoice_date
    + seller_gstin
    + buyer_gstin

The deterministic document ID is a SHA-256 hash of that identity.
This preserves InvoiceIQ's current duplicate-invoice rule.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import firebase_admin
from firebase_admin import credentials, firestore
from google.api_core.exceptions import AlreadyExists

from extraction.invoice_extractor import Invoice
from dotenv import load_dotenv


load_dotenv()

# Kept for compatibility with the rest of InvoiceIQ.
# Firestore does not use a local database path.
DEFAULT_DATABASE = "firestore"


FIRESTORE_COLLECTION = os.getenv(
    "INVOICEIQ_FIRESTORE_COLLECTION",
    "invoices",
)

# ============================================================
# FIREBASE INITIALIZATION
# ============================================================

def _initialize_firebase() -> None:
    """Initialize Firebase Admin SDK exactly once."""

    try:
        firebase_admin.get_app()
        return
    except ValueError:
        pass

    service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT")

    if service_account_path:
        credential_path = Path(service_account_path).expanduser()

        if not credential_path.is_absolute():
            project_root = Path(__file__).resolve().parent.parent
            credential_path = project_root / credential_path

        if not credential_path.is_file():
            raise FileNotFoundError(
                "Firebase service-account file was not found: "
                f"{credential_path}"
            )

        cred = credentials.Certificate(str(credential_path))
        firebase_admin.initialize_app(cred)

    else:
        # Google Cloud / Cloud Run:
        # use Application Default Credentials.
        firebase_admin.initialize_app()


def get_firestore_client():
    """Return the Firestore client."""

    _initialize_firebase()

    return firestore.client()


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def initialize_database(
    database_path: str | Path = DEFAULT_DATABASE,
) -> None:
    """
    Verify that Firestore is reachable.

    Unlike SQLite, Firestore does not require CREATE TABLE statements.
    Collections/documents are created automatically when data is written.
    """
    client = get_firestore_client()

    # A lightweight read verifies that the database is reachable.
    client.collection(FIRESTORE_COLLECTION).limit(1).get()


# ============================================================
# INVOICE IDENTITY / DOCUMENT ID
# ============================================================

def _identity_string(
    invoice_number: str,
    invoice_type: str,
    invoice_date: str | None,
    seller_gstin: str | None,
    buyer_gstin: str | None,
) -> str:
    """
    Build the canonical identity string used for duplicate detection.
    """
    values = [
        (invoice_number or "").strip().upper(),
        (invoice_type or "").strip().upper(),
        (invoice_date or "").strip(),
        (seller_gstin or "").strip().upper(),
        (buyer_gstin or "").strip().upper(),
    ]

    return "|".join(values)


def _document_id(
    invoice_number: str,
    invoice_type: str,
    invoice_date: str | None,
    seller_gstin: str | None,
    buyer_gstin: str | None,
) -> str:
    """Create a deterministic Firestore document ID."""
    identity = _identity_string(
        invoice_number,
        invoice_type,
        invoice_date,
        seller_gstin,
        buyer_gstin,
    )

    return hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()


def get_invoice_document_id(invoice: Invoice) -> str:
    """Return the Firestore document ID for an Invoice."""
    return _document_id(
        invoice.invoice_number,
        invoice.invoice_type,
        invoice.invoice_date,
        invoice.seller_gstin,
        invoice.buyer_gstin,
    )


# ============================================================
# SERIALIZATION
# ============================================================

def _item_to_dict(
    item: Any,
    invoice_id: str,
    item_number: int,
) -> dict[str, Any]:
    return {
        "id": f"{invoice_id}_item_{item_number}",
        "invoice_id": invoice_id,
        "item_number": item_number,
        "material_name": item.material_name,
        "hsn": item.hsn,
        "quantity": item.quantity,
        "unit": item.unit,
        "rate": item.rate,
        "taxable_value": item.taxable_value,
    }


def _tax_to_dict(
    tax: Any,
    invoice_id: str,
    tax_number: int,
) -> dict[str, Any]:
    return {
        "id": f"{invoice_id}_tax_{tax_number}",
        "invoice_id": invoice_id,
        "tax_type": tax.type,
        "rate": tax.rate,
        "amount": tax.amount,
    }


def _invoice_to_dict(
    invoice: Invoice,
    invoice_id: str,
    validation_status: str | None,
) -> dict[str, Any]:
    """
    Convert the Invoice dataclass into one Firestore document.
    """
    return {
        "id": invoice_id,
        "invoice_number": invoice.invoice_number,
        "invoice_type": invoice.invoice_type,
        "invoice_date": invoice.invoice_date,
        "due_date": invoice.due_date,
        "seller": invoice.seller,
        "seller_gstin": invoice.seller_gstin,
        "buyer": invoice.buyer,
        "buyer_gstin": invoice.buyer_gstin,
        "total_tax": float(invoice.total_tax or 0),
        "round_off": float(invoice.round_off or 0),
        "total_amount": float(invoice.total_amount or 0),
        "received_amount": float(invoice.received_amount or 0),
        "source_file": str(invoice.source_file),
        "source_filename": str(invoice.source_filename),
        "source_filename": str(invoice.source_filename),
        "validation_status": validation_status,
        "items": [
            _item_to_dict(
                item,
                invoice_id,
                item_number,
            )
            for item_number, item in enumerate(
                invoice.items,
                start=1,
            )
        ],
        "taxes": [
            _tax_to_dict(
                tax,
                invoice_id,
                tax_number,
            )
            for tax_number, tax in enumerate(
                invoice.taxes,
                start=1,
            )
        ],
    }


def _snapshot_to_dict(snapshot) -> dict[str, Any]:
    """Convert a Firestore document snapshot into a normal dict."""
    data = snapshot.to_dict() or {}
    data.setdefault("id", snapshot.id)
    return data


# ============================================================
# INSERT INVOICE
# ============================================================

def insert_invoice(
    invoice: Invoice,
    database_path: str | Path = DEFAULT_DATABASE,
) -> str:
    """
    Insert an Invoice and all associated items/taxes.

    Returns:
        Firestore document ID.

    Raises:
        ValueError if the exact invoice already exists.
    """
    return insert_validated_invoice(
        invoice,
        validation_status=None,
        database_path=database_path,
    )


# ============================================================
# INSERT WITH VALIDATION STATUS
# ============================================================

def insert_validated_invoice(
    invoice: Invoice,
    validation_status: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> str:
    """
    Insert an invoice while storing its validation status.

    Firestore's create() operation fails if the document already exists,
    so duplicate protection is enforced at the database write itself.
    """
    client = get_firestore_client()

    invoice_id = get_invoice_document_id(invoice)

    document = _invoice_to_dict(
        invoice,
        invoice_id,
        validation_status,
    )

    reference = (
        client.collection(FIRESTORE_COLLECTION)
        .document(invoice_id)
    )

    try:
        reference.create(document)
    except AlreadyExists as exc:
        raise ValueError(
            "Invoice already exists in Firestore."
        ) from exc

    return invoice_id


# ============================================================
# CHECK DUPLICATE
# ============================================================

def invoice_exists(
    invoice_number: str,
    invoice_type: str,
    invoice_date: str,
    seller_gstin: str | None,
    buyer_gstin: str | None,
    database_path: str | Path = DEFAULT_DATABASE,
) -> bool:
    """
    Check whether the exact same invoice already exists.

    Invoice identity:

        invoice number
        + invoice type
        + invoice date
        + seller GSTIN
        + buyer GSTIN
    """
    client = get_firestore_client()

    invoice_id = _document_id(
        invoice_number,
        invoice_type,
        invoice_date,
        seller_gstin,
        buyer_gstin,
    )

    snapshot = (
        client.collection(FIRESTORE_COLLECTION)
        .document(invoice_id)
        .get()
    )

    return snapshot.exists


# ============================================================
# FETCH INVOICES
# ============================================================

def get_all_invoices(
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    """
    Return all stored invoices.

    Results are dictionaries rather than sqlite3.Row objects.
    Existing InvoiceIQ code can continue using invoice["field"] access.
    """
    client = get_firestore_client()

    rows = [
        _snapshot_to_dict(snapshot)
        for snapshot in (
            client.collection(FIRESTORE_COLLECTION).stream()
        )
    ]

    rows.sort(
        key=lambda row: (
            row.get("invoice_date") or "",
            row.get("id") or "",
        )
    )

    return rows


# ============================================================
# FETCH SINGLE INVOICE
# ============================================================

def get_invoice_by_id(
    invoice_id: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> dict[str, Any] | None:
    """Return one invoice document by Firestore document ID."""
    client = get_firestore_client()

    snapshot = (
        client.collection(FIRESTORE_COLLECTION)
        .document(str(invoice_id))
        .get()
    )

    if not snapshot.exists:
        return None

    return _snapshot_to_dict(snapshot)


# ============================================================
# FETCH ITEMS
# ============================================================

def get_invoice_items(
    invoice_id: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    """
    Return all items belonging to an invoice.

    Items are embedded inside the invoice document in Firestore.
    """
    invoice = get_invoice_by_id(
        invoice_id,
        database_path,
    )

    if invoice is None:
        return []

    items = invoice.get("items") or []

    return sorted(
        items,
        key=lambda item: int(
            item.get("item_number", 0)
        ),
    )


# ============================================================
# FETCH TAXES
# ============================================================

def get_invoice_taxes(
    invoice_id: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[dict[str, Any]]:
    """
    Return all taxes belonging to an invoice.

    Taxes are embedded inside the invoice document in Firestore.
    """
    invoice = get_invoice_by_id(
        invoice_id,
        database_path,
    )

    if invoice is None:
        return []

    return invoice.get("taxes") or []


# ============================================================
# DELETE INVOICE
# ============================================================

def delete_invoice(
    invoice_id: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> bool:
    """
    Delete an invoice.

    Items and taxes are embedded in the invoice document, so deleting
    the document deletes them automatically.
    """
    client = get_firestore_client()

    reference = (
        client.collection(FIRESTORE_COLLECTION)
        .document(str(invoice_id))
    )

    snapshot = reference.get()

    if not snapshot.exists:
        return False

    reference.delete()
    return True


# ============================================================
# DATABASE SUMMARY
# ============================================================

def get_database_summary(
    database_path: str | Path = DEFAULT_DATABASE,
) -> dict[str, int]:
    """Return basic Firestore statistics."""
    invoices = get_all_invoices(database_path)

    item_count = sum(
        len(invoice.get("items") or [])
        for invoice in invoices
    )

    tax_count = sum(
        len(invoice.get("taxes") or [])
        for invoice in invoices
    )

    return {
        "invoices": len(invoices),
        "items": item_count,
        "taxes": tax_count,
    }


# ============================================================
# COMMAND LINE TEST
# ============================================================

if __name__ == "__main__":
    initialize_database()

    print("✅ InvoiceIQ Firestore connection initialized.")

    summary = get_database_summary()

    print("\nFirestore summary:")
    print(f"  Invoices: {summary['invoices']}")
    print(f"  Items:    {summary['items']}")
    print(f"  Taxes:    {summary['taxes']}")

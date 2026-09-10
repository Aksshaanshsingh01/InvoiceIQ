"""
InvoiceIQ - SQLite Database Layer

Stores extracted invoices, invoice items, and taxes.

Database relationship:

    invoices
        |
        +----< items
        |
        +----< taxes

The database layer is intentionally independent from:
    - PDF extraction
    - batch processing
    - Excel export
    - JSON export
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from extraction.invoice_extractor import Invoice


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_DATABASE = (
    Path("output") / "invoiceiq.db"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================


def get_connection(
    database_path: str | Path = DEFAULT_DATABASE,
) -> sqlite3.Connection:
    """
    Create a SQLite database connection.

    Row factory is enabled so rows can be accessed by
    column name.
    """

    database_path = Path(
        database_path
    )

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        database_path
    )

    connection.row_factory = (
        sqlite3.Row
    )

    # Enable foreign-key enforcement.
    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


# ============================================================
# DATABASE INITIALIZATION
# ============================================================


def initialize_database(
    database_path: str | Path = DEFAULT_DATABASE,
) -> None:
    """
    Create all InvoiceIQ database tables.

    Safe to call multiple times.
    """

    with get_connection(
        database_path
    ) as connection:

        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                invoice_number TEXT NOT NULL,
                invoice_type TEXT NOT NULL,

                invoice_date TEXT,
                due_date TEXT,

                seller TEXT,
                seller_gstin TEXT,

                buyer TEXT,
                buyer_gstin TEXT,

                total_tax REAL NOT NULL DEFAULT 0,
                round_off REAL NOT NULL DEFAULT 0,
                total_amount REAL NOT NULL DEFAULT 0,
                received_amount REAL NOT NULL DEFAULT 0,

                source_file TEXT,

                validation_status TEXT,

                created_at TEXT
                    NOT NULL DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (
                    invoice_number,
                    invoice_type,
                    invoice_date,
                    seller_gstin,
                    buyer_gstin
                )
            );


            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                invoice_id INTEGER NOT NULL,

                item_number INTEGER NOT NULL,

                material_name TEXT,
                hsn TEXT,

                quantity REAL,
                unit TEXT,

                rate REAL,
                taxable_value REAL,

                FOREIGN KEY (
                    invoice_id
                )
                REFERENCES invoices(id)
                ON DELETE CASCADE,

                UNIQUE (
                    invoice_id,
                    item_number
                )
            );


            CREATE TABLE IF NOT EXISTS taxes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                invoice_id INTEGER NOT NULL,

                tax_type TEXT NOT NULL,

                rate REAL,
                amount REAL,

                FOREIGN KEY (
                    invoice_id
                )
                REFERENCES invoices(id)
                ON DELETE CASCADE
            );


            CREATE INDEX IF NOT EXISTS
                idx_invoices_invoice_number
            ON invoices(invoice_number);


            CREATE INDEX IF NOT EXISTS
                idx_invoices_seller_gstin
            ON invoices(seller_gstin);


            CREATE INDEX IF NOT EXISTS
                idx_items_invoice_id
            ON items(invoice_id);


            CREATE INDEX IF NOT EXISTS
                idx_taxes_invoice_id
            ON taxes(invoice_id);
            """
        )


# ============================================================
# INSERT INVOICE
# ============================================================


def insert_invoice(
    invoice: Invoice,
    database_path: str | Path = DEFAULT_DATABASE,
) -> int:
    """
    Insert an Invoice and all associated items and taxes.

    Returns:
        Database ID of the invoice.

    Raises:
        sqlite3.IntegrityError if the invoice already exists
        according to the seller GSTIN + invoice number constraint.

    The entire operation is transactional.
    """

    with get_connection(
        database_path
    ) as connection:

        cursor = connection.execute(
            """
            INSERT INTO invoices (
                invoice_number,
                invoice_type,
                invoice_date,
                due_date,
                seller,
                seller_gstin,
                buyer,
                buyer_gstin,
                total_tax,
                round_off,
                total_amount,
                received_amount,
                source_file,
                validation_status
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
            """,
            (
                invoice.invoice_number,
                invoice.invoice_type,
                invoice.invoice_date,
                invoice.due_date,
                invoice.seller,
                invoice.seller_gstin,
                invoice.buyer,
                invoice.buyer_gstin,
                invoice.total_tax,
                invoice.round_off,
                invoice.total_amount,
                invoice.received_amount,
                str(invoice.source_file),
                None,
            ),
        )

        invoice_id = cursor.lastrowid

        # ----------------------------------------------------
        # Items
        # ----------------------------------------------------

        for item_number, item in enumerate(
            invoice.items,
            start=1,
        ):

            connection.execute(
                """
                INSERT INTO items (
                    invoice_id,
                    item_number,
                    material_name,
                    hsn,
                    quantity,
                    unit,
                    rate,
                    taxable_value
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_id,
                    item_number,
                    item.material_name,
                    item.hsn,
                    item.quantity,
                    item.unit,
                    item.rate,
                    item.taxable_value,
                ),
            )

        # ----------------------------------------------------
        # Taxes
        # ----------------------------------------------------

        for tax in invoice.taxes:

            connection.execute(
                """
                INSERT INTO taxes (
                    invoice_id,
                    tax_type,
                    rate,
                    amount
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    invoice_id,
                    tax.type,
                    tax.rate,
                    tax.amount,
                ),
            )

        return int(invoice_id)


# ============================================================
# INSERT WITH VALIDATION STATUS
# ============================================================


def insert_validated_invoice(
    invoice: Invoice,
    validation_status: str,
    database_path: str | Path = DEFAULT_DATABASE,
) -> int:
    """
    Insert an invoice while explicitly storing its
    validation status.

    Expected statuses include:

        VALID
        WARNING
        INVALID
    """

    with get_connection(
        database_path
    ) as connection:

        cursor = connection.execute(
            """
            INSERT INTO invoices (
                invoice_number,
                invoice_type,
                invoice_date,
                due_date,
                seller,
                seller_gstin,
                buyer,
                buyer_gstin,
                total_tax,
                round_off,
                total_amount,
                received_amount,
                source_file,
                validation_status
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
            """,
            (
                invoice.invoice_number,
                invoice.invoice_type,
                invoice.invoice_date,
                invoice.due_date,
                invoice.seller,
                invoice.seller_gstin,
                invoice.buyer,
                invoice.buyer_gstin,
                invoice.total_tax,
                invoice.round_off,
                invoice.total_amount,
                invoice.received_amount,
                str(invoice.source_file),
                validation_status,
            ),
        )

        invoice_id = cursor.lastrowid

        for item_number, item in enumerate(
            invoice.items,
            start=1,
        ):

            connection.execute(
                """
                INSERT INTO items (
                    invoice_id,
                    item_number,
                    material_name,
                    hsn,
                    quantity,
                    unit,
                    rate,
                    taxable_value
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_id,
                    item_number,
                    item.material_name,
                    item.hsn,
                    item.quantity,
                    item.unit,
                    item.rate,
                    item.taxable_value,
                ),
            )

        for tax in invoice.taxes:

            connection.execute(
                """
                INSERT INTO taxes (
                    invoice_id,
                    tax_type,
                    rate,
                    amount
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    invoice_id,
                    tax.type,
                    tax.rate,
                    tax.amount,
                ),
            )

        return int(invoice_id)


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

    This allows the same invoice number to appear on
    different dates or transactions.
    """

    with get_connection(
        database_path
    ) as connection:

        row = connection.execute(
            """
            SELECT 1
            FROM invoices
            WHERE invoice_number = ?
              AND invoice_type = ?
              AND invoice_date = ?
              AND seller_gstin IS ?
              AND buyer_gstin IS ?
            LIMIT 1
            """,
            (
                invoice_number,
                invoice_type,
                invoice_date,
                seller_gstin,
                buyer_gstin,
            ),
        ).fetchone()

    return row is not None


# ============================================================
# FETCH INVOICES
# ============================================================


def get_all_invoices(
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[sqlite3.Row]:
    """
    Return all stored invoices.
    """

    with get_connection(
        database_path
    ) as connection:

        rows = connection.execute(
            """
            SELECT *
            FROM invoices
            ORDER BY id
            """
        ).fetchall()

    return rows


# ============================================================
# FETCH ITEMS
# ============================================================


def get_invoice_items(
    invoice_id: int,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[sqlite3.Row]:
    """
    Return all items belonging to an invoice.
    """

    with get_connection(
        database_path
    ) as connection:

        rows = connection.execute(
            """
            SELECT *
            FROM items
            WHERE invoice_id = ?
            ORDER BY item_number
            """,
            (invoice_id,),
        ).fetchall()

    return rows


# ============================================================
# FETCH TAXES
# ============================================================


def get_invoice_taxes(
    invoice_id: int,
    database_path: str | Path = DEFAULT_DATABASE,
) -> list[sqlite3.Row]:
    """
    Return all taxes belonging to an invoice.
    """

    with get_connection(
        database_path
    ) as connection:

        rows = connection.execute(
            """
            SELECT *
            FROM taxes
            WHERE invoice_id = ?
            ORDER BY id
            """,
            (invoice_id,),
        ).fetchall()

    return rows


# ============================================================
# DELETE INVOICE
# ============================================================


def delete_invoice(
    invoice_id: int,
    database_path: str | Path = DEFAULT_DATABASE,
) -> bool:
    """
    Delete an invoice.

    Associated items and taxes are automatically deleted
    through ON DELETE CASCADE.

    Returns True if an invoice was deleted.
    """

    with get_connection(
        database_path
    ) as connection:

        cursor = connection.execute(
            """
            DELETE FROM invoices
            WHERE id = ?
            """,
            (invoice_id,),
        )

    return cursor.rowcount > 0


# ============================================================
# DATABASE SUMMARY
# ============================================================


def get_database_summary(
    database_path: str | Path = DEFAULT_DATABASE,
) -> dict[str, int]:
    """
    Return basic database statistics.
    """

    with get_connection(
        database_path
    ) as connection:

        invoice_count = connection.execute(
            "SELECT COUNT(*) FROM invoices"
        ).fetchone()[0]

        item_count = connection.execute(
            "SELECT COUNT(*) FROM items"
        ).fetchone()[0]

        tax_count = connection.execute(
            "SELECT COUNT(*) FROM taxes"
        ).fetchone()[0]

    return {
        "invoices": invoice_count,
        "items": item_count,
        "taxes": tax_count,
    }


# ============================================================
# COMMAND LINE TEST
# ============================================================


if __name__ == "__main__":

    initialize_database()

    print(
        "✅ InvoiceIQ database initialized."
    )

    print(
        f"Database: {DEFAULT_DATABASE}"
    )

    summary = get_database_summary()

    print("\nDatabase summary:")

    print(
        f"  Invoices: {summary['invoices']}"
    )

    print(
        f"  Items:    {summary['items']}"
    )

    print(
        f"  Taxes:    {summary['taxes']}"
    )
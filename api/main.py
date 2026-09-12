"""
InvoiceIQ - FastAPI Application

API layer for the InvoiceIQ invoice-processing system.
"""

from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from uuid import uuid4
from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
)

from database.db import (
    DEFAULT_DATABASE,
    initialize_database,
    get_all_invoices,
    get_invoice_items,
    get_invoice_taxes,
)

from database.queries import (
    get_invoice_by_id,
    get_invoice_by_number,
    get_invoices_by_seller,
    get_invoices_by_buyer,
    get_invoices_by_seller_gstin,
    get_invoices_by_type,
    get_invoices_by_date_range,
)

from analytics.dashboard import get_dashboard_metrics
from database.client_queries import search_clients as search_client_records

from services.invoice_service import process_invoice


load_dotenv()


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)




# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("invoiceiq.api")


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

UPLOAD_DIRECTORY = Path(
    os.getenv(
        "INVOICEIQ_UPLOAD_DIRECTORY",
        str(PROJECT_ROOT / "uploads"),
    )
)

MAX_UPLOAD_SIZE = int(
    os.getenv(
        "INVOICEIQ_MAX_UPLOAD_SIZE",
        str(10 * 1024 * 1024),  # 10 MB
    )
)


# ============================================================
# APPLICATION LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize InvoiceIQ resources when the API starts.
    """

    logger.info("Starting InvoiceIQ API")

    UPLOAD_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    initialize_database()

    logger.info("Firestore connection initialized")
    logger.info(
        "Upload directory: %s",
        UPLOAD_DIRECTORY,
    )
    logger.info(
        "Maximum upload size: %d bytes",
        MAX_UPLOAD_SIZE,
    )

    yield

    logger.info("Shutting down InvoiceIQ API")


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="InvoiceIQ API",
    description="Invoice processing and analytics API",
    version="1.0.0",
    lifespan=lifespan,
)

# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup_event():
    """
    Initialize the database and upload directory
    when the API starts.
    """

    initialize_database(DEFAULT_DATABASE)

    UPLOAD_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    """
    Confirm that the InvoiceIQ API is running.
    """

    return {
        "status": "healthy",
        "service": "InvoiceIQ API",
    }


# ============================================================
# GET ALL INVOICES
# ============================================================

@app.get("/invoices")
def get_invoices():
    """
    Return all invoices stored in the database.
    """

    invoices = get_all_invoices(
        DEFAULT_DATABASE
    )

    return {
        "count": len(invoices),
        "invoices": [
            dict(invoice)
            for invoice in invoices
        ],
    }

# ============================================================
# SEARCH INVOICES
# ============================================================

@app.get("/invoices/search")
def search_invoices(
    invoice_number: str | None = Query(
        default=None
    ),
    seller: str | None = Query(
        default=None
    ),
    buyer: str | None = Query(
        default=None
    ),
    seller_gstin: str | None = Query(
        default=None
    ),
    invoice_type: str | None = Query(
        default=None
    ),
    start_date: str | None = Query(
        default=None
    ),
    end_date: str | None = Query(
        default=None
    ),
):
    """
    Search invoices using supported filters.
    """

    # --------------------------------------------------------
    # 1. Date range
    # --------------------------------------------------------

    if start_date or end_date:

        if not start_date or not end_date:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Both start_date and end_date "
                    "are required for date range search."
                ),
            )

        invoices = get_invoices_by_date_range(
            start_date,
            end_date,
            DEFAULT_DATABASE,
        )

    # --------------------------------------------------------
    # 2. Invoice number
    # --------------------------------------------------------

    elif invoice_number:

        invoices = get_invoice_by_number(
            invoice_number,
            DEFAULT_DATABASE,
        )

    # --------------------------------------------------------
    # 3. Seller
    # --------------------------------------------------------

    elif seller:

        invoices = get_invoices_by_seller(
            seller,
            DEFAULT_DATABASE,
        )

    # --------------------------------------------------------
    # 4. Buyer
    # --------------------------------------------------------

    elif buyer:

        invoices = get_invoices_by_buyer(
            buyer,
            DEFAULT_DATABASE,
        )

    # --------------------------------------------------------
    # 5. Seller GSTIN
    # --------------------------------------------------------

    elif seller_gstin:

        invoices = get_invoices_by_seller_gstin(
            seller_gstin,
            DEFAULT_DATABASE,
        )

    # --------------------------------------------------------
    # 6. Invoice type
    # --------------------------------------------------------

    elif invoice_type:

        normalized_type = invoice_type.upper()

        if normalized_type not in {
            "SALE",
            "PURCHASE",
        }:
            raise HTTPException(
                status_code=400,
                detail=(
                    "invoice_type must be "
                    "'SALE' or 'PURCHASE'."
                ),
            )

        invoices = get_invoices_by_type(
            normalized_type,
            DEFAULT_DATABASE,
        )

    # --------------------------------------------------------
    # 7. No filter
    # --------------------------------------------------------

    else:

        raise HTTPException(
            status_code=400,
            detail="Provide at least one search filter.",
        )

    # --------------------------------------------------------
    # 8. Return results
    # --------------------------------------------------------

    return {
        "count": len(invoices),
        "invoices": [
            dict(invoice)
            for invoice in invoices
        ],
    }

# ============================================================
# SEARCH CLIENTS
# ============================================================

@app.get("/clients/search")
def search_clients(
    q: str = Query(
        ...,
        min_length=1,
        description="Client name, GSTIN, or invoice number",
    ),
):
    """
    Search clients by name or GSTIN.

    GSTIN is treated as the client-level identifier, so the response
    includes the complete invoice history for each matching GSTIN.
    """
    results = search_client_records(
        q,
        DEFAULT_DATABASE,
    )

    return {
        "count": len(results),
        "clients": results,
    }


# ============================================================
# DASHBOARD METRICS
# ============================================================

@app.get("/dashboard")
def dashboard():
    """Return aggregated financial and invoice activity metrics."""
    return get_dashboard_metrics(DEFAULT_DATABASE)


# ============================================================
# GET SINGLE INVOICE
# ============================================================

@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    """
    Return one invoice with its items and taxes.
    """

    # --------------------------------------------------------
    # 1. Get invoice
    # --------------------------------------------------------

    invoice = get_invoice_by_id(
        invoice_id,
        DEFAULT_DATABASE,
    )

    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice with ID {invoice_id} not found.",
        )

    # --------------------------------------------------------
    # 2. Get invoice items
    # --------------------------------------------------------

    items = get_invoice_items(
        invoice_id,
        DEFAULT_DATABASE,
    )

    # --------------------------------------------------------
    # 3. Get invoice taxes
    # --------------------------------------------------------

    taxes = get_invoice_taxes(
        invoice_id,
        DEFAULT_DATABASE,
    )

    # --------------------------------------------------------
    # 4. Build response
    # --------------------------------------------------------

    return {
        **dict(invoice),
        "items": [
            dict(item)
            for item in items
        ],
        "taxes": [
            dict(tax)
            for tax in taxes
        ],
    }

# ============================================================
# INVOICE UPLOAD
# ============================================================

@app.post("/invoices/upload")
async def upload_invoice(
    file: UploadFile = File(...),
):
    """
    Upload and process an invoice PDF.

    Workflow:

        PDF upload
            ↓
        Validate upload
            ↓
        Save temporary file
            ↓
        Service Layer
            ↓
        Extraction
            ↓
        Validation
            ↓
        Duplicate Check
            ↓
        Firestore
            ↓
        Delete temporary file
            ↓
        Return result
    """

    upload_path: Path | None = None

    # --------------------------------------------------------
    # 1. Validate filename
    # --------------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided.",
        )

    original_filename = Path(file.filename).name

    # --------------------------------------------------------
    # 2. Validate file extension
    # --------------------------------------------------------

    file_extension = Path(
        original_filename
    ).suffix.lower()

    if file_extension != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    # --------------------------------------------------------
    # 3. Read upload with size protection
    # --------------------------------------------------------

    file_contents = await file.read()

    if not file_contents:
        raise HTTPException(
            status_code=400,
            detail="The uploaded PDF is empty.",
        )

    if len(file_contents) > MAX_UPLOAD_SIZE:
        max_size_mb = MAX_UPLOAD_SIZE / (1024 * 1024)

        raise HTTPException(
            status_code=413,
            detail=(
                f"Uploaded file exceeds the maximum allowed size "
                f"of {max_size_mb:.1f} MB."
            ),
        )

    # --------------------------------------------------------
    # 4. Validate PDF signature
    # --------------------------------------------------------

    if not file_contents.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid PDF.",
        )

    # --------------------------------------------------------
    # 5. Create temporary upload path
    # --------------------------------------------------------

    unique_filename = f"{uuid4().hex}.pdf"

    upload_path = (
        UPLOAD_DIRECTORY
        / unique_filename
    )

    # --------------------------------------------------------
    # 6. Save temporary PDF
    # --------------------------------------------------------

    try:
        upload_path.write_bytes(file_contents)

        logger.info(
            "Processing uploaded invoice: %s",
            original_filename,
        )

        # ----------------------------------------------------
        # 7. Process through Service Layer
        # ----------------------------------------------------

        result = process_invoice(
            upload_path,
            DEFAULT_DATABASE,
            source_filename=file.filename,
        )

        # ----------------------------------------------------
        # 8. Handle duplicate
        # ----------------------------------------------------

        if result["status"] == "DUPLICATE":
            raise HTTPException(
                status_code=409,
                detail=result,
            )

        # ----------------------------------------------------
        # 9. Handle validation failure
        # ----------------------------------------------------

        if result["status"] == "VALIDATION_FAILED":
            raise HTTPException(
                status_code=422,
                detail=result,
            )

        # ----------------------------------------------------
        # 10. Successful processing
        # ----------------------------------------------------

        logger.info(
            "Invoice processed successfully: %s",
            original_filename,
        )

        return result

    except HTTPException:
        raise

    except ValueError as exc:
        logger.warning(
            "Invoice processing failed for %s: %s",
            original_filename,
            exc,
        )

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception:
        logger.exception(
            "Unexpected error while processing %s",
            original_filename,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "An unexpected error occurred while "
                "processing the invoice."
            ),
        )

    finally:
        # ----------------------------------------------------
        # 11. Always delete temporary PDF
        # ----------------------------------------------------

        if upload_path is not None:
            try:
                upload_path.unlink(
                    missing_ok=True
                )

                logger.debug(
                    "Deleted temporary upload: %s",
                    upload_path,
                )

            except OSError:
                logger.exception(
                    "Failed to delete temporary upload: %s",
                    upload_path,
                )

    # --------------------------------------------------------
    # 1. Validate file type
    # --------------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided.",
        )

    file_extension = Path(
        file.filename
    ).suffix.lower()

    if file_extension != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    # --------------------------------------------------------
    # 2. Create unique upload filename
    # --------------------------------------------------------

    unique_filename = (
        f"{uuid4().hex}{file_extension}"
    )

    upload_path = (
        UPLOAD_DIRECTORY
        / unique_filename
    )

    # --------------------------------------------------------
    # 3. Save uploaded PDF
    # --------------------------------------------------------

    file_contents = await file.read()

    upload_path.write_bytes(
        file_contents
    )

    # --------------------------------------------------------
    # 4. Process invoice through Service Layer
    # --------------------------------------------------------

    try:

        result = process_invoice(
            upload_path,
            DEFAULT_DATABASE,
        )

    except ValueError as exc:

        # Extraction/parsing failures are input errors, not server failures.
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the invoice.",
        ) from exc

    # --------------------------------------------------------
    # 5. Handle duplicate
    # --------------------------------------------------------

    if result["status"] == "DUPLICATE":

        raise HTTPException(
            status_code=409,
            detail=result,
        )

    # --------------------------------------------------------
    # 6. Handle validation failure
    # --------------------------------------------------------

    if result["status"] == "VALIDATION_FAILED":

        raise HTTPException(
            status_code=422,
            detail=result,
        )

    # --------------------------------------------------------
    # 7. Successful processing
    # --------------------------------------------------------

    return result

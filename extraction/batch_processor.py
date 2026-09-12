"""
InvoiceIQ - Batch Processing Engine

Processes multiple invoice PDFs from a directory.

Responsibilities:

    1. Discover PDF files
    2. Extract each invoice
    3. Validate each invoice
    4. Detect duplicates within the batch
    5. Detect duplicates already stored in SQLite
    6. Persist new invoices to SQLite
    7. Export JSON and Excel
    8. Produce a batch summary
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json

from .invoice_extractor import (
    Invoice,
    extract_invoice,
)

from .validators import validate_invoice

from .exporter import (
    export_invoices_json,
)

from database.db import (
    DEFAULT_DATABASE,
    initialize_database,
    insert_validated_invoice,
    invoice_exists,
)

from export.excel_exporter import (
    export_invoices_excel,
)


# ============================================================
# BATCH RESULT
# ============================================================


@dataclass
class BatchFailure:
    """
    Represents one PDF that could not be processed.
    """

    file: str
    error: str


@dataclass
class BatchResult:
    """
    Result of processing an entire directory.
    """

    total_files: int = 0

    successful_files: int = 0

    failed_files: int = 0

    invoices: list[Invoice] = field(
        default_factory=list
    )

    failures: list[BatchFailure] = field(
        default_factory=list
    )

    duplicate_invoice_numbers: list[str] = field(
        default_factory=list
    )

    database_duplicates: list[str] = field(
        default_factory=list
    )

    database_inserted: int = 0

    validation_errors: dict[str, list[str]] = field(
        default_factory=dict
    )

    @property
    def success_rate(self) -> float:
        """
        Percentage of files successfully extracted.
        """

        if self.total_files == 0:
            return 0.0

        return (
            self.successful_files
            / self.total_files
            * 100
        )


# ============================================================
# DISCOVER PDF FILES
# ============================================================


def discover_pdfs(
    input_directory: str | Path,
) -> list[Path]:
    """
    Find PDF files in the supplied directory.

    Only files directly inside the directory are processed.
    """

    input_directory = Path(
        input_directory
    )

    if not input_directory.exists():
        raise FileNotFoundError(
            f"Input directory not found: "
            f"{input_directory}"
        )

    if not input_directory.is_dir():
        raise NotADirectoryError(
            f"Input path is not a directory: "
            f"{input_directory}"
        )

    return sorted(
        [
            path
            for path in input_directory.iterdir()
            if path.is_file()
            and path.suffix.lower() == ".pdf"
        ]
    )


# ============================================================
# PROCESS ONE PDF
# ============================================================


def process_pdf(
    pdf_path: str | Path,
) -> Invoice:
    """
    Extract one invoice from one PDF.
    """

    return extract_invoice(
        Path(pdf_path)
    )


# ============================================================
# PROCESS DIRECTORY
# ============================================================


def process_directory(
    input_directory: str | Path,
    database_path: str | Path | None = None,
) -> BatchResult:
    """
    Process every PDF in a directory.

    If database_path is supplied:

        - SQLite is initialized
        - extracted invoices are persisted
        - existing invoices are skipped

    If database_path is None:

        - processing works without persistence
        - useful for isolated tests and library usage

    One failed invoice does not stop the entire batch.
    """

    pdf_files = discover_pdfs(
        input_directory
    )

    result = BatchResult(
        total_files=len(pdf_files)
    )

    # --------------------------------------------------------
    # Initialize database if requested
    # --------------------------------------------------------

    if database_path is not None:

        initialize_database(
            database_path
        )

    # Tracks invoice identity within this batch.
    #
    # Identity:
    #
    #     seller GSTIN + invoice number
    #
    seen_invoices: set[tuple[str, str]] = set()

    for pdf_path in pdf_files:

        print(
            f"\nProcessing: {pdf_path.name}"
        )

        try:

            # ------------------------------------------------
            # Extraction
            # ------------------------------------------------

            invoice = process_pdf(
                pdf_path
            )

            result.invoices.append(
                invoice
            )

            result.successful_files += 1

            print(
                f"  ✅ Extracted: "
                f"{invoice.invoice_number}"
            )

            # ------------------------------------------------
            # Validation
            # ------------------------------------------------

            validation = validate_invoice(
                invoice
            )

            if validation.errors:

                result.validation_errors[
                    invoice.invoice_number
                ] = list(
                    validation.errors
                )

                print(
                    "  ⚠️ Validation: "
                    f"{validation.status}"
                )

            else:

                print(
                    "  ✅ Validation: "
                    f"{validation.status}"
                )

            # ------------------------------------------------
            # Duplicate identity
            # ------------------------------------------------

            invoice_key = (
                invoice.seller_gstin or "",
                invoice.invoice_number or "",
            )

            # ------------------------------------------------
            # Duplicate inside current batch
            # ------------------------------------------------

            if invoice_key in seen_invoices:

                if (
                    invoice.invoice_number
                    not in result.duplicate_invoice_numbers
                ):

                    result.duplicate_invoice_numbers.append(
                        invoice.invoice_number
                    )

                print(
                    "  ⚠️ Duplicate within current batch"
                )

                # Do not insert the duplicate into DB.
                continue

            seen_invoices.add(
                invoice_key
            )

            # ------------------------------------------------
            # Database persistence
            # ------------------------------------------------

            if database_path is not None:

                already_exists = invoice_exists(
                    invoice.invoice_number,
                    invoice.seller_gstin,
                    database_path,
                )

                if already_exists:

                    if (
                        invoice.invoice_number
                        not in result.database_duplicates
                    ):

                        result.database_duplicates.append(
                            invoice.invoice_number
                        )

                    print(
                        "  ⚠️ Already exists in database"
                    )

                else:

                    insert_validated_invoice(
                        invoice,
                        validation.status,
                        database_path,
                    )

                    result.database_inserted += 1

                    print(
                        "  💾 Stored in database"
                    )

        except Exception as error:

            result.failed_files += 1

            result.failures.append(
                BatchFailure(
                    file=str(pdf_path),
                    error=str(error),
                )
            )

            print(
                f"  ❌ Failed: {error}"
            )

    return result


# ============================================================
# EXPORT BATCH RESULT
# ============================================================


def export_batch_result(
    result: BatchResult,
    output_directory: str | Path,
) -> dict[str, Path]:
    """
    Export successfully extracted invoices.

    Files created:

        invoices.json
        InvoiceIQ.xlsx
        batch_summary.json
    """

    output_directory = Path(
        output_directory
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    json_path = (
        output_directory
        / "invoices.json"
    )

    export_invoices_json(
        result.invoices,
        json_path,
    )

    # --------------------------------------------------------
    # Excel
    # --------------------------------------------------------

    excel_path = (
        output_directory
        / "InvoiceIQ.xlsx"
    )

    export_invoices_excel(
        result.invoices,
        excel_path,
    )

    # --------------------------------------------------------
    # Batch summary
    # --------------------------------------------------------

    summary_path = (
        output_directory
        / "batch_summary.json"
    )

    summary = {
        "total_files": result.total_files,

        "successful_files": (
            result.successful_files
        ),

        "failed_files": (
            result.failed_files
        ),

        "success_rate": round(
            result.success_rate,
            2,
        ),

        "duplicate_invoice_numbers": (
            result.duplicate_invoice_numbers
        ),

        "database_duplicates": (
            result.database_duplicates
        ),

        "database_inserted": (
            result.database_inserted
        ),

        "validation_errors": (
            result.validation_errors
        ),

        "failures": [
            {
                "file": failure.file,
                "error": failure.error,
            }
            for failure in result.failures
        ],
    }

    with summary_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            summary,
            file,
            indent=2,
            ensure_ascii=False,
        )

    return {
        "json": json_path,
        "excel": excel_path,
        "summary": summary_path,
    }


# ============================================================
# PRINT SUMMARY
# ============================================================


def print_batch_summary(
    result: BatchResult,
) -> None:
    """
    Print a human-readable batch summary.
    """

    print("\n")

    print(
        "=" * 70
    )

    print(
        "INVOICEIQ BATCH SUMMARY"
    )

    print(
        "=" * 70
    )

    print(
        f"Total files       : "
        f"{result.total_files}"
    )

    print(
        f"Successful        : "
        f"{result.successful_files}"
    )

    print(
        f"Failed            : "
        f"{result.failed_files}"
    )

    print(
        f"Success rate      : "
        f"{result.success_rate:.2f}%"
    )

    print(
        f"Batch duplicates  : "
        f"{len(result.duplicate_invoice_numbers)}"
    )

    print(
        f"DB duplicates     : "
        f"{len(result.database_duplicates)}"
    )

    print(
        f"DB inserted       : "
        f"{result.database_inserted}"
    )

    print(
        f"Validation issues : "
        f"{len(result.validation_errors)}"
    )

    # --------------------------------------------------------
    # Batch duplicates
    # --------------------------------------------------------

    if result.duplicate_invoice_numbers:

        print(
            "\nDUPLICATE IN CURRENT BATCH:"
        )

        for invoice_number in (
            result.duplicate_invoice_numbers
        ):

            print(
                f"  ⚠️ {invoice_number}"
            )

    # --------------------------------------------------------
    # Database duplicates
    # --------------------------------------------------------

    if result.database_duplicates:

        print(
            "\nALREADY IN DATABASE:"
        )

        for invoice_number in (
            result.database_duplicates
        ):

            print(
                f"  ⚠️ {invoice_number}"
            )

    # --------------------------------------------------------
    # Validation issues
    # --------------------------------------------------------

    if result.validation_errors:

        print(
            "\nVALIDATION ISSUES:"
        )

        for invoice_number, errors in (
            result.validation_errors.items()
        ):

            print(
                f"\n  {invoice_number}"
            )

            for error in errors:

                print(
                    f"    ❌ {error}"
                )

    # --------------------------------------------------------
    # Failed files
    # --------------------------------------------------------

    if result.failures:

        print(
            "\nFAILED FILES:"
        )

        for failure in result.failures:

            print(
                f"  ❌ {failure.file}"
            )

            print(
                f"     {failure.error}"
            )

    print(
        "=" * 70
    )


# ============================================================
# COMMAND LINE INTERFACE
# ============================================================


if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:

        print(
            "Usage:"
        )

        print(
            "python -m extraction.batch_processor "
            "<input_directory> [output_directory] "
            "[database_path]"
        )

        sys.exit(1)

    input_directory = Path(
        sys.argv[1]
    )

    if len(sys.argv) >= 3:

        output_directory = Path(
            sys.argv[2]
        )

    else:

        output_directory = (
            Path("output") / "batch"
        )

    if len(sys.argv) >= 4:

        database_path = Path(
            sys.argv[3]
        )

    else:

        database_path = DEFAULT_DATABASE

    print(
        "=" * 70
    )

    print(
        "InvoiceIQ Batch Processor"
    )

    print(
        "=" * 70
    )

    print(
        f"Input    : {input_directory}"
    )

    print(
        f"Output   : {output_directory}"
    )

    print(
        f"Database : {database_path}"
    )

    try:

        batch_result = process_directory(
            input_directory,
            database_path,
        )

        print_batch_summary(
            batch_result
        )

        exported = export_batch_result(
            batch_result,
            output_directory,
        )

        print(
            "\nEXPORTED FILES:"
        )

        for file_type, path in (
            exported.items()
        ):

            print(
                f"  {file_type.upper():8} "
                f"{path}"
            )

    except Exception as error:

        print(
            f"\n❌ Batch processing failed: "
            f"{error}"
        )

        sys.exit(1)

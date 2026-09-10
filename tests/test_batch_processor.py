"""
Tests for the InvoiceIQ batch processing engine.
"""

from pathlib import Path

from extraction.batch_processor import (
    discover_pdfs,
    process_directory,
    export_batch_result,
)


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

SAMPLES_DIR = (
    PROJECT_ROOT / "samples"
)


# ============================================================
# PDF Discovery
# ============================================================


def test_discover_pdfs():

    pdfs = discover_pdfs(
        SAMPLES_DIR
    )

    assert len(pdfs) == 4

    assert all(
        pdf.suffix.lower() == ".pdf"
        for pdf in pdfs
    )


# ============================================================
# Batch Processing
# ============================================================


def test_process_directory():

    result = process_directory(
        SAMPLES_DIR
    )

    # --------------------------------------------------------
    # File counts
    # --------------------------------------------------------

    assert result.total_files == 4

    assert result.successful_files == 4

    assert result.failed_files == 0

    # --------------------------------------------------------
    # Invoices
    # --------------------------------------------------------

    assert len(result.invoices) == 4

    # --------------------------------------------------------
    # Duplicate detection
    # --------------------------------------------------------

    assert (
        "YGEPL/26-27/4"
        in result.duplicate_invoice_numbers
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    assert (
        len(result.validation_errors)
        == 0
    )


# ============================================================
# Batch Export
# ============================================================


def test_export_batch_result(
    tmp_path,
):

    result = process_directory(
        SAMPLES_DIR
    )

    output_directory = (
        tmp_path / "batch"
    )

    exported = export_batch_result(
        result,
        output_directory,
    )

    # --------------------------------------------------------
    # Files exist
    # --------------------------------------------------------

    assert exported["json"].exists()

    assert exported["excel"].exists()

    assert exported["summary"].exists()

    # --------------------------------------------------------
    # Paths
    # --------------------------------------------------------

    assert (
        exported["json"].name
        == "invoices.json"
    )

    assert (
        exported["excel"].name
        == "InvoiceIQ.xlsx"
    )

    assert (
        exported["summary"].name
        == "batch_summary.json"
    )
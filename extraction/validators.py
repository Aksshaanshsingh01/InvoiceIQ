"""
InvoiceIQ - Invoice Validation Engine

Validates the structured Invoice object produced by
invoice_extractor.py.

Validation checks:

1. Required fields
2. Item quantity × rate = taxable value
3. Tax calculations
4. Total tax
5. Grand total
6. Received amount
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .invoice_extractor import Invoice


# ============================================================
# Configuration
# ============================================================

TOLERANCE = 0.02


# ============================================================
# Validation Result
# ============================================================

@dataclass
class ValidationResult:
    status: str = "VALID"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(
        self,
        message: str,
    ) -> None:

        self.errors.append(message)
        self.status = "INVALID"

    def add_warning(
        self,
        message: str,
    ) -> None:

        self.warnings.append(message)

        if self.status == "VALID":
            self.status = "WARNING"


# ============================================================
# Utility
# ============================================================

def values_match(
    actual: float,
    expected: float,
    tolerance: float = TOLERANCE,
) -> bool:

    return abs(
        actual - expected
    ) <= tolerance


# ============================================================
# Required Fields
# ============================================================

def validate_required_fields(
    invoice: Invoice,
    result: ValidationResult,
) -> None:

    if not invoice.invoice_number:
        result.add_error(
            "Invoice number is missing."
        )

    if not invoice.invoice_date:
        result.add_error(
            "Invoice date is missing."
        )

    if not invoice.seller:
        result.add_error(
            "Seller information is missing."
        )

    if not invoice.buyer:
        result.add_error(
            "Buyer information is missing."
        )

    if not invoice.items:
        result.add_error(
            "No invoice items were extracted."
        )


# ============================================================
# Item Validation
# ============================================================

def validate_items(
    invoice: Invoice,
    result: ValidationResult,
) -> None:

    for index, item in enumerate(
        invoice.items,
        start=1,
    ):

        if not item.material_name:
            result.add_error(
                f"Item {index}: "
                "Material name is missing."
            )

        if not item.hsn:
            result.add_warning(
                f"Item {index}: "
                "HSN code is missing."
            )

        if item.quantity <= 0:
            result.add_error(
                f"Item {index}: "
                "Quantity must be greater than zero."
            )

        if item.rate < 0:
            result.add_error(
                f"Item {index}: "
                "Rate cannot be negative."
            )

        if item.taxable_value < 0:
            result.add_error(
                f"Item {index}: "
                "Taxable value cannot be negative."
            )

        # ----------------------------------------------------
        # Quantity × Rate
        # ----------------------------------------------------

        calculated_taxable = round(
            item.quantity * item.rate,
            2,
        )

        if not values_match(
            calculated_taxable,
            item.taxable_value,
        ):

            result.add_error(
                f"Item {index}: "
                "Taxable value mismatch. "
                f"Expected "
                f"₹{calculated_taxable:.2f}, "
                f"but extracted "
                f"₹{item.taxable_value:.2f}."
            )


# ============================================================
# Tax Validation
# ============================================================

def validate_taxes(
    invoice: Invoice,
    result: ValidationResult,
) -> None:

    taxable_value = round(
        sum(
            item.taxable_value
            for item in invoice.items
        ),
        2,
    )

    calculated_total_tax = 0.0

    for tax in invoice.taxes:

        if tax.rate < 0:
            result.add_error(
                f"{tax.type}: "
                "Tax rate cannot be negative."
            )

        if tax.amount < 0:
            result.add_error(
                f"{tax.type}: "
                "Tax amount cannot be negative."
            )

        expected_tax = round(
            taxable_value
            * tax.rate
            / 100,
            2,
        )

        calculated_total_tax += (
            tax.amount
        )

        if not values_match(
            tax.amount,
            expected_tax,
        ):

            result.add_error(
                f"{tax.type}: "
                "Tax calculation mismatch. "
                f"Expected "
                f"₹{expected_tax:.2f} "
                f"for {tax.rate}%, "
                f"but extracted "
                f"₹{tax.amount:.2f}."
            )

    calculated_total_tax = round(
        calculated_total_tax,
        2,
    )

    # --------------------------------------------------------
    # Compare sum of tax components with invoice total tax.
    # --------------------------------------------------------

    if not values_match(
        calculated_total_tax,
        invoice.total_tax,
    ):

        result.add_error(
            "Total tax mismatch. "
            f"Individual taxes = "
            f"₹{calculated_total_tax:.2f}, "
            f"invoice total tax = "
            f"₹{invoice.total_tax:.2f}."
        )


# ============================================================
# Grand Total Validation
# ============================================================

def validate_grand_total(
    invoice: Invoice,
    result: ValidationResult,
) -> None:

    taxable_value = round(
        sum(
            item.taxable_value
            for item in invoice.items
        ),
        2,
    )

    expected_total = round(
        taxable_value
        + invoice.total_tax
        + invoice.round_off,
        2,
    )

    if not values_match(
        expected_total,
        invoice.total_amount,
    ):

        result.add_error(
            "Grand total mismatch. "
            f"Expected "
            f"₹{expected_total:.2f}, "
            f"but extracted total = "
            f"₹{invoice.total_amount:.2f}."
        )


# ============================================================
# Received Amount Validation
# ============================================================

def validate_received_amount(
    invoice: Invoice,
    result: ValidationResult,
) -> None:

    if invoice.received_amount < 0:

        result.add_error(
            "Received amount cannot be negative."
        )

    if invoice.received_amount > (
        invoice.total_amount
        + TOLERANCE
    ):

        result.add_error(
            f"Received amount "
            f"₹{invoice.received_amount:.2f} "
            f"is greater than invoice total "
            f"₹{invoice.total_amount:.2f}."
        )


# ============================================================
# Main Validation Function
# ============================================================

def validate_invoice(
    invoice: Invoice,
) -> ValidationResult:

    result = ValidationResult()

    validate_required_fields(
        invoice,
        result,
    )

    validate_items(
        invoice,
        result,
    )

    validate_taxes(
        invoice,
        result,
    )

    validate_grand_total(
        invoice,
        result,
    )

    validate_received_amount(
        invoice,
        result,
    )

    return result


# ============================================================
# Display
# ============================================================

def print_validation_result(
    result: ValidationResult,
) -> None:

    print("\n" + "=" * 60)
    print("INVOICE VALIDATION")
    print("=" * 60)

    print(
        f"Status: {result.status}"
    )

    if result.errors:

        print("\nERRORS:")

        for error in result.errors:
            print(f"  ❌ {error}")

    if result.warnings:

        print("\nWARNINGS:")

        for warning in result.warnings:
            print(f"  ⚠️  {warning}")

    if (
        not result.errors
        and not result.warnings
    ):

        print(
            "\n  ✅ All validation checks passed."
        )

    print("=" * 60)


# ============================================================
# Standalone Validation Test
# ============================================================

if __name__ == "__main__":

    from pathlib import Path

    from .invoice_extractor import extract_invoice

    project_root = (
        Path(__file__)
        .resolve()
        .parent
        .parent
    )

    sample_files = [
        project_root
        / "samples"
        / "Purchase Invoice 4.pdf",

        project_root
        / "samples"
        / "Sale Invoice 4.pdf",
    ]

    for pdf_file in sample_files:

        print("\n")
        print("#" * 60)
        print(
            f"Testing: {pdf_file.name}"
        )
        print("#" * 60)

        try:

            invoice = extract_invoice(
                pdf_file
            )

            print(
                f"Invoice No: "
                f"{invoice.invoice_number}"
            )

            print(
                f"Type:       "
                f"{invoice.invoice_type}"
            )

            print(
                f"Total:      "
                f"₹{invoice.total_amount:.2f}"
            )

            result = validate_invoice(
                invoice
            )

            print_validation_result(
                result
            )

        except Exception as error:

            print(
                f"❌ Validation test failed: "
                f"{error}"
            )

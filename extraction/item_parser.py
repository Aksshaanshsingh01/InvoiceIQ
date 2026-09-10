"""InvoiceIQ - Item Parser."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .table_parser import TableSection, parse_sections


@dataclass
class ParsedItem:
    material_name: str
    hsn: str
    quantity: float
    unit: str
    rate: float
    tax_amount: float
    tax_rate: float
    amount: float


def parse_money(value: str) -> float:
    value = value.replace("₹", "").replace(",", "").strip()
    return float(value)


def parse_percentage(value: str) -> float:
    value = value.replace("(", "").replace(")", "").replace("%", "").strip()
    return float(value)


def parse_quantity_unit(value: str) -> tuple[float, str]:
    match = re.fullmatch(r"([\d,.]+)\s+(.+)", value.strip())
    if not match:
        raise ValueError(f"Invalid quantity/unit: {value}")
    return float(match.group(1).replace(",", "")), match.group(2).strip()


def is_hsn(value: str) -> bool:
    return bool(re.fullmatch(r"\d{6,8}", value.strip()))


def is_money(value: str) -> bool:
    return bool(re.fullmatch(r"₹?\s*[\d,]+(?:\.\d+)?", value.strip()))


def is_percentage(value: str) -> bool:
    return bool(re.fullmatch(r"\(?\s*\d+(?:\.\d+)?%\s*\)?", value.strip()))


def _is_quantity_line(value: str) -> bool:
    return bool(re.fullmatch(r"[\d,.]+\s+[A-Za-z][A-Za-z ./-]*", value.strip()))


def _is_serial(value: str) -> bool:
    return bool(re.fullmatch(r"\d+", value.strip()))


def _looks_like_header(value: str) -> bool:
    return value.strip().upper() in {
        "S.NO.", "S.NO", "S NO.", "S NO", "ITEMS", "ITEM", "HSN", "HSN/SAC",
        "HSN NO.", "QTY.", "QTY", "QUANTITY", "RATE", "TAX", "AMOUNT", "TOTAL",
        "ROUND OFF", "RECEIVED AMOUNT", "SHIP TO", "IGST", "CGST", "SGST", "SUBTOTAL",
    }


def _is_inline_hsn_quantity(value: str) -> bool:
    return bool(re.fullmatch(r"\d{6,8}\s+[\d,.]+\s+[A-Za-z][A-Za-z ./-]*", value.strip()))


def _parse_inline_hsn_quantity(value: str) -> tuple[str, float, str]:
    match = re.fullmatch(r"(\d{6,8})\s+([\d,.]+)\s+([A-Za-z][A-Za-z ./-]*)", value.strip())
    if not match:
        raise ValueError(f"Invalid inline HSN/quantity: {value}")
    return match.group(1), float(match.group(2).replace(",", "")), match.group(3).strip()


def find_item_blocks(section: TableSection) -> list[list[str]]:
    """Split the item table on actual serial-number rows.

    Serial numbers are the strongest row-boundary signal in the supplied
    Purchase and Sale PDFs. HSN/quantity are then parsed inside each block.
    This avoids stealing the preceding item's numeric values when the second
    HSN occurs later in the extracted PDF text.
    """
    lines = [line.strip() for line in section.lines if line.strip()]
    if not lines:
        raise ValueError("No item rows found in item table.")

    # Find serial numbers after the table header. Ignore numeric values such as
    # HSN codes and quantities because those are not standalone integer lines.
    serials: list[int] = []
    for i, line in enumerate(lines):
        if not _is_serial(line):
            continue
        number = int(line)
        # A real item serial is normally followed by descriptive/HSN/quantity
        # content. Avoid treating a stray numeric total as an item boundary.
        lookahead = lines[i + 1:i + 7]
        if any(is_hsn(x) or _is_quantity_line(x) or not is_money(x) for x in lookahead):
            if number == len(serials) + 1 or not serials:
                serials.append(i)

    if serials:
        blocks: list[list[str]] = []
        for n, start in enumerate(serials):
            end = serials[n + 1] if n + 1 < len(serials) else len(lines)
            block = lines[start:end]
            # Round-off belongs after the final item, not to the item itself.
            round_idx = next((j for j, x in enumerate(block) if x.upper() == "ROUND OFF"), None)
            if round_idx is not None:
                block = block[:round_idx]
            if block:
                blocks.append(block)
        if blocks:
            return blocks

    # Fallback for a table without serial numbers: locate HSN anchors.
    candidates: list[int] = []
    for i, line in enumerate(lines):
        if is_hsn(line) and any(_is_quantity_line(x) for x in lines[i + 1:i + 7]):
            candidates.append(i)
        elif _is_inline_hsn_quantity(line):
            candidates.append(i)

    if not candidates:
        raise ValueError("No item rows found in item table.")

    blocks = []
    for n, start in enumerate(candidates):
        end = candidates[n + 1] if n + 1 < len(candidates) else len(lines)
        # Include a small preceding descriptive window for material names.
        blocks.append(lines[max(0, start - 3):end])
    return blocks


def _locate_hsn_quantity(lines: list[str], item_number: int) -> tuple[int, str, float, str]:
    for i, line in enumerate(lines):
        if _is_inline_hsn_quantity(line):
            hsn, qty, unit = _parse_inline_hsn_quantity(line)
            return i, hsn, qty, unit
        if is_hsn(line):
            for j in range(i + 1, min(i + 7, len(lines))):
                if _is_quantity_line(lines[j]):
                    qty, unit = parse_quantity_unit(lines[j])
                    return i, line, qty, unit
    raise ValueError(f"Item {item_number}: HSN and quantity could not be identified. Block: {lines}")


def parse_item_block(block: list[str], item_number: int) -> ParsedItem:
    lines = [x.strip() for x in block if x.strip()]
    if not lines:
        raise ValueError(f"Item {item_number}: empty item block.")

    hsn_index, hsn, quantity, unit = _locate_hsn_quantity(lines, item_number)

    # Material is between the serial/header and the HSN. For inline HSN rows,
    # material is whatever descriptive text precedes the inline row.
    material_parts: list[str] = []
    for x in lines[:hsn_index]:
        if _is_serial(x) or _looks_like_header(x):
            continue
        if is_money(x) or is_percentage(x) or _is_quantity_line(x):
            continue
        material_parts.append(x)
    material_name = " ".join(material_parts).strip()
    if not material_name:
        raise ValueError(f"Item {item_number}: Material name not found.")

    percentage_indices = [i for i, x in enumerate(lines) if is_percentage(x)]
    if not percentage_indices:
        raise ValueError(f"Item {item_number}: Tax rate not found.")
    tax_rate_index = percentage_indices[0]
    tax_rate = parse_percentage(lines[tax_rate_index])

    # Monetary values after quantity and before tax rate are candidates for
    # rate/tax. The item amount is normally the first monetary value after tax.
    qty_indices = {i for i, x in enumerate(lines) if _is_quantity_line(x)}
    numeric: list[tuple[int, float]] = []
    for i, line in enumerate(lines):
        if i <= hsn_index or i in qty_indices or is_percentage(line):
            continue
        if is_money(line):
            numeric.append((i, parse_money(line)))

    before_tax = [(i, v) for i, v in numeric if i < tax_rate_index]
    after_tax = [(i, v) for i, v in numeric if i > tax_rate_index]

    rate = tax_amount = None
    rate_index = None
    tax_index = None

    # In the known PDFs the values are rate, tax, (tax rate), amount. Validate
    # the pair mathematically rather than relying only on column positions.
    for a, (i1, v1) in enumerate(before_tax):
        expected_tax = quantity * v1 * tax_rate / 100.0
        for i2, v2 in before_tax[a + 1:]:
            if abs(v2 - expected_tax) <= max(1.0, abs(expected_tax) * 0.01):
                rate, tax_amount = v1, v2
                rate_index, tax_index = i1, i2
                break
        if rate is not None:
            break

    # Handle a compact line containing rate and tax.
    if rate is None:
        for i, line in enumerate(lines):
            if i <= hsn_index or i >= tax_rate_index:
                continue
            values = re.findall(r"[\d,]+(?:\.\d+)?", line)
            if len(values) >= 2:
                v1 = parse_money(values[0])
                v2 = parse_money(values[1])
                expected_tax = quantity * v1 * tax_rate / 100.0
                if abs(v2 - expected_tax) <= max(1.0, abs(expected_tax) * 0.01):
                    rate, tax_amount = v1, v2
                    rate_index = tax_index = i
                    break

    if rate is None:
        # Conservative fallback only when exactly one monetary candidate exists
        # before the tax rate. Never borrow a value from another item.
        if len(before_tax) == 1:
            rate_index, rate = before_tax[0]
            tax_amount = round(quantity * rate * tax_rate / 100.0, 2)
        else:
            raise ValueError(f"Item {item_number}: Rate not found. Block: {block}")

    amount = after_tax[0][1] if after_tax else round(quantity * rate + tax_amount, 2)

    return ParsedItem(
        material_name=material_name,
        hsn=hsn,
        quantity=quantity,
        unit=unit,
        rate=rate,
        tax_amount=tax_amount,
        tax_rate=tax_rate,
        amount=amount,
    )


def parse_items(section: TableSection) -> list[ParsedItem]:
    blocks = find_item_blocks(section)
    return [parse_item_block(block, index) for index, block in enumerate(blocks, start=1)]


def print_items(items: list[ParsedItem]) -> None:
    print("\n" + "=" * 80)
    print("PARSED ITEMS")
    print("=" * 80)
    for index, item in enumerate(items, start=1):
        print(f"\nItem {index}")
        print(f"  Material     : {item.material_name}")
        print(f"  HSN          : {item.hsn}")
        print(f"  Quantity     : {item.quantity}")
        print(f"  Unit         : {item.unit}")
        print(f"  Rate         : ₹{item.rate:.2f}")
        print(f"  Tax Rate     : {item.tax_rate}%")
        print(f"  Tax Amount   : ₹{item.tax_amount:.2f}")
        print(f"  Item Amount  : ₹{item.amount:.2f}")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    sample_files = [
        project_root / "samples" / "Purchase Invoice 4.pdf",
        project_root / "samples" / "Sale Invoice 4.pdf",
    ]
    for pdf_file in sample_files:
        try:
            sections = parse_sections(pdf_file)
            print(f"\nFILE: {pdf_file.name}")
            print_items(parse_items(sections.item_table))
        except Exception as error:
            print(f"\nFailed to parse {pdf_file.name}: {error}")

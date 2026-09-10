from pathlib import Path

import pymupdf


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLES_DIR = PROJECT_ROOT / "samples"

FILES = [
    SAMPLES_DIR / "Purchase Invoice 4.pdf",
    SAMPLES_DIR / "Sale Invoice 4.pdf",
]


for pdf_path in FILES:

    print("\n")
    print("=" * 100)
    print(f"FILE: {pdf_path.name}")
    print("=" * 100)

    document = pymupdf.open(pdf_path)

    try:

        for page_number, page in enumerate(
            document,
            start=1,
        ):

            print("\n")
            print("-" * 100)
            print(f"PAGE {page_number}")
            print("-" * 100)

            text = page.get_text("text")

            lines = text.splitlines()

            for index, line in enumerate(lines):

                line = line.strip()

                if not line:
                    continue

                print(
                    f"{index:04d}: {line}"
                )

    finally:

        document.close()
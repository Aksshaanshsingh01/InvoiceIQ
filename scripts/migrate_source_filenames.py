from pathlib import Path

from database.db import get_firestore_client


def main() -> None:
    client = get_firestore_client()

    collection = client.collection("invoices")
    documents = collection.stream()

    updated = 0

    for document in documents:
        data = document.to_dict() or {}

        if data.get("source_filename"):
            print(f"SKIP  {document.id}")
            continue

        source_file = data.get("source_file")

        if not source_file:
            print(f"SKIP  {document.id} - no source_file")
            continue

        source_filename = Path(str(source_file)).name

        document.reference.update({
            "source_filename": source_filename,
        })

        updated += 1

        print(
            f"UPDATE {document.id} -> {source_filename}"
        )

    print()
    print(f"Migration complete. Updated: {updated}")


if __name__ == "__main__":
    main()

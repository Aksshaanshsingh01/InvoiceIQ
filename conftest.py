import os

# Force the entire pytest suite onto an isolated Firestore collection.
# This must happen before database.db is imported.
os.environ["INVOICEIQ_FIRESTORE_COLLECTION"] = "invoices_test"

import pytest

from database.db import FIRESTORE_COLLECTION, get_firestore_client


# Safety guard: never allow the test fixture to touch production data.
assert FIRESTORE_COLLECTION == "invoices_test"


def _clear_test_collection() -> None:
    client = get_firestore_client()
    collection = client.collection(FIRESTORE_COLLECTION)

    for document in collection.stream():
        document.reference.delete()


@pytest.fixture(autouse=True)
def isolate_firestore():
    """Give every test a clean Firestore collection."""
    _clear_test_collection()

    yield

    _clear_test_collection()

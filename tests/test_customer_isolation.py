import os

os.environ["MILVUS_COLLECTION"] = "customer_summaries_test"

import pandas as pd

from app.config import get_settings
from app.rag.document_builder import build_documents_from_df
from app.rag.milvus_store import ingest_documents
from app.rag.retriever import retrieve_for_customer


def main():
    settings = get_settings()

    # Load only 10 sample records
    df = pd.read_csv(
        settings.dataset_path,
        nrows=10,
        low_memory=False,
    )

    documents = build_documents_from_df(df)

    # Use the first two customers for isolation testing
    customer_a = str(documents[0].metadata["user_id"])
    customer_b = str(documents[1].metadata["user_id"])

    print("Customer A:", customer_a)
    print("Customer B:", customer_b)

    # Recreate only the test collection and ingest sample documents
    count = ingest_documents(
        documents,
        batch_size=5,
        drop_old=True,
    )

    print("Documents indexed:", count)

    # Query as Customer A
    results_a = retrieve_for_customer(
        query="customer subscription and payment information",
        user_id=customer_a,
    )

    # Query as Customer B
    results_b = retrieve_for_customer(
        query="customer subscription and payment information",
        user_id=customer_b,
    )

    ids_a = {
        str(doc.metadata.get("user_id"))
        for doc in results_a
    }

    ids_b = {
        str(doc.metadata.get("user_id"))
        for doc in results_b
    }

    print("\nCustomer A retrieved IDs:", ids_a)
    print("Customer B retrieved IDs:", ids_b)

    # Both customers should receive their own records
    assert results_a, "No results returned for Customer A"
    assert results_b, "No results returned for Customer B"

    assert ids_a == {customer_a}, (
        f"Customer A received unexpected records: {ids_a}"
    )

    assert ids_b == {customer_b}, (
        f"Customer B received unexpected records: {ids_b}"
    )

    assert customer_a not in ids_b, (
        "Customer B received Customer A's record!"
    )

    assert customer_b not in ids_a, (
        "Customer A received Customer B's record!"
    )

    print("\nCustomer isolation test passed!")


if __name__ == "__main__":
    main()
    
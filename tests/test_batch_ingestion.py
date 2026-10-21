import os

os.environ["MILVUS_COLLECTION"] = "customer_summaries_test"

import pandas as pd

from app.config import get_settings
from app.rag.document_builder import build_documents_from_df
from app.rag.milvus_store import ingest_documents
from app.rag.retriever import retrieve_for_customer


def main():
    settings = get_settings()

    # Load a small dataset sample
    df = pd.read_csv(
        settings.dataset_path,
        nrows=10,
        low_memory=False,
    )

    documents = build_documents_from_df(df)

    expected_ids = {
        str(doc.metadata["user_id"])
        for doc in documents
    }

    print("Documents prepared:", len(documents))
    print("Unique customer IDs:", len(expected_ids))

    # Insert documents in batches of five
    count = ingest_documents(
        documents,
        batch_size=5,
        drop_old=True,
    )

    print("Documents indexed:", count)

    assert count == len(documents), "Incorrect ingestion count"
    assert len(expected_ids) == len(documents), "Duplicate customer IDs"

    # Verify retrieval for every customer
    retrieved_ids = set()

    for customer_id in expected_ids:
        results = retrieve_for_customer(
            query="customer account subscription payment details",
            user_id=customer_id,
        )

        assert results, f"No results for customer {customer_id}"

        result_ids = {
            str(doc.metadata.get("user_id"))
            for doc in results
        }

        assert result_ids == {customer_id}, (
            f"Unexpected customer data returned for {customer_id}: "
            f"{result_ids}"
        )

        retrieved_ids.update(result_ids)

    assert retrieved_ids == expected_ids, (
        "Some customer records were not retrieved"
    )

    print("\nBatch ingestion test passed!")
    print("Expected customers:", len(expected_ids))
    print("Verified customers:", len(retrieved_ids))


if __name__ == "__main__":
    main()
import os

# Use a dedicated test collection.
# Set this BEFORE importing application modules.
os.environ["MILVUS_COLLECTION"] = "customer_summaries_test"

import pandas as pd

from app.config import get_settings
from app.rag.document_builder import build_documents_from_df
from app.rag.milvus_store import ingest_documents
from app.rag.retriever import retrieve_for_customer


def main():
    settings = get_settings()

    # Read only 10 rows instead of loading the entire dataset.
    df = pd.read_csv(
        settings.dataset_path,
        nrows=10,
        low_memory=False,
    )

    print("Sample records loaded:", len(df))

    documents = build_documents_from_df(df)

    print("Documents created:", len(documents))
    print("First customer ID:", documents[0].metadata["user_id"])
    print("Embedding text preview:")
    print(documents[0].page_content[:300])

    # Recreate only the dedicated test collection.
    count = ingest_documents(
        documents,
        batch_size=10,
        drop_old=True,
    )

    print("Documents indexed:", count)

    customer_id = str(documents[0].metadata["user_id"])

    results = retrieve_for_customer(
        query="customer subscription and payment information",
        user_id=customer_id,
    )

    print("Retrieved documents:", len(results))

    for doc in results:
        print("Retrieved customer:", doc.metadata.get("user_id"))
        print("Retrieved metadata:", doc.metadata)

    assert results, "No documents retrieved!"

    assert all(
        str(doc.metadata.get("user_id")) == customer_id
        for doc in results
    ), "Customer isolation test failed!"

    print("Dataset ingestion test passed!")


if __name__ == "__main__":
    main()
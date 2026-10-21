import os

os.environ["MILVUS_COLLECTION"] = "customer_summaries_test"

import pandas as pd

from app.config import get_settings
from app.rag.document_builder import build_documents_from_df
from app.rag.milvus_store import ingest_documents
from app.rag.retriever import retrieve_for_customer


def main():
    settings = get_settings()

    # Load a small sample
    df = pd.read_csv(
        settings.dataset_path,
        nrows=10,
        low_memory=False,
    )

    documents = build_documents_from_df(df)

    # Recreate only the test collection
    ingest_documents(
        documents,
        batch_size=5,
        drop_old=True,
    )

    customer_id = str(documents[0].metadata["user_id"])

    test_queries = [
        "What is the customer's subscription plan and status?",
        "What are the customer's payment attempts and net revenue?",
        "What are the customer's usage events and login events?",
    ]

    for query in test_queries:
        print("\n" + "=" * 60)
        print("Query:", query)

        results = retrieve_for_customer(
            query=query,
            user_id=customer_id,
        )

        print("Results found:", len(results))

        if not results:
            print("No relevant document retrieved.")
            continue

        for doc in results:
            print("Customer ID:", doc.metadata.get("user_id"))
            print("Document type:", doc.metadata.get("document_type"))
            print("Retrieved text preview:")
            print(doc.page_content[:500])

            assert str(doc.metadata.get("user_id")) == customer_id, (
                "Customer isolation failed!"
            )

    print("\nRetrieval quality smoke test completed.")


if __name__ == "__main__":
    main()
from langchain_core.documents import Document
from app.rag.milvus_store import ingest_documents
from app.rag.retriever import retrieve_for_customer

# Create sample customer documents
documents = [
    Document(
        page_content="Customer CUST_TEST_001 has a high reward balance "
        "and frequently redeems loyalty points.",
        metadata={"user_id": "CUST_TEST_001"},
    ),
    Document(
        page_content="Customer CUST_TEST_002 has a low reward balance "
        "and rarely redeems loyalty points.",
        metadata={"user_id": "CUST_TEST_002"},
    ),
]

# Insert documents into Milvus
count = ingest_documents(documents, drop_old=False)
print(f"\nDocuments indexed: {count}")

# Retrieve documents for the first customer
results = retrieve_for_customer(
    query="What is the customer's reward balance and redemption behavior?",
    user_id="CUST_TEST_001",
)

print(f"\nDocuments retrieved for CUST_TEST_001: {len(results)}")

for doc in results:
    print("User ID:", doc.metadata.get("user_id"))
    print("Content:", doc.page_content)

# Verify customer data isolation
assert all(
    doc.metadata.get("user_id") == "CUST_TEST_001"
    for doc in results
), "Customer data isolation failed!"

print("\nCustomer data isolation check passed!")
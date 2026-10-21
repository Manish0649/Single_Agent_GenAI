import os

os.environ["MILVUS_COLLECTION"] = "customer_summaries_test"

from pymilvus import Collection, connections, utility
from app.config import get_settings


settings = get_settings()

connections.connect(
    alias="default",
    uri=settings.milvus_uri,
    token=settings.milvus_token or "",
)

collection_name = settings.milvus_collection

print("Collection:", collection_name)

if not utility.has_collection(collection_name):
    print("Collection does not exist!")
else:
    collection = Collection(collection_name)

    print("\nCollection schema:")
    for field in collection.schema.fields:
        print({
            "name": field.name,
            "type": str(field.dtype),
            "is_primary": field.is_primary,
            "params": field.params,
        })

    print("\nDynamic fields enabled:")
    print(collection.schema.enable_dynamic_field)

    print("\nTotal entities:")
    print(collection.num_entities)

    collection.load()

    print("\nStored records:")
    rows = collection.query(
        expr='pk != ""',
        output_fields=["pk", "text", "$meta"],
        limit=3,
    )

    for row in rows:
        print(row)
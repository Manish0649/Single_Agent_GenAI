from app.rag.embeddings import get_embeddings


def main():
    print("Initializing local embeddings...")

    embeddings = get_embeddings()

    print("Generating test embedding...")

    vector = embeddings.embed_query(
        "This is a test customer subscription record."
    )

    print("Embedding generated successfully!")
    print("Vector dimensions:", len(vector))
    print("First five values:", vector[:5])


if __name__ == "__main__":
    main()
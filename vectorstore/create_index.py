import os

from dotenv import load_dotenv
from qdrant_client.models import Distance, VectorParams

from llm.embeddings import EMBEDDING_DIM
from vectorstore.qdrant_store import get_qdrant_client

load_dotenv()


def create_index(
    collection_name: str,
    embedding_dimensions: int = EMBEDDING_DIM
) -> None:
    """
    Create the Qdrant collection if it doesn't already exist.

    Args:
        collection_name: Collection name.
        embedding_dimensions: Embedding vector size.
    """
    client = get_qdrant_client()

    if client.collection_exists(collection_name):
        print(f"Collection '{collection_name}' already exists.")
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=embedding_dimensions,
            distance=Distance.COSINE
        )
    )

    print(f"Collection '{collection_name}' created successfully.")


if __name__ == "__main__":
    create_index(
        collection_name=os.getenv("QDRANT_COLLECTION", "investor-intelligence")
    )

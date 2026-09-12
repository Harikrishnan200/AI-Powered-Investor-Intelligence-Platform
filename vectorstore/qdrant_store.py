import os
import uuid
from types import SimpleNamespace

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct


def get_qdrant_client() -> QdrantClient:
    """
    Create a Qdrant client.

    Uses a hosted/self-hosted Qdrant instance when QDRANT_URL is set
    (e.g. a free Qdrant Cloud cluster), otherwise falls back to a local,
    on-disk Qdrant instance that needs no server or account at all.
    """
    url = os.getenv("QDRANT_URL")

    if url:
        return QdrantClient(url=url, api_key=os.getenv("QDRANT_API_KEY"))

    return QdrantClient(path=os.getenv("QDRANT_PATH", "./qdrant_data"))


class QdrantVectorStore:
    """Qdrant vector store."""

    def __init__(
        self,
        collection_name: str,
        client: QdrantClient | None = None
    ) -> None:
        self.client = client or get_qdrant_client()
        self.collection_name = collection_name

    def upload_chunks(
        self,
        chunks,
        embeddings,
        company: str,
        year: str,
        source_file: str
    ) -> None:
        """
        Upload chunks to Qdrant.
        """
        points = []

        for chunk in chunks:
            vector = embeddings.embed_query(chunk.page_content)

            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "company": company,
                        "year": str(year),
                        "source_file": source_file,
                        "content": chunk.page_content
                    }
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        print(f"Uploaded {len(points)} chunks.")

    def as_retriever(self, embeddings) -> "Retriever":
        return Retriever(
            client=self.client,
            collection_name=self.collection_name,
            embeddings=embeddings
        )


class Retriever:
    """Retrieves relevant chunks from Qdrant using vector similarity search."""

    def __init__(self, client: QdrantClient, collection_name: str, embeddings) -> None:
        self.client = client
        self.collection_name = collection_name
        self.embeddings = embeddings

    def invoke(
        self,
        query: str,
        company: str | None = None,
        year: int | None = None,
        top_k: int = 20
    ) -> list:
        """Retrieve relevant chunks from Qdrant.
        Returns a list of SimpleNamespace objects with `page_content`.
        """
        query_filter = None

        if company and year:
            query_filter = Filter(
                must=[
                    FieldCondition(key="company", match=MatchValue(value=company)),
                    FieldCondition(key="year", match=MatchValue(value=str(year)))
                ]
            )

        vector = self.embeddings.embed_query(query)

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=query_filter,
            limit=top_k
        ).points

        return [
            SimpleNamespace(page_content=result.payload.get("content", ""))
            for result in results
        ]

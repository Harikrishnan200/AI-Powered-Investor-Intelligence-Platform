import os
import sys
from dotenv import load_dotenv

load_dotenv()

from llm.embeddings import FastEmbedEmbeddings
from vectorstore.qdrant_store import QdrantVectorStore


def search_vectorstore(query: str, top: int = 5):
    collection_name = os.getenv("QDRANT_COLLECTION", "investor-intelligence")

    store = QdrantVectorStore(collection_name=collection_name)
    retriever = store.as_retriever(FastEmbedEmbeddings())
    results = retriever.invoke(query=query, top_k=top)

    print(f"Query: {query!r}")
    print(f"Top: {top}")
    print(f"Results: {len(results)}\n")

    for idx, doc in enumerate(results, start=1):
        snippet = doc.page_content.strip().replace("\n", " ")
        if len(snippet) > 350:
            snippet = snippet[:350].rstrip() + "..."

        print(f"Result {idx}")
        print(f"  content snippet: {snippet}")
        print("  " + "-" * 60)

    if not results:
        print("No results returned. Verify your collection contents or try a different query.")

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m rag.retrieval_debug \"your query here\"")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    search_vectorstore(query)


if __name__ == "__main__":
    main()

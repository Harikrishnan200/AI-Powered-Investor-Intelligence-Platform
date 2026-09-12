import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from llm.embeddings import FastEmbedEmbeddings
from llm.groq_llm import DEFAULT_MODEL, get_groq_client
from vectorstore.qdrant_store import QdrantVectorStore

router = APIRouter()

# Groq's free tier caps requests at ~8000 tokens/minute, so context is kept small.
MAX_CONTEXT_CHARS = 10000
TOP_K = 6

class ChatRequest(BaseModel):
    question: str
    company: str | None = None
    year: int | None = None

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        # Initialize vector store and retriever
        vector_store = QdrantVectorStore(
            collection_name=os.getenv("QDRANT_COLLECTION", "investor-intelligence")
        )
        retriever = vector_store.as_retriever(FastEmbedEmbeddings())

        # Retrieve relevant context
        context = ""
        if request.company and request.year:
            docs = retriever.invoke(
                query=request.question,
                company=request.company,
                year=request.year,
                top_k=TOP_K
            )
        else:
            docs = retriever.invoke(
                query=request.question,
                top_k=TOP_K
            )
        context = "\n\n".join(doc.page_content for doc in docs)[:MAX_CONTEXT_CHARS]

        # Build chat prompt – include retrieved context and the user question
        prompt = f"You are an expert financial analyst. Use the following context from corporate reports to answer the user's question. If the context does not contain relevant information, politely indicate that you do not have enough data.\n\nContext:\n{context}\n\nUser Question: {request.question}\n\nAnswer:"

        client = get_groq_client()
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", DEFAULT_MODEL),
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response.choices[0].message.content
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

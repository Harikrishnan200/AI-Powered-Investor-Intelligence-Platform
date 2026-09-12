import shutil
from fastapi import APIRouter, File, UploadFile
from pathlib import Path
import os
from llm.embeddings import FastEmbedEmbeddings
from vectorstore.qdrant_store import QdrantVectorStore
from ingestion.ingest_documents import ingest_document

router = APIRouter()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...)
):
    upload_dir = Path("data/raw_pdfs")
    upload_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    file_path = upload_dir / file.filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

        # Initialize embeddings and vector store
        embeddings = FastEmbedEmbeddings()

        vector_store = QdrantVectorStore(
            collection_name=os.getenv("QDRANT_COLLECTION", "investor-intelligence")
        )

        ingest_document(
            pdf_path=str(file_path),
            embeddings=embeddings,
            vector_store=vector_store
        )

    return {
        "message": "Document uploaded successfully",
        "file_name": file.filename
    }
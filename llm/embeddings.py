from fastembed import TextEmbedding

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384

_model = None


def _get_model() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=MODEL_NAME)
    return _model


class FastEmbedEmbeddings:
    """Local, free embedding model (no API key, runs on CPU)."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [vector.tolist() for vector in _get_model().embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

import numpy as np
from fastembed import TextEmbedding

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _model


def embed(text: str) -> list:
    vec = np.array(list(_get_model().embed([text]))[0], dtype=float)
    vec = vec / np.linalg.norm(vec)   
    return vec.tolist()


def cosine(a: list, b: list) -> float:
    return float(np.dot(np.array(a), np.array(b)))
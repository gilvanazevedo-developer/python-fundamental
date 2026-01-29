"""
Embeddings Module
Handles text embedding generation using sentence-transformers.
"""

from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np

from config.settings import EMBEDDING_MODEL


class EmbeddingGenerator:
    """Generates embeddings for text using sentence-transformers."""

    _instance = None
    _model = None

    def __new__(cls):
        """Singleton pattern to avoid loading model multiple times."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the embedding model."""
        if self._model is None:
            self._model = SentenceTransformer(EMBEDDING_MODEL)

    def generate(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Generate embeddings for text or list of texts.

        Args:
            text: Single string or list of strings to embed

        Returns:
            numpy array of embeddings
        """
        if isinstance(text, str):
            text = [text]

        embeddings = self._model.encode(
            text,
            convert_to_numpy=True,
            show_progress_bar=False
        )

        return embeddings

    def generate_single(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: String to embed

        Returns:
            List of floats representing the embedding
        """
        embedding = self.generate(text)
        return embedding[0].tolist()

    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: List of strings to embed

        Returns:
            List of embeddings (each embedding is a list of floats)
        """
        embeddings = self.generate(texts)
        return embeddings.tolist()


# Convenience function for quick embedding generation
def get_embedding(text: str) -> List[float]:
    """Generate embedding for a single text."""
    generator = EmbeddingGenerator()
    return generator.generate_single(text)


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts."""
    generator = EmbeddingGenerator()
    return generator.generate_batch(texts)

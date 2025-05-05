
import pickle, faiss, numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path

EMBED_DIM = 768
INDEX_PATH = Path("vector_store/faiss.index")
META_PATH  = Path("vector_store/meta.pkl")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

class Retriever:
    def __init__(self, k=4):
        self.k = k
        self.model = SentenceTransformer(MODEL_NAME)
        self.index = faiss.read_index(str(INDEX_PATH))
        with open(META_PATH, "rb") as f:
            self.meta = pickle.load(f)

    def fetch(self, query: str):
        q_emb = self.model.encode(query.lower(), convert_to_numpy=True)
        scores, idx = self.index.search(q_emb.reshape(1, -1), self.k)
        return [self.meta[i] for i in idx.flatten()]

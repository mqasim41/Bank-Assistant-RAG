import faiss
import pickle
from pathlib import Path
from sentence_transformers import SentenceTransformer
from .logger import setup_logger

# Set up logger for this module
logger = setup_logger("bank_llm.retrieval", "retrieval.log")

class Retriever:
    def __init__(self):
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.index = faiss.read_index("vector_store/faiss.index")
        with open("vector_store/meta.pkl", "rb") as f:
            self.meta = pickle.load(f)
        logger.info("Retriever initialized successfully")

    def search(self, query: str, k: int = 5):
        try:
            query_emb = self.model.encode(query, convert_to_numpy=True)
            scores, indices = self.index.search(query_emb.reshape(1, -1), k)
            results = [self.meta[i] for i in indices[0]]
            logger.debug(f"Retrieved {len(results)} results for query: {query}")
            return results
        except Exception as e:
            logger.error(f"Error during retrieval: {str(e)}")
            return []

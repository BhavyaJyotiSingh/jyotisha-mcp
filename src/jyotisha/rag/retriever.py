"""
RAG Retriever Module — Layer O

Connects to the local ChromaDB vector database and retrieves
relevant classical astrological verses based on chart factors.
"""

from pathlib import Path

try:
    import chromadb
    from chromadb.utils import embedding_functions
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False

class JyotishaRetriever:
    """Retrieves classical texts matching astrological conditions."""
    
    def __init__(self, db_path: str = None):
        if not HAS_CHROMA:
            raise ImportError("ChromaDB is required. Install with: pip install chromadb sentence-transformers")
            
        if db_path is None:
            # Default to project root / db / chromadb
            base_dir = Path(__file__).parent.parent.parent.parent
            self.db_path = str(base_dir / "db" / "chroma")
        else:
            self.db_path = db_path
            
        # Initialize client
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # We use a lightweight, fast local sentence transformer for embeddings
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Get or create the main collection for classical texts
        self.collection = self.client.get_or_create_collection(
            name="classical_texts",
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"}
        )

    def query(
        self, 
        query_text: str, 
        n_results: int = 3, 
        filter_metadata: dict = None
    ) -> list[dict]:
        """
        Query the vector database for relevant verses.
        Example query: "Sun in 10th house in Aries"
        """
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=filter_metadata
        )
        
        formatted_results = []
        if results and results["documents"] and len(results["documents"]) > 0:
            for i in range(len(results["documents"][0])):
                formatted_results.append({
                    "id": results["ids"][0][i],
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if "distances" in results and results["distances"] else 0.0
                })
                
        return formatted_results

    def get_collection_stats(self) -> dict:
        """Get info about the loaded database."""
        return {
            "name": self.collection.name,
            "count": self.collection.count()
        }

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

MOCK_TEXTS = [
    {
        "id": "bphs_7th_lord_1",
        "text": "If the 7th lord is in the 2nd house, the native will have many wives, or will be devoid of a wife, or his wife will be a source of wealth.",
        "metadata": {"source": "BPHS", "chapter": "Effects of 7th Lord"}
    },
    {
        "id": "jaimini_darakaraka_1",
        "text": "The planet with the lowest degree in any sign becomes the Darakaraka. The Darakaraka represents the spouse.",
        "metadata": {"source": "Jaimini Sutras", "chapter": "Karakas"}
    },
    {
        "id": "kp_marriage_1",
        "text": "If the sub-lord of the 7th cusp is a significator of the 2nd, 7th, or 11th houses, marriage is promised.",
        "metadata": {"source": "KP Reader 4", "chapter": "Marriage"}
    },
    {
        "id": "bphs_yoga_1",
        "text": "When lords of 9th and 10th houses conjunct or mutually aspect each other, a powerful Raja Yoga is formed.",
        "metadata": {"source": "BPHS", "chapter": "Raja Yogas"}
    }
]

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
        
        # Prepopulate with mock texts if empty
        if self.collection.count() == 0:
            documents = [t["text"] for t in MOCK_TEXTS]
            metadatas = [t["metadata"] for t in MOCK_TEXTS]
            ids = [t["id"] for t in MOCK_TEXTS]
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
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

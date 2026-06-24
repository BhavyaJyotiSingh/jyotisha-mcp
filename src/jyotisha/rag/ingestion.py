"""
RAG Ingestion - Mock for Phase 5

Ingests classical astrological texts into ChromaDB.
"""

from __future__ import annotations
try:
    import chromadb
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

class RAGIngestion:
    """Mock RAG ingestion engine using an ephemeral ChromaDB client."""
    def __init__(self, persist_dir: str = "./.chroma_db"):
        self.persist_dir = persist_dir
        if HAS_CHROMA:
            self.client = chromadb.Client() # Ephemeral for mock
            self.collection = self.client.get_or_create_collection(name="jyotisha_texts")
        else:
            self.client = None
            self.collection = None

    def ingest_mock_data(self):
        """Ingests the mock texts into the Chroma collection."""
        if not HAS_CHROMA:
            print("ChromaDB not installed. Skipping RAG ingestion.")
            return

        # Check if already populated
        if self.collection.count() > 0:
            return

        documents = [t["text"] for t in MOCK_TEXTS]
        metadatas = [t["metadata"] for t in MOCK_TEXTS]
        ids = [t["id"] for t in MOCK_TEXTS]

        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Ingested {len(documents)} mock rules into ChromaDB.")

if __name__ == "__main__":
    ingester = RAGIngestion()
    ingester.ingest_mock_data()

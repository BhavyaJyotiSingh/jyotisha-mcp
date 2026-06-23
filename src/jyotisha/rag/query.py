"""
RAG Query - Mock for Phase 5

Queries the ChromaDB collection for relevant astrological rules.
"""

from __future__ import annotations
from typing import Optional

try:
    import chromadb
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False

from jyotisha.rag.ingestion import RAGIngestion

class RAGQuery:
    """Queries the RAG knowledge base for astrological rules."""
    
    def __init__(self, ingester: Optional[RAGIngestion] = None):
        if not HAS_CHROMA:
            self.collection = None
            return
            
        # For this mock, we share the ephemeral ingester's client so it stays in memory
        self.ingester = ingester or RAGIngestion()
        self.ingester.ingest_mock_data()
        self.collection = self.ingester.collection

    def query(self, query_text: str, n_results: int = 2) -> list[dict]:
        """
        Query the RAG system for rules related to the query text.
        
        Returns:
            List of dictionaries containing text, source, and chapter.
        """
        if not self.collection:
            return []

        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        formatted_results = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            
            for doc, meta in zip(docs, metas):
                formatted_results.append({
                    "text": doc,
                    "source": meta.get("source", "Unknown"),
                    "chapter": meta.get("chapter", "Unknown")
                })
                
        return formatted_results

if __name__ == "__main__":
    q = RAGQuery()
    print("Querying for 'marriage indicators':")
    res = q.query("marriage indicators")
    for r in res:
        print(f"- {r['text']} (Source: {r['source']})")

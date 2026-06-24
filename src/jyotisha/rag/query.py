"""
RAG Query - Backwards-compatible wrapper around persistent JyotishaRetriever.
"""

from __future__ import annotations
from typing import Optional
from jyotisha.rag.retriever import JyotishaRetriever

class RAGQuery:
    """Wrapper that matches the legacy RAGQuery interface, backed by JyotishaRetriever."""
    
    def __init__(self, retriever: Optional[JyotishaRetriever] = None):
        self.retriever = retriever or JyotishaRetriever()

    def query(self, query_text: str, n_results: int = 2) -> list[dict]:
        """
        Query the persistent RAG system for rules related to the query text.
        
        Returns:
            List of dictionaries containing text, source, and chapter.
        """
        raw_results = self.retriever.query(query_text, n_results=n_results)
        
        formatted_results = []
        for res in raw_results:
            meta = res.get("metadata", {})
            formatted_results.append({
                "text": res.get("text", ""),
                "source": meta.get("source", "Unknown"),
                "chapter": meta.get("chapter", "Unknown")
            })
            
        return formatted_results

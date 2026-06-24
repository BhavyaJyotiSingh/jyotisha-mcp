"""
Hybrid Retriever Module

Combines vector search queries (ChromaDB) and structured ontology queries (NetworkX)
using Reciprocal Rank Fusion (RRF).
"""

from typing import Optional, Any
import re

from jyotisha.rag.retriever import JyotishaRetriever
from jyotisha.knowledge.graph import VedicAstrologyGraph
from jyotisha.knowledge.ontology import NodeType, RelationType
from jyotisha.constants import Planet, SIGN_NAMES

class HybridRetriever:
    """Performs hybrid search over vector store and knowledge graph."""
    
    def __init__(self, retriever: Optional[JyotishaRetriever] = None, graph: Optional[VedicAstrologyGraph] = None):
        self.retriever = retriever or JyotishaRetriever()
        self.graph = graph or VedicAstrologyGraph()
        self.rrf_k = 60  # Standard RRF constant

    def query(self, query_text: str, n_results: int = 3) -> list[dict[str, Any]]:
        """
        Perform hybrid query combining ChromaDB vector search and NetworkX graph search.
        
        Returns a list of matching verses with merged rank scores.
        """
        # 1. Retrieve from vector DB
        vector_results = self.retriever.query(query_text, n_results=n_results * 2)
        
        # 2. Extract entities and retrieve from graph
        entities = self._extract_entities(query_text)
        graph_verses = []
        for ent_id in entities:
            if ent_id in self.graph.graph:
                # Find incoming refersTo relations (typically from Verses)
                incoming = self.graph.get_inverse_relations(ent_id, RelationType.REFERS_TO)
                for inc in incoming:
                    verse_id = inc["source"]
                    node_data = self.graph.graph.nodes.get(verse_id)
                    if node_data and node_data.get("type") == NodeType.VERSE.value:
                        graph_verses.append({
                            "id": verse_id,
                            "text": node_data.get("text", ""),
                            "metadata": {
                                "source": node_data.get("source", "Unknown"),
                                "chapter": node_data.get("chapter", "Unknown"),
                                "verse": node_data.get("verse", "Unknown")
                            }
                        })

        # 3. Reciprocal Rank Fusion (RRF)
        # Create unique map of all doc candidates
        docs_by_id = {}
        vector_rank = {}
        for rank, res in enumerate(vector_results):
            doc_id = res["id"]
            docs_by_id[doc_id] = {
                "id": doc_id,
                "text": res["text"],
                "metadata": res.get("metadata", {})
            }
            vector_rank[doc_id] = rank

        graph_rank = {}
        for rank, res in enumerate(graph_verses):
            doc_id = res["id"]
            docs_by_id[doc_id] = res
            graph_rank[doc_id] = rank

        # Compute RRF score for each document
        rrf_scores = []
        for doc_id, doc in docs_by_id.items():
            score = 0.0
            if doc_id in vector_rank:
                score += 1.0 / (self.rrf_k + vector_rank[doc_id])
            if doc_id in graph_rank:
                score += 1.0 / (self.rrf_k + graph_rank[doc_id])
                
            rrf_scores.append((score, doc))

        # Sort by RRF score descending
        rrf_scores.sort(key=lambda x: x[0], reverse=True)
        
        # Format final results
        final_results = []
        for score, doc in rrf_scores[:n_results]:
            final_results.append({
                "id": doc["id"],
                "text": doc["text"],
                "metadata": doc["metadata"],
                "rrf_score": score
            })
            
        return final_results

    def _extract_entities(self, text: str) -> list[str]:
        """Parse query string for known astrological entities."""
        entities = []
        lower_text = text.lower()
        
        # Detect planets
        for p in Planet:
            if p.value.lower() in lower_text:
                entities.append(p.value)
                
        # Detect signs
        for sign in SIGN_NAMES:
            if sign.lower() in lower_text:
                entities.append(sign)
                
        # Detect houses (e.g. "7th house", "house 7", "seventh house")
        house_mappings = {
            "first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3,
            "fourth": 4, "4th": 4, "fifth": 5, "5th": 5, "sixth": 6, "6th": 6,
            "seventh": 7, "7th": 7, "eighth": 8, "8th": 8, "ninth": 9, "9th": 9,
            "tenth": 10, "10th": 10, "eleventh": 11, "11th": 11, "twelfth": 12, "12th": 12
        }
        
        for term, num in house_mappings.items():
            if term in lower_text:
                entities.append(f"House_{num}")
                
        # Also check simple regex "house \d+"
        match = re.search(r"house\s+(\d+)", lower_text)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 12:
                entities.append(f"House_{num}")
                
        return list(set(entities))

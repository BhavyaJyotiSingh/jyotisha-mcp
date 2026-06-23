"""
Explanation Engine - Layer G

Connects the astrological rules fired during analysis to the RAG system 
to provide textual justification from classical sources.
"""

from __future__ import annotations
from typing import Optional

from jyotisha.rag.query import RAGQuery

class ExplanationEngine:
    """Generates explanations and citations for astrological rules."""
    
    def __init__(self, rag_query: Optional[RAGQuery] = None):
        self.rag = rag_query or RAGQuery()

    def generate_explanation(self, rule_text: str) -> dict:
        """
        Given a programmatic rule that fired (e.g., "7th lord in 2nd house"),
        query the RAG system to find the classical citation.
        """
        citations = self.rag.query(rule_text, n_results=1)
        
        if not citations:
            return {
                "rule": rule_text,
                "citation": "No classical citation found in knowledge base.",
                "source": "General Principle"
            }
            
        best_match = citations[0]
        return {
            "rule": rule_text,
            "citation": best_match["text"],
            "source": f"{best_match['source']} ({best_match['chapter']})"
        }
        
    def explain_school_result(self, school_name: str, rules_fired: list[str]) -> str:
        """
        Format an explanation block for a specific school.
        """
        if not rules_fired:
            return f"[{school_name}]: No specific rules provided."
            
        lines = [f"[{school_name}] Evidence:"]
        for rule in rules_fired:
            exp = self.generate_explanation(rule)
            lines.append(f"  - Logic: {rule}")
            lines.append(f"    Classical Support: \"{exp['citation']}\" - {exp['source']}")
            
        return "\n".join(lines)

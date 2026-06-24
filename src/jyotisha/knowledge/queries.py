"""
Knowledge Graph Queries

Provides domain-specific helper queries on the NetworkX astrology graph.
"""

from typing import Any, Optional
from jyotisha.knowledge.graph import VedicAstrologyGraph
from jyotisha.knowledge.ontology import RelationType

def get_planet_details(graph: VedicAstrologyGraph, planet_name: str) -> dict[str, Any]:
    """Retrieve all ontological details for a planet."""
    if planet_name not in graph.graph:
        return {}
        
    node_data = graph.graph.nodes[planet_name]
    exaltations = graph.get_relations(planet_name, RelationType.EXALTED_IN)
    debilitations = graph.get_relations(planet_name, RelationType.DEBILITATED_IN)
    ruled_signs = graph.get_relations(planet_name, RelationType.RULES_SIGN)
    friends = graph.get_relations(planet_name, RelationType.FRIENDS_WITH)
    enemies = graph.get_relations(planet_name, RelationType.ENEMIES_WITH)
    karaka_for = graph.get_relations(planet_name, RelationType.KARAKA_FOR)
    
    return {
        "name": planet_name,
        "sanskrit": node_data.get("sanskrit", ""),
        "significations": node_data.get("significations", []),
        "rules_signs": [r["target"] for r in ruled_signs],
        "exalted_in": exaltations[0]["target"] if exaltations else None,
        "exaltation_degree": exaltations[0]["attributes"].get("exact_degree") if exaltations else None,
        "debilitated_in": debilitations[0]["target"] if debilitations else None,
        "friends": [f["target"] for f in friends],
        "enemies": [e["target"] for e in enemies],
        "karaka_for_houses": [int(k["target"].split("_")[1]) for k in karaka_for if "_" in k["target"]]
    }

def get_house_ontology(graph: VedicAstrologyGraph, house_number: int) -> dict[str, Any]:
    """Retrieve ontological details for a house (1-12)."""
    house_id = f"House_{house_number}"
    if house_id not in graph.graph:
        return {}
        
    node_data = graph.graph.nodes[house_id]
    
    # Karakas pointing to the house
    karakas = graph.get_inverse_relations(house_id, RelationType.KARAKA_FOR)
    
    # Sign that sits in this house dynamically depends on the chart,
    # but the base ontology stores significations and static lords.
    return {
        "house_number": house_number,
        "significations": node_data.get("significations", []),
        "karakas": [k["source"] for k in karakas]
    }

def find_supporting_verses(graph: VedicAstrologyGraph, node_id: str) -> list[dict[str, Any]]:
    """Retrieve all scriptural verses connected to a specific yoga or concept."""
    if node_id not in graph.graph:
        return []
        
    # Verses that point to/refers to the yoga or concept node
    incoming = graph.get_inverse_relations(node_id, RelationType.REFERS_TO)
    results = []
    for inc in incoming:
        verse_id = inc["source"]
        verse_data = graph.graph.nodes.get(verse_id, {})
        results.append({
            "verse_id": verse_id,
            "text": verse_data.get("text", ""),
            "source": verse_data.get("source", "Unknown"),
            "chapter": verse_data.get("chapter", "Unknown"),
            "verse": verse_data.get("verse", "Unknown")
        })
    return results

import pytest
import json
import os
from pathlib import Path

from jyotisha.knowledge.ontology import NodeType, RelationType
from jyotisha.knowledge.graph import VedicAstrologyGraph
import jyotisha.knowledge.queries as graph_queries
from jyotisha.rag.hybrid import HybridRetriever
from jyotisha.api.server import get_knowledge_relations, get_planet_ontology, get_house_ontology, query_classical_texts

@pytest.fixture
def temp_graph_path(tmp_path):
    return str(tmp_path / "temp_kg.json")

@pytest.fixture
def astrology_graph(temp_graph_path):
    # Returns a pre-populated graph for testing
    return VedicAstrologyGraph(persistence_path=temp_graph_path)

def test_base_ontology_population(astrology_graph):
    # Verify planets exist
    assert "Sun" in astrology_graph.graph
    assert "Saturn" in astrology_graph.graph
    
    # Verify signs exist
    assert "Aries" in astrology_graph.graph
    assert "Pisces" in astrology_graph.graph
    
    # Verify relationship counts and values
    rulers = astrology_graph.get_relations("Sun", RelationType.RULES_SIGN)
    assert len(rulers) == 1
    assert rulers[0]["target"] == "Leo"
    
    friends = astrology_graph.get_relations("Sun", RelationType.FRIENDS_WITH)
    friend_targets = [f["target"] for f in friends]
    assert "Moon" in friend_targets
    assert "Jupiter" in friend_targets

def test_exaltation_and_debilitation(astrology_graph):
    # Sun exalted in Aries at 10 degrees
    ex = astrology_graph.get_relations("Sun", RelationType.EXALTED_IN)
    assert len(ex) == 1
    assert ex[0]["target"] == "Aries"
    assert ex[0]["attributes"]["exact_degree"] == 10.0
    
    # Sun debilitated in Libra
    deb = astrology_graph.get_relations("Sun", RelationType.DEBILITATED_IN)
    assert len(deb) == 1
    assert deb[0]["target"] == "Libra"

def test_graph_serialization(astrology_graph, temp_graph_path):
    # Save, clear, and reload
    astrology_graph.add_node(NodeType.YOGA, "Gajakesari", {"description": "Jupiter in Kendra from Moon"})
    astrology_graph.save()
    
    # Re-instantiate
    reloaded_graph = VedicAstrologyGraph(persistence_path=temp_graph_path)
    assert "Gajakesari" in reloaded_graph.graph
    assert reloaded_graph.graph.nodes["Gajakesari"]["description"] == "Jupiter in Kendra from Moon"

def test_query_helpers(astrology_graph):
    details = graph_queries.get_planet_details(astrology_graph, "Sun")
    assert details["name"] == "Sun"
    assert details["exalted_in"] == "Aries"
    assert details["exaltation_degree"] == 10.0
    assert details["debilitated_in"] == "Libra"
    assert "Leo" in details["rules_signs"]
    assert "Moon" in details["friends"]
    
    house_details = graph_queries.get_house_ontology(astrology_graph, 7)
    assert house_details["house_number"] == 7
    assert "Marriage" in house_details["significations"]
    assert "Venus" in house_details["karakas"]

def test_mock_verses_linking(astrology_graph):
    # Verify mock verses exist as nodes
    assert "bphs_7th_lord_1" in astrology_graph.graph
    assert "kp_marriage_1" in astrology_graph.graph
    
    # Check that they refer to the correct houses
    ref_7th_lord = astrology_graph.get_relations("bphs_7th_lord_1", RelationType.REFERS_TO)
    ref_targets = [r["target"] for r in ref_7th_lord]
    assert "House_7" in ref_targets
    assert "House_2" in ref_targets

    # Query supporting verses for House_7
    supporting = graph_queries.find_supporting_verses(astrology_graph, "House_7")
    supporting_ids = [s["verse_id"] for s in supporting]
    assert "bphs_7th_lord_1" in supporting_ids
    assert "jaimini_darakaraka_1" in supporting_ids
    assert "kp_marriage_1" in supporting_ids

def test_hybrid_entity_extractor():
    retriever = HybridRetriever()
    
    # Check planets
    entities_1 = retriever._extract_entities("Where is the Sun placed?")
    assert "Sun" in entities_1
    
    # Check signs
    entities_2 = retriever._extract_entities("Jupiter transit in Taurus")
    assert "Jupiter" in entities_2
    assert "Taurus" in entities_2
    
    # Check houses
    entities_3 = retriever._extract_entities("7th lord in the second house")
    assert "House_7" in entities_3
    assert "House_2" in entities_3

def test_hybrid_query_rrf(astrology_graph):
    retriever = HybridRetriever(graph=astrology_graph)
    results = retriever.query("ruling planet of 7th house and marriage indicators", n_results=3)
    
    # Should return results
    assert len(results) > 0
    # The top result should have high RRF score
    assert results[0]["rrf_score"] > 0
    # Fields should be correctly structured
    for r in results:
        assert "id" in r
        assert "text" in r
        assert "metadata" in r
        assert "rrf_score" in r

@pytest.mark.asyncio
async def test_mcp_tools_integration():
    # 1. Test get_knowledge_relations
    relations_str = await get_knowledge_relations("Sun")
    relations = json.loads(relations_str)
    assert relations["node_id"] == "Sun"
    assert len(relations["outgoing_relations"]) > 0
    
    # 2. Test get_planet_ontology
    planet_str = await get_planet_ontology("Venus")
    planet = json.loads(planet_str)
    assert planet["name"] == "Venus"
    assert planet["exalted_in"] == "Pisces"
    
    # 3. Test get_house_ontology
    house_str = await get_house_ontology(10)
    house = json.loads(house_str)
    assert house["house_number"] == 10
    assert "Career" in house["significations"]
    
    # 4. Test query_classical_texts (Hybrid RAG)
    texts_str = await query_classical_texts("7th lord in 2nd house", n_results=2)
    texts = json.loads(texts_str)
    assert len(texts) > 0
    assert "rrf_score" in texts[0]

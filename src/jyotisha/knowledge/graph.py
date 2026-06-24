"""
Lightweight Knowledge Graph wrapper using NetworkX.
Provides serialization, querying, and pre-population of Vedic Astrology ontology.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, Any
import networkx as nx

from jyotisha.knowledge.ontology import NodeType, RelationType
from jyotisha.constants import (
    Planet, Sign, SIGN_NAMES, SIGN_LORDS, EXALTATION, DEBILITATION,
    OWN_SIGNS, NATURAL_FRIENDS, NATURAL_ENEMIES, NAKSHATRA_NAMES, NAKSHATRA_LORDS,
    BHAVA_KARAKAS, HOUSE_SIGNIFICATIONS, NAISARGIKA_KARAKAS, SIGN_SANSKRIT,
    SIGN_ELEMENTS, SIGN_MODALITIES, PLANET_SANSKRIT
)

class VedicAstrologyGraph:
    """Wrapper around NetworkX DiGraph for Vedic Astrology ontology."""
    
    def __init__(self, persistence_path: Optional[str] = None):
        self.graph = nx.DiGraph()
        
        if persistence_path is None:
            # Default location: workspace / db / knowledge_graph.json
            base_dir = Path(__file__).parent.parent.parent.parent
            self.persistence_path = base_dir / "db" / "knowledge_graph.json"
        else:
            self.persistence_path = Path(persistence_path)
            
        # Ensure directory exists
        self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or initialize
        if self.persistence_path.exists():
            self.load()
        else:
            self.prepopulate_base_ontology()
            self.save()

    def add_node(self, node_type: NodeType, node_id: str, attributes: Optional[dict[str, Any]] = None):
        """Add a typed node to the knowledge graph."""
        attrs = attributes or {}
        attrs["type"] = node_type.value
        self.graph.add_node(node_id, **attrs)

    def add_edge(
        self, 
        source_id: str, 
        target_id: str, 
        relation_type: RelationType, 
        attributes: Optional[dict[str, Any]] = None
    ):
        """Add a typed directed edge to the knowledge graph."""
        if not self.graph.has_node(source_id):
            raise ValueError(f"Source node '{source_id}' does not exist in the graph.")
        if not self.graph.has_node(target_id):
            raise ValueError(f"Target node '{target_id}' does not exist in the graph.")
            
        attrs = attributes or {}
        attrs["relation"] = relation_type.value
        self.graph.add_edge(source_id, target_id, **attrs)

    def get_relations(self, node_id: str, relation_type: Optional[RelationType] = None) -> list[dict[str, Any]]:
        """Retrieve outgoing relationships from a node."""
        if not self.graph.has_node(node_id):
            return []
            
        results = []
        for target_id in self.graph.successors(node_id):
            edge_data = self.graph.get_edge_data(node_id, target_id)
            if relation_type is None or edge_data.get("relation") == relation_type.value:
                results.append({
                    "source": node_id,
                    "target": target_id,
                    "relation": edge_data.get("relation"),
                    "attributes": {k: v for k, v in edge_data.items() if k != "relation"}
                })
        return results

    def get_inverse_relations(self, node_id: str, relation_type: Optional[RelationType] = None) -> list[dict[str, Any]]:
        """Retrieve incoming relationships to a node."""
        if not self.graph.has_node(node_id):
            return []
            
        results = []
        for source_id in self.graph.predecessors(node_id):
            edge_data = self.graph.get_edge_data(source_id, node_id)
            if relation_type is None or edge_data.get("relation") == relation_type.value:
                results.append({
                    "source": source_id,
                    "target": node_id,
                    "relation": edge_data.get("relation"),
                    "attributes": {k: v for k, v in edge_data.items() if k != "relation"}
                })
        return results

    def save(self):
        """Serialize NetworkX graph to a JSON file."""
        data = nx.readwrite.json_graph.node_link_data(self.graph)
        with open(self.persistence_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load(self):
        """Deserialize NetworkX graph from a JSON file."""
        with open(self.persistence_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.graph = nx.readwrite.json_graph.node_link_graph(data)

    def prepopulate_base_ontology(self):
        """Populate the graph with standard Vedic Astrology constants and relationships."""
        self.graph.clear()
        
        # 1. Add Planets
        for p in Planet:
            sanskrit = PLANET_SANSKRIT.get(p, "")
            significations = NAISARGIKA_KARAKAS.get(p, [])
            self.add_node(
                NodeType.PLANET, 
                p.value, 
                {"sanskrit": sanskrit, "significations": significations}
            )
            
        # 2. Add Signs
        for i, name in enumerate(SIGN_NAMES):
            self.add_node(
                NodeType.SIGN,
                name,
                {
                    "number": i,
                    "sanskrit": SIGN_SANSKRIT[i],
                    "element": SIGN_ELEMENTS[i].value,
                    "modality": SIGN_MODALITIES[i].value
                }
            )
            
        # 3. Add Houses
        for i in range(1, 13):
            self.add_node(
                NodeType.HOUSE,
                f"House_{i}",
                {
                    "number": i,
                    "significations": HOUSE_SIGNIFICATIONS.get(i, [])
                }
            )
            
        # 4. Add Nakshatras
        for i, name in enumerate(NAKSHATRA_NAMES):
            self.add_node(
                NodeType.NAKSHATRA,
                name,
                {
                    "number": i + 1,
                    "lord": NAKSHATRA_LORDS[i].value
                }
            )

        # 5. Connect Sign Lords (Rulers)
        for sign_enum, lord_enum in SIGN_LORDS.items():
            sign_name = SIGN_NAMES[sign_enum.value]
            self.add_edge(lord_enum.value, sign_name, RelationType.RULES_SIGN)

        # 6. Exaltation & Debilitation
        for planet_enum, ex_data in EXALTATION.items():
            sign_name = SIGN_NAMES[ex_data.sign.value]
            self.add_edge(
                planet_enum.value, 
                sign_name, 
                RelationType.EXALTED_IN, 
                {"exact_degree": ex_data.exact_degree}
            )
            
        for planet_enum, deb_sign_enum in DEBILITATION.items():
            sign_name = SIGN_NAMES[deb_sign_enum.value]
            self.add_edge(planet_enum.value, sign_name, RelationType.DEBILITATED_IN)

        # 7. Natural Friendships & Enmities
        for planet_enum, friends in NATURAL_FRIENDS.items():
            for friend in friends:
                self.add_edge(planet_enum.value, friend.value, RelationType.FRIENDS_WITH)
                
        for planet_enum, enemies in NATURAL_ENEMIES.items():
            for enemy in enemies:
                self.add_edge(planet_enum.value, enemy.value, RelationType.ENEMIES_WITH)

        # 8. Bhava Karakas (Significators for Houses)
        for house_num, karakas in BHAVA_KARAKAS.items():
            house_id = f"House_{house_num}"
            for karaka in karakas:
                self.add_edge(karaka.value, house_id, RelationType.KARAKA_FOR)

        # 9. Nakshatra Vimshottari Lords
        for i, name in enumerate(NAKSHATRA_NAMES):
            lord = NAKSHATRA_LORDS[i].value
            self.add_edge(name, lord, RelationType.PLANET_IN_NAKSHATRA)  # Nakshatra points to Vimshottari lord

        # 10. Add Prepopulated Mock Verses and refersTo Relationships
        mock_verses_definitions = [
            {
                "id": "bphs_7th_lord_1",
                "text": "If the 7th lord is in the 2nd house, the native will have many wives, or will be devoid of a wife, or his wife will be a source of wealth.",
                "source": "BPHS",
                "chapter": "Effects of 7th Lord",
                "verse": "1",
                "refers_to": ["House_7", "House_2"]
            },
            {
                "id": "jaimini_darakaraka_1",
                "text": "The planet with the lowest degree in any sign becomes the Darakaraka. The Darakaraka represents the spouse.",
                "source": "Jaimini Sutras",
                "chapter": "Karakas",
                "verse": "1",
                "refers_to": ["House_7"]
            },
            {
                "id": "kp_marriage_1",
                "text": "If the sub-lord of the 7th cusp is a significator of the 2nd, 7th, or 11th houses, marriage is promised.",
                "source": "KP Reader 4",
                "chapter": "Marriage",
                "verse": "1",
                "refers_to": ["House_7", "House_2", "House_11"]
            },
            {
                "id": "bphs_yoga_1",
                "text": "When lords of 9th and 10th houses conjunct or mutually aspect each other, a powerful Raja Yoga is formed.",
                "source": "BPHS",
                "chapter": "Raja Yogas",
                "verse": "1",
                "refers_to": ["House_9", "House_10"]
            }
        ]

        for mv in mock_verses_definitions:
            self.add_node(
                NodeType.VERSE,
                mv["id"],
                {
                    "text": mv["text"],
                    "source": mv["source"],
                    "chapter": mv["chapter"],
                    "verse": mv["verse"]
                }
            )
            for ref in mv["refers_to"]:
                self.add_edge(mv["id"], ref, RelationType.REFERS_TO)

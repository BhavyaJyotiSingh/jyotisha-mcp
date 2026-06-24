"""
Vedic Astrology Knowledge Graph Ontology

Defines the structure, node types, and relationship types for the local NetworkX graph.
"""

from enum import Enum

class NodeType(str, Enum):
    PLANET = "Planet"
    SIGN = "Sign"
    HOUSE = "House"
    NAKSHATRA = "Nakshatra"
    YOGA = "Yoga"
    VERSE = "Verse"
    DASHA = "Dasha"
    REMEDY = "Remedy"

class RelationType(str, Enum):
    # Astronomical/Chart relationships
    PLANET_IN_SIGN = "planetInSign"
    PLANET_IN_HOUSE = "planetInHouse"
    PLANET_IN_NAKSHATRA = "planetInNakshatra"
    RULES_SIGN = "rulesSign"
    RULES_HOUSE = "rulesHouse"
    
    # Dignities and friendships
    EXALTED_IN = "exaltedIn"
    DEBILITATED_IN = "debilitatedIn"
    FRIENDS_WITH = "friendsWith"
    ENEMIES_WITH = "enemiesWith"
    
    # Aspects and Karakatva
    ASPECTS = "aspects"
    CONJUNCTS = "conjuncts"
    KARAKA_FOR = "karakaFor"
    
    # Scriptural / Text citations
    REFERS_TO = "refersTo"
    CITED_IN = "citedIn"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    
    # Interpretations/Timing/Remedies
    ACTIVATES_YOGA = "activatesYoga"
    REMEDIES_FOR = "remediesFor"

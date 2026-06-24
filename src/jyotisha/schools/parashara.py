"""
Parashara School Module — Layer L

Implements traditional Brihat Parashara Hora Shastra (BPHS) analysis.
Integrates Chart, Dasha, and Yoga engines for a unified reading.
"""

from typing import Optional
from datetime import datetime

from jyotisha.models.schemas import Chart, SchoolResult
from jyotisha.engines.yoga import YogaEngine
from jyotisha.engines.dasha import DashaEngine
from jyotisha.constants import BHAVA_KARAKAS, HOUSE_SIGNIFICATIONS

class ParasharaModule:
    """
    Parashara School Analysis Engine.
    """
    
    school_name = "Parashara"
    sources = ["Brihat Parashara Hora Shastra (BPHS)", "Phaladeepika", "Saravali"]
    
    def __init__(self):
        self.yoga_engine = YogaEngine()
        self.dasha_engine = DashaEngine()

    def analyze_chart(self, chart: Chart) -> dict:
        """
        Run full Parashara analysis on a birth chart.
        Returns a comprehensive report dictionary.
        """
        
        # 1. House Analysis (Bhava Phala)
        house_analysis = self._analyze_houses(chart)
        
        # 2. Yoga Detection
        yogas = self.yoga_engine.detect_yogas(chart)
        
        # 3. Dasha Overview (Vimshottari)
        dashas = self.dasha_engine.compute_vimshottari_from_chart(chart, levels=2)
        
        return {
            "school": self.school_name,
            "ascendant_summary": {
                "sign": chart.ascendant.sign,
                "lord": chart.ascendant.lord,
                "lord_dignity": chart.get_planet(chart.ascendant.lord).dignity.status if chart.get_planet(chart.ascendant.lord) else "Unknown",
                "lord_house": chart.get_planet(chart.ascendant.lord).house if chart.get_planet(chart.ascendant.lord) else "Unknown",
            },
            "yogas": [y.model_dump() for y in yogas],
            "house_analysis": house_analysis,
            "current_dasha": self._get_current_dasha_summary(dashas),
            "sources_used": self.sources
        }

    def predict(self, chart: Chart, question: str, target_date: Optional[str] = None) -> SchoolResult:
        """
        Predict timing of an event using Parashara methods (Vimshottari Dasha).
        """
        if not target_date:
            target_date = datetime.now().strftime("%Y-%m-%d")
            
        dashas = self.dasha_engine.compute_vimshottari_from_chart(chart, levels=2)
        query_jd = self.dasha_engine._date_to_jd(target_date)
        current = self.dasha_engine.get_current_dasha(dashas, query_jd)
        
        maha_lord = current.get("mahadasha", {}).get("lord")
        antar_lord = current.get("antardasha", {}).get("lord")
        
        if question.lower() == "marriage":
            lord_7 = chart.get_house_lord(7)
            karaka = "Venus"
            house_7 = chart.get_house(7)
            occupants = house_7.planets_in_house if house_7 else []
            
            # Check if dasha lords match significators
            significators = set([lord_7, karaka] + occupants)
            
            confidence = 0.0
            rules = []
            
            if maha_lord in significators:
                confidence += 0.5
                rules.append(f"Mahadasha lord {maha_lord} signifies marriage.")
            if antar_lord in significators:
                confidence += 0.3
                rules.append(f"Antardasha lord {antar_lord} signifies marriage.")
                
            # Aspect on 7th house or lord
            if maha_lord and house_7 and maha_lord in house_7.aspects_received:
                confidence += 0.2
                rules.append(f"Mahadasha lord {maha_lord} aspects 7th house.")
                
            confidence = min(1.0, confidence)
            
            answer = "Favorable period for marriage." if confidence > 0.5 else "Period does not strongly indicate marriage."
            
            return SchoolResult(
                school=self.school_name,
                answer=answer,
                confidence=round(confidence, 2),
                sources=["BPHS Chapter on Marriage"],
                reasoning=f"Current Dasha is {maha_lord}/{antar_lord}. Significators are {list(significators)}.",
                rules_fired=rules,
                structured_data={
                    "mahadasha": maha_lord,
                    "antardasha": antar_lord,
                    "significators": list(significators)
                }
            )
            
        elif question.lower() == "career":
            lord_10 = chart.get_house_lord(10)
            lord_11 = chart.get_house_lord(11)
            lord_2 = chart.get_house_lord(2)
            house_10 = chart.get_house(10)
            occupants = house_10.planets_in_house if house_10 else []
            
            # Significators: 10th lord, 11th lord, 2nd lord, occupants, and Sun/Mercury/Saturn
            significators = set([lord_10, lord_11, lord_2] + occupants + ["Sun", "Mercury", "Saturn"])
            significators.discard(None)
            
            confidence = 0.0
            rules = []
            
            if maha_lord in significators:
                confidence += 0.4
                rules.append(f"Mahadasha lord {maha_lord} signifies career (10th/11th/2nd connection or natural karaka).")
            if antar_lord in significators:
                confidence += 0.3
                rules.append(f"Antardasha lord {antar_lord} signifies career.")
                
            # Aspect on 10th house
            if maha_lord and house_10 and maha_lord in house_10.aspects_received:
                confidence += 0.2
                rules.append(f"Mahadasha lord {maha_lord} aspects 10th house of profession.")
                
            # Check 10th lord strength
            if lord_10:
                p_lord = chart.get_planet(lord_10)
                if p_lord and p_lord.dignity.is_exalted:
                    confidence += 0.1
                    rules.append(f"10th house lord {lord_10} is Exalted, giving strong professional foundation.")
                elif p_lord and p_lord.dignity.is_own_sign:
                    confidence += 0.05
                    rules.append(f"10th house lord {lord_10} is in its Own Sign.")
            
            confidence = min(1.0, confidence)
            answer = "Favorable period for career progression/gains." if confidence > 0.4 else "Period does not indicate strong career progression."
            
            return SchoolResult(
                school=self.school_name,
                answer=answer,
                confidence=round(confidence, 2),
                sources=["BPHS Chapter on Profession"],
                reasoning=f"Current Dasha is {maha_lord}/{antar_lord}. Significators are {list(significators)}.",
                rules_fired=rules,
                structured_data={
                    "mahadasha": maha_lord,
                    "antardasha": antar_lord,
                    "significators": list(significators)
                }
            )
            
        return SchoolResult(
            school=self.school_name,
            answer="Prediction logic only implemented for marriage and career.",
            confidence=0.0
        )

    def explain(self, result: SchoolResult) -> str:
        """Explain the school's result."""
        return f"[Parashara Explanation]: {result.reasoning}"

    def _analyze_houses(self, chart: Chart) -> list[dict]:
        """Generate analysis for all 12 houses."""
        results = []
        for house in chart.houses:
            lord = chart.get_planet(house.lord)
            
            # Strength heuristic (0-10)
            strength = 5
            if lord:
                if lord.dignity.is_exalted or lord.dignity.is_own_sign:
                    strength += 3
                if lord.dignity.is_debilitated:
                    strength -= 3
                if lord.house in [6, 8, 12]:
                    strength -= 2
                if lord.house in [1, 4, 7, 10, 5, 9]:
                    strength += 2
                    
            strength = max(0, min(10, strength))
            bhavat_bhavam_house = ((2 * house.number - 2) % 12) + 1
            
            results.append({
                "house": house.number,
                "sign": house.sign,
                "lord": house.lord,
                "lord_house": lord.house if lord else None,
                "lord_sign": lord.sign if lord else None,
                "lord_dignity": lord.dignity.status if lord else "Unknown",
                "occupants": house.planets_in_house,
                "aspects_received": house.aspects_received,
                "karakas": [planet.value for planet in BHAVA_KARAKAS.get(house.number, [])],
                "significations": HOUSE_SIGNIFICATIONS.get(house.number, []),
                "bhavat_bhavam_house": bhavat_bhavam_house,
                "bhavat_bhavam_significations": HOUSE_SIGNIFICATIONS.get(
                    bhavat_bhavam_house, []
                ),
                "overall_strength": strength,
            })
        return results

    def _get_current_dasha_summary(self, timeline) -> dict:
        """Get the dasha running today."""
        today = datetime.now().strftime("%Y-%m-%d")
        # Need to convert to JD, using the DashaEngine's helper
        query_jd = self.dasha_engine._date_to_jd(today)
        return self.dasha_engine.get_current_dasha(timeline, query_jd)

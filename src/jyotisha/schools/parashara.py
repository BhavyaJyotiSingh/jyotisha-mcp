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
from jyotisha.constants import HOUSE_SIGNIFICATIONS

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
        Predict timing of an event using Parashara methods (Vimshottari Dasha + transits).
        """
        # A full implementation would check Dasha lords, Antardasha lords, and their connection
        # to the event's significator houses (e.g., House 7 for marriage).
        
        if question.lower() == "marriage":
            lord_7 = chart.get_house_lord(7)
            return SchoolResult(
                school=self.school_name,
                answer="Prediction requires advanced Dasha/Antardasha matching.",
                confidence=0.5,
                sources=["BPHS Chapter on Marriage"],
                reasoning=f"Must check dashas of 7th lord ({lord_7}) and Venus.",
                rules_fired=[]
            )
            
        return SchoolResult(
            school=self.school_name,
            answer="Not implemented for this question type.",
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
            
            results.append({
                "house": house.number,
                "sign": house.sign,
                "lord": house.lord,
                "occupants": house.planets_in_house,
                "aspects_received": house.aspects_received,
                "significations": HOUSE_SIGNIFICATIONS.get(house.number, []),
                "overall_strength": strength,
            })
        return results

    def _get_current_dasha_summary(self, timeline) -> dict:
        """Get the dasha running today."""
        today = datetime.now().strftime("%Y-%m-%d")
        # Need to convert to JD, using the DashaEngine's helper
        query_jd = self.dasha_engine._date_to_jd(today)
        return self.dasha_engine.get_current_dasha(timeline, query_jd)

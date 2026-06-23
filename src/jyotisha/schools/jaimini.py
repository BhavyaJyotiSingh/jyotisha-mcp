"""
Jaimini School Module — Layer M

Implements Jaimini Sutras analysis, including:
- 7 Chara Karakas (Atmakaraka, etc.)
- Rashi Drishti (Sign aspects)
- Arudha Padas
"""

from jyotisha.models.schemas import Chart, ArudhaPada, SchoolResult
from jyotisha.constants import Planet, Modality, SIGN_MODALITIES, SIGN_NAMES
from jyotisha.engines.arudha import ArudhaEngine


class JaiminiModule:
    """
    Jaimini School Analysis Engine.
    """
    school_name = "Jaimini"
    sources = ["Jaimini Sutras"]

    def analyze_chart(self, chart: Chart) -> dict:
        """
        Run full Jaimini analysis on a birth chart.
        """
        karakas = self._compute_chara_karakas(chart)
        rashi_drishti = self._compute_rashi_drishti(chart)
        arudha_engine = ArudhaEngine()
        arudhas = arudha_engine.compute_arudhas(chart)
        
        return {
            "school": self.school_name,
            "chara_karakas": karakas,
            "rashi_drishti": rashi_drishti,
            "arudha_padas": [a.model_dump() for a in arudhas],
            "sources_used": self.sources
        }

    def predict(self, chart: Chart, question: str) -> SchoolResult:
        """
        Generate a prediction based on Jaimini principles.
        """
        karakas = self._compute_chara_karakas(chart)
        
        if question.lower() == "marriage":
            dk = karakas.get("Darakaraka (DK) - Spouse/Partnership")
            if dk:
                return SchoolResult(
                    school=self.school_name,
                    answer="Marriage indicators rely on Darakaraka.",
                    confidence=0.6,
                    sources=self.sources,
                    reasoning=f"Darakaraka is {dk['planet']} in {dk['sign']}.",
                    rules_fired=["Darakaraka Analysis"]
                )
                
        return SchoolResult(
            school=self.school_name,
            answer="Prediction not fully supported for this question.",
            confidence=0.0
        )
        
    def explain(self, result: SchoolResult) -> str:
        """Explain the school's result."""
        return f"[Jaimini Explanation]: {result.reasoning}"

    def _compute_chara_karakas(self, chart: Chart) -> dict:
        """
        Calculate the 7 Chara Karakas based on degrees in sign.
        Excludes Rahu and Ketu (using the 7-karaka scheme).
        """
        # Get 7 main planets (Sun to Saturn)
        main_planets = [p for p in chart.planets if p.name not in [Planet.RAHU, Planet.KETU]]
        
        # Sort by degree_in_sign descending
        sorted_planets = sorted(main_planets, key=lambda p: p.degree_in_sign, reverse=True)
        
        karaka_names = [
            "Atmakaraka (AK) - Self/Soul",
            "Amatyakaraka (AmK) - Career/Mind",
            "Bhratrukaraka (BK) - Siblings/Guru",
            "Matrukaraka (MK) - Mother/Property",
            "Putrakaraka (PK) - Children/Intellect",
            "Gnatikaraka (GK) - Rivals/Disease",
            "Darakaraka (DK) - Spouse/Partnership"
        ]
        
        karakas = {}
        for i, planet in enumerate(sorted_planets):
            if i < len(karaka_names):
                karakas[karaka_names[i]] = {
                    "planet": planet.name,
                    "degree": planet.degree_in_sign,
                    "sign": planet.sign
                }
                
        return karakas

    def _compute_rashi_drishti(self, chart: Chart) -> dict:
        """
        Compute Jaimini Rashi Drishti (Sign Aspects).
        - Movable signs aspect all Fixed signs (except adjacent)
        - Fixed signs aspect all Movable signs (except adjacent)
        - Dual signs aspect all other Dual signs
        """
        aspects = {}
        
        for p1 in chart.planets:
            aspecting_sign = p1.sign_number
            modality = SIGN_MODALITIES[aspecting_sign]
            
            aspected_signs = []
            if modality == Modality.MOVABLE:
                # Aspects Fixed signs (1, 4, 7, 10 aspect 2, 5, 8, 11) - except adjacent
                fixed_signs = [s for s in range(12) if SIGN_MODALITIES[s] == Modality.FIXED]
                adjacent = (aspecting_sign + 1) % 12
                aspected_signs = [s for s in fixed_signs if s != adjacent]
                
            elif modality == Modality.FIXED:
                # Aspects Movable signs - except adjacent
                movable_signs = [s for s in range(12) if SIGN_MODALITIES[s] == Modality.MOVABLE]
                adjacent = (aspecting_sign - 1) % 12
                aspected_signs = [s for s in movable_signs if s != adjacent]
                
            elif modality == Modality.DUAL:
                # Aspects all other Dual signs
                aspected_signs = [s for s in range(12) if SIGN_MODALITIES[s] == Modality.DUAL and s != aspecting_sign]
                
            # Find which planets are in the aspected signs
            aspected_planets = []
            for p2 in chart.planets:
                if p2.sign_number in aspected_signs and p2.name != p1.name:
                    aspected_planets.append(p2.name)
                    
            if aspected_planets:
                aspects[p1.name] = aspected_planets
                
        return aspects



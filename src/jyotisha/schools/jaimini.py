"""
Jaimini School Module — Layer M

Implements Jaimini Sutras analysis, including:
- 7 Chara Karakas (Atmakaraka, etc.)
- Rashi Drishti (Sign aspects)
- Arudha Padas
"""

from typing import Optional
from jyotisha.models.schemas import Chart, SchoolResult
from jyotisha.constants import Planet, Modality, SIGN_MODALITIES
from jyotisha.engines.arudha import ArudhaEngine


class JaiminiModule:
    """
    Jaimini School Analysis Engine.
    """
    school_name = "Jaimini"
    sources = ["Jaimini Sutras"]

    def __init__(self, use_8_karakas: bool = False):
        self.use_8_karakas = use_8_karakas

    def compute_karakamsa(self, chart: Chart, use_8_karakas: Optional[bool] = None) -> dict:
        """
        Calculate the Karakamsa (Navamsha sign of Atmakaraka)
        and Swamsa (Karakamsa treated as Ascendant sign).
        """
        karakas = self._compute_chara_karakas(chart, use_8_karakas=use_8_karakas)
        ak_info = karakas.get("Atmakaraka (AK) - Self/Soul")
        if not ak_info:
            return {}
        
        ak_planet = ak_info["planet"]
        planet_obj = chart.get_planet(ak_planet)
        if not planet_obj:
            return {}
        
        from jyotisha.engines.varga import VargaEngine
        varga_engine = VargaEngine()
        karakamsa_sign_num = varga_engine.compute_varga_sign(planet_obj.longitude, 9)
        
        from jyotisha.constants import SIGN_NAMES
        karakamsa_sign_name = SIGN_NAMES[karakamsa_sign_num]
        
        return {
            "atmakaraka_planet": ak_planet,
            "karakamsa_sign_number": karakamsa_sign_num,
            "karakamsa_sign": karakamsa_sign_name,
            "swamsa_sign_number": karakamsa_sign_num,
            "swamsa_sign": karakamsa_sign_name
        }

    def analyze_chart(self, chart: Chart, use_8_karakas: Optional[bool] = None) -> dict:
        """
        Run full Jaimini analysis on a birth chart.
        """
        karakas = self._compute_chara_karakas(chart, use_8_karakas=use_8_karakas)
        rashi_drishti = self._compute_rashi_drishti(chart)
        arudha_engine = ArudhaEngine()
        arudhas = arudha_engine.compute_arudhas(chart)
        karakamsa = self.compute_karakamsa(chart, use_8_karakas=use_8_karakas)
        
        return {
            "school": self.school_name,
            "chara_karakas": karakas,
            "rashi_drishti": rashi_drishti,
            "arudha_padas": [a.model_dump() for a in arudhas],
            "karakamsa": karakamsa,
            "sources_used": self.sources
        }

    def predict(self, chart: Chart, question: str, target_date: Optional[str] = None, use_8_karakas: Optional[bool] = None) -> SchoolResult:
        """
        Generate a prediction based on Jaimini principles.
        """
        karakas = self._compute_chara_karakas(chart, use_8_karakas=use_8_karakas)
        
        if question.lower() == "marriage":
            dk = karakas.get("Darakaraka (DK) - Spouse/Partnership")
            arudha_engine = ArudhaEngine()
            arudhas = arudha_engine.compute_arudhas(chart)
            ul = next((a for a in arudhas if "UL" in a.type), None)
            
            if dk and ul:
                confidence = 0.0
                rules = []
                
                # We could add transit checks here if target_date is given
                if target_date:
                    from jyotisha.engines.transit import TransitEngine
                    transit_engine = TransitEngine()
                    transits = transit_engine.compute_transits(chart, target_date)
                    
                    # Check if Jupiter or DK transits UL or 7th from UL
                    jupiter_transit = next((t for t in transits.transit_planets if t.name == "Jupiter"), None)
                    dk_transit = next((t for t in transits.transit_planets if t.name == dk['planet']), None)
                    
                    ul_sign = ul.sign_number
                    ul_7th = (ul_sign + 6) % 12
                    
                    if jupiter_transit and jupiter_transit.sign_number in [ul_sign, ul_7th]:
                        confidence += 0.5
                        rules.append("Transiting Jupiter connects with Upapada Lagna.")
                    if dk_transit and dk_transit.sign_number in [ul_sign, ul_7th]:
                        confidence += 0.5
                        rules.append("Transiting Darakaraka connects with Upapada Lagna.")
                
                confidence = min(1.0, confidence)
                answer = "Favorable transit for marriage." if confidence > 0.0 else "No strong Jaimini transit indication."
                
                return SchoolResult(
                    school=self.school_name,
                    answer=answer,
                    confidence=confidence,
                    sources=self.sources,
                    reasoning=f"Darakaraka is {dk['planet']}. Upapada Lagna is {ul.sign}. Confidence based on transits over UL.",
                    rules_fired=rules,
                    structured_data={"darakaraka": dk['planet'], "dk_sign": dk['sign'], "ul_sign": ul.sign}
                )
                
        elif question.lower() == "career":
            amk = karakas.get("Amatyakaraka (AmK) - Career/Mind")
            arudha_engine = ArudhaEngine()
            arudhas = arudha_engine.compute_arudhas(chart)
            al = next((a for a in arudhas if a.type == "AL"), None)
            
            if amk and al:
                confidence = 0.0
                rules = []
                
                # Check Jaimini aspects: Movable/Fixed/Dual
                def rashi_aspects(s1_num: int, s2_num: int) -> bool:
                    if s1_num == s2_num:
                        return True
                    from jyotisha.constants import SIGN_MODALITIES, Modality
                    m1 = SIGN_MODALITIES[s1_num]
                    m2 = SIGN_MODALITIES[s2_num]
                    if m1 == Modality.MOVABLE and m2 == Modality.FIXED:
                        return s2_num != (s1_num + 1) % 12
                    if m1 == Modality.FIXED and m2 == Modality.MOVABLE:
                        return s2_num != (s1_num - 1) % 12
                    if m1 == Modality.DUAL and m2 == Modality.DUAL:
                        return s1_num != s2_num
                    return False
                
                amk_planet = chart.get_planet(amk["planet"])
                amk_sign = amk_planet.sign_number if amk_planet else 0
                al_sign = al.sign_number
                
                if target_date:
                    from jyotisha.engines.transit import TransitEngine
                    transit_engine = TransitEngine()
                    transits = transit_engine.compute_transits(chart, target_date)
                    
                    jup_transit = next((t for t in transits.transit_planets if t.name == "Jupiter"), None)
                    sat_transit = next((t for t in transits.transit_planets if t.name == "Saturn"), None)
                    
                    if jup_transit:
                        if rashi_aspects(jup_transit.sign_number, amk_sign):
                            confidence += 0.4
                            rules.append(f"Transiting Jupiter aspects/occupies Amatyakaraka ({amk['planet']}) sign.")
                        if rashi_aspects(jup_transit.sign_number, al_sign):
                            confidence += 0.3
                            rules.append("Transiting Jupiter aspects/occupies Arudha Lagna (AL).")
                            
                    if sat_transit:
                        if rashi_aspects(sat_transit.sign_number, al_sign):
                            confidence += 0.3
                            rules.append("Transiting Saturn aspects/occupies Arudha Lagna (AL).")
                            
                if rashi_aspects(amk_sign, al_sign):
                    confidence += 0.1
                    rules.append(f"Amatyakaraka {amk['planet']} aspectually connects with Arudha Lagna (AL) in natal chart.")
                    
                confidence = min(1.0, confidence)
                answer = "Favorable Jaimini indicators for career progression." if confidence > 0.4 else "No strong Jaimini indicators for career timing."
                
                return SchoolResult(
                    school=self.school_name,
                    answer=answer,
                    confidence=confidence,
                    sources=self.sources,
                    reasoning=f"Amatyakaraka (AmK) is {amk['planet']}. Arudha Lagna (AL) is in {al.sign}.",
                    rules_fired=rules,
                    structured_data={"amatyakaraka": amk['planet'], "amk_sign": amk['sign'], "al_sign": al.sign}
                )
                
        return SchoolResult(
            school=self.school_name,
            answer="Prediction not fully supported for this question.",
            confidence=0.0
        )
        
    def explain(self, result: SchoolResult) -> str:
        """Explain the school's result."""
        return f"[Jaimini Explanation]: {result.reasoning}"

    def _compute_chara_karakas(self, chart: Chart, use_8_karakas: Optional[bool] = None) -> dict:
        """
        Calculate the Chara Karakas based on degrees in sign.
        Supports 7-karaka (default, excluding Rahu) and 8-karaka (including Rahu) schemes.
        For Rahu, the degree in the sign is calculated as 30.0 - degree_in_sign.
        """
        if use_8_karakas is None:
            use_8_karakas = self.use_8_karakas

        if use_8_karakas:
            # 8-karaka scheme: Include Rahu, exclude Ketu
            planets_to_use = [p for p in chart.planets if p.name != Planet.KETU]
            
            planet_degrees = []
            for p in planets_to_use:
                if p.name == Planet.RAHU:
                    eff_deg = 30.0 - p.degree_in_sign
                else:
                    eff_deg = p.degree_in_sign
                planet_degrees.append((p.name, eff_deg, p.sign))
                
            sorted_planets = sorted(planet_degrees, key=lambda x: (x[1], x[0]), reverse=True)
            
            karaka_names = [
                "Atmakaraka (AK) - Self/Soul",
                "Amatyakaraka (AmK) - Career/Mind",
                "Bhratrukaraka (BK) - Siblings/Guru",
                "Matrukaraka (MK) - Mother/Property",
                "Pitrukaraka (PiK) - Father/Ancestors",
                "Putrakaraka (PK) - Children/Intellect",
                "Gnatikaraka (GK) - Rivals/Disease",
                "Darakaraka (DK) - Spouse/Partnership"
            ]
            
            karakas = {}
            for i, (planet_name, degree, sign) in enumerate(sorted_planets):
                if i < len(karaka_names):
                    karakas[karaka_names[i]] = {
                        "planet": planet_name,
                        "degree": degree,
                        "sign": sign
                    }
            return karakas
        else:
            # 7-karaka scheme: Exclude Rahu and Ketu
            main_planets = [p for p in chart.planets if p.name not in [Planet.RAHU, Planet.KETU]]
            
            sorted_planets = sorted(main_planets, key=lambda p: (p.degree_in_sign, p.name), reverse=True)
            
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



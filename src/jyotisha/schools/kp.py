"""
Krishnamurti Paddhati (KP) Module — Layer N

Implements KP system specific calculations:
- Sub-lords based on unequal 9-fold division of Nakshatras
- Placidus House cusps (requires PySwissEph)
- Significators (A, B, C, D levels)
"""


from jyotisha.models.schemas import Chart, SchoolResult
from jyotisha.constants import (
    NAKSHATRA_SPAN, NAKSHATRA_LORDS, VIMSHOTTARI_YEARS,
    VIMSHOTTARI_ORDER, VIMSHOTTARI_TOTAL_YEARS, Planet,
    SIGN_LORDS, Sign
)

class KPModule:
    """KP School Analysis Engine."""
    
    school_name = "Krishnamurti Paddhati (KP)"
    sources = ["KP Astrology Principles"]

    def analyze_chart(self, chart: Chart) -> dict:
        """Run full KP analysis."""
        
        # In a full KP system, houses MUST be Placidus. 
        # Our core Chart currently uses Whole Sign by default, 
        # but we can calculate sub-lords for planets regardless.
        
        planet_subs = self._compute_all_sub_lords(chart)
        ruling_planets = self._compute_ruling_planets(chart)
        
        return {
            "school": self.school_name,
            "planet_sub_lords": planet_subs,
            "ruling_planets": ruling_planets,
            "sources_used": self.sources
        }

    def predict(self, chart: Chart, question: str) -> SchoolResult:
        """
        Generate a prediction based on KP principles.
        """
        planet_subs = self._compute_all_sub_lords(chart)
        
        if question.lower() == "marriage":
            # For marriage, in KP we check the 7th Cusp Sub-lord. 
            # Since we don't have exact Placidus cusps fully exposed yet, 
            # we look at Venus and the 7th house lord as proxies.
            lord_7 = chart.get_house_lord(7)
            sub_7 = planet_subs.get(lord_7)
            if sub_7:
                return SchoolResult(
                    school=self.school_name,
                    answer="Marriage indicators rely on 7th cusp sub-lord significations.",
                    confidence=0.7,
                    sources=self.sources,
                    reasoning=f"7th Lord {lord_7} has Sub Lord {sub_7['sub_lord']}. Check if it signifies 2, 7, 11.",
                    rules_fired=["Cuspal Sub Lord Analysis"],
                    structured_data={"cusp_7_lord": lord_7, "cusp_7_sub_lord": sub_7['sub_lord']}
                )
                
        return SchoolResult(
            school=self.school_name,
            answer="Prediction not fully supported for this question.",
            confidence=0.0
        )
        
    def explain(self, result: SchoolResult) -> str:
        """Explain the school's result."""
        return f"[KP Explanation]: {result.reasoning}"

    def _compute_all_sub_lords(self, chart: Chart) -> dict:
        """Compute the Star Lord (Nakshatra Lord) and Sub Lord for each planet."""
        results = {}
        for p in chart.planets:
            star_lord, sub_lord = self.get_sub_lord(p.longitude)
            results[p.name] = {
                "longitude": round(p.longitude, 4),
                "star_lord": star_lord,
                "sub_lord": sub_lord
            }
            
        # Also do Ascendant
        star_lord, sub_lord = self.get_sub_lord(chart.ascendant.longitude)
        results["Ascendant"] = {
            "longitude": round(chart.ascendant.longitude, 4),
            "star_lord": star_lord,
            "sub_lord": sub_lord
        }
        
        return results

    def get_sub_lord(self, longitude: float) -> tuple[Planet, Planet]:
        """
        Calculates the Nakshatra Lord (Star Lord) and the Sub Lord
        for a given longitude (0-360).
        """
        # 1. Find Nakshatra and its Lord
        nakshatra_num = int(longitude / NAKSHATRA_SPAN)
        if nakshatra_num >= 27:
            nakshatra_num = 26
            
        star_lord = NAKSHATRA_LORDS[nakshatra_num]
        
        # 2. Find position inside the nakshatra (0 to 13.333)
        degree_in_nakshatra = longitude % NAKSHATRA_SPAN
        
        # 3. Iterate through Vimshottari order starting from Star Lord
        start_idx = VIMSHOTTARI_ORDER.index(star_lord)
        
        current_span = 0.0
        for i in range(9):
            sub_idx = (start_idx + i) % 9
            sub_lord = VIMSHOTTARI_ORDER[sub_idx]
            
            # Sub-lord span = (Years of Sub-lord / 120) * 13.3333...
            years = VIMSHOTTARI_YEARS[sub_lord]
            sub_span = (years / VIMSHOTTARI_TOTAL_YEARS) * NAKSHATRA_SPAN
            
            current_span += sub_span
            if degree_in_nakshatra <= current_span:
                return star_lord, sub_lord
                
        # Fallback (should not reach due to float precision unless exactly at end)
        return star_lord, VIMSHOTTARI_ORDER[(start_idx + 8) % 9]

    def _compute_ruling_planets(self, chart: Chart) -> dict:
        """
        Calculate KP Ruling Planets at the time of the chart.
        1. Ascendant Star Lord
        2. Ascendant Sign Lord
        3. Moon Star Lord
        4. Moon Sign Lord
        5. Day Lord (Lord of the weekday)
        """
        ruling = {}
        
        # Ascendant Lords
        asc_star, asc_sub = self.get_sub_lord(chart.ascendant.longitude)
        ruling["Ascendant_Star_Lord"] = asc_star
        asc_sign = Sign(chart.ascendant.sign_number)
        ruling["Ascendant_Sign_Lord"] = SIGN_LORDS.get(asc_sign)
        
        # Moon Lords
        moon = chart.get_planet("Moon")
        if moon:
            moon_star, moon_sub = self.get_sub_lord(moon.longitude)
            ruling["Moon_Star_Lord"] = moon_star
            moon_sign = Sign(moon.sign_number)
            ruling["Moon_Sign_Lord"] = SIGN_LORDS.get(moon_sign)
            
        # Day Lord
        if chart.birth_event and chart.birth_event.datetime_utc:
            try:
                from datetime import timedelta
                # datetime_utc is a datetime object
                dt_utc = chart.birth_event.datetime_utc
                # Adjust to local time using the provided offset
                local_dt = dt_utc + timedelta(hours=chart.birth_event.utc_offset_hours)
                
                weekday = local_dt.weekday()
                
                # Vedic day starts at sunrise. If birth is before ~6 AM, it typically falls under the previous day's lord.
                if local_dt.hour < 6:
                    weekday = (weekday - 1) % 7
                    
                # Monday=0, Sunday=6
                day_lords = [
                    Planet.MOON,    # Mon (0)
                    Planet.MARS,    # Tue (1)
                    Planet.MERCURY, # Wed (2)
                    Planet.JUPITER, # Thu (3)
                    Planet.VENUS,   # Fri (4)
                    Planet.SATURN,  # Sat (5)
                    Planet.SUN      # Sun (6)
                ]
                ruling["Day_Lord"] = day_lords[weekday]
            except Exception:
                ruling["Day_Lord"] = "Unknown"
                
        return ruling

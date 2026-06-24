"""
Krishnamurti Paddhati (KP) Module — Layer N

Implements KP system specific calculations:
- Sub-lords based on unequal 9-fold division of Nakshatras
- Placidus House cusps (requires PySwissEph)
- Significators (A, B, C, D levels)
"""


from typing import Optional
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
        planet_significators = self._compute_planet_significators(chart, planet_subs)
        cusp_subs = self._compute_cusp_sub_lords(chart, planet_significators)
        ruling_planets = self._compute_ruling_planets(chart)
        
        return {
            "school": self.school_name,
            "planet_sub_lords": planet_subs,
            "planet_significators": planet_significators,
            "cusp_sub_lords": cusp_subs,
            "ruling_planets": ruling_planets,
            "sources_used": self.sources
        }

    def predict(self, chart: Chart, question: str, target_date: Optional[str] = None) -> SchoolResult:
        """
        Generate a prediction based on KP principles.
        """
        planet_subs = self._compute_all_sub_lords(chart)
        planet_significators = self._compute_planet_significators(chart, planet_subs)
        house_significators = self._compute_house_significators(chart, planet_subs)
        cusp_subs = self._compute_cusp_sub_lords(chart, planet_significators)
        
        # Event configurations (primary cusp, favorable houses, unfavorable houses)
        event_configs = {
            "marriage": {
                "primary_cusp": 7,
                "favorable_houses": [2, 7, 11],
                "unfavorable_houses": [1, 6, 10],
                "promise_text": "marriage",
                "success_message": "Strong KP promise for marriage.",
                "fail_message": "Weak or no KP promise for marriage."
            },
            "career": {
                "primary_cusp": 10,
                "favorable_houses": [2, 6, 10, 11],
                "unfavorable_houses": [5, 8, 12],
                "promise_text": "professional success",
                "success_message": "Strong KP promise for professional success.",
                "fail_message": "Moderate or weak KP indicators for career progression."
            },
            "childbirth": {
                "primary_cusp": 5,
                "favorable_houses": [2, 5, 11],
                "unfavorable_houses": [1, 4, 10],
                "promise_text": "childbirth",
                "success_message": "Strong KP promise for childbirth / children.",
                "fail_message": "Weak or delayed KP promise for childbirth."
            },
            "education": {
                "primary_cusp": 4,
                "favorable_houses": [4, 9, 11],
                "unfavorable_houses": [3, 8, 12],
                "promise_text": "academic success",
                "success_message": "Strong KP promise for educational / academic success.",
                "fail_message": "Weak or moderate KP indicators for higher education."
            },
            "travel": {
                "primary_cusp": 9,
                "favorable_houses": [3, 9, 12],
                "unfavorable_houses": [2, 4, 11],
                "promise_text": "foreign travel / relocation",
                "success_message": "Strong KP promise for foreign travel / relocation.",
                "fail_message": "Weak or no foreign travel indicators in the chart."
            }
        }
        
        q_lower = question.lower()
        if q_lower not in event_configs:
            return SchoolResult(
                school=self.school_name,
                answer="Prediction not fully supported for this question.",
                confidence=0.0
            )
            
        config = event_configs[q_lower]
        primary_cusp = config["primary_cusp"]
        favorable = config["favorable_houses"]
        unfavorable = config["unfavorable_houses"]
        
        # Get primary cusp sub lord
        cusp_data = cusp_subs.get(primary_cusp)
        if not cusp_data:
            return SchoolResult(
                school=self.school_name,
                answer="Cuspal data missing.",
                confidence=0.0
            )
            
        sub_lord = cusp_data["sub_lord"].value
        
        # Determine if sub_lord signifies favorable houses
        signified_fav = []
        signified_unfav = []
        rules = []
        confidence = 0.0
        
        # Check significance for each house
        for h in range(1, 13):
            is_fav = h in favorable
            is_unfav = h in unfavorable
            
            levels = house_significators.get(h, {})
            in_levels = []
            if sub_lord in levels.get("A", []):
                in_levels.append("A")
            if sub_lord in levels.get("B", []):
                in_levels.append("B")
            if sub_lord in levels.get("C", []):
                in_levels.append("C")
            if sub_lord in levels.get("D", []):
                in_levels.append("D")
                
            if in_levels:
                level_scores = {"A": 0.4, "B": 0.3, "C": 0.2, "D": 0.1}
                max_lvl_score = max(level_scores[l] for l in in_levels)
                
                if is_fav:
                    signified_fav.append(h)
                    confidence += max_lvl_score
                    rules.append(f"Sub Lord {sub_lord} signifies favorable house {h} at levels {in_levels}.")
                elif is_unfav:
                    signified_unfav.append(h)
                    confidence -= (max_lvl_score * 0.5)  # Unfavorable houses reduce confidence
                    rules.append(f"Sub Lord {sub_lord} signifies unfavorable house {h} at levels {in_levels}.")
                    
        # If target_date is given, verify dasha timing
        if target_date:
            try:
                from jyotisha.engines.dasha import DashaEngine
                dasha_engine = DashaEngine()
                timeline = dasha_engine.compute_vimshottari_from_chart(chart, levels=3)
                query_jd = dasha_engine._date_to_jd(target_date)
                current_dasha_data = dasha_engine.get_current_dasha(timeline, query_jd)
                
                timing_lords = []
                for d_level in ["mahadasha", "antardasha", "pratyantardasha"]:
                    if d_level in current_dasha_data:
                        timing_lords.append(current_dasha_data[d_level]["lord"])
                        
                timing_significance = 0.0
                for lord in timing_lords:
                    for h in favorable:
                        levels = house_significators.get(h, {})
                        if any(lord in levels.get(lvl, []) for lvl in ["A", "B", "C", "D"]):
                            timing_significance += 0.1
                            rules.append(f"Timing Lord {lord} signifies favorable house {h}.")
                            break
                confidence += timing_significance
            except Exception:
                pass
            
        confidence = max(0.0, min(1.0, confidence))
        answer = config["success_message"] if confidence >= 0.4 else config["fail_message"]
        
        # Include detailed structured data
        structured = {
            "primary_cusp": primary_cusp,
            "sub_lord": sub_lord,
            "favorable_houses_signified": signified_fav,
            "unfavorable_houses_signified": signified_unfav,
            "ruling_planets": [r.value for r in self._compute_ruling_planets(chart).values() if hasattr(r, "value")]
        }
        
        return SchoolResult(
            school=self.school_name,
            answer=answer,
            confidence=round(confidence, 2),
            sources=self.sources,
            reasoning=f"Sub Lord of cusp {primary_cusp} is {sub_lord}. Signifies favorable houses {signified_fav} and unfavorable houses {signified_unfav}.",
            rules_fired=rules,
            structured_data=structured
        )
        
    def explain(self, result: SchoolResult) -> str:
        """Explain the school's result."""
        return f"[KP Explanation]: {result.reasoning}"

    def _compute_house_significators(self, chart: Chart, planet_subs: dict) -> dict:
        """
        Compute the planets signifying each house (1-12) at levels A, B, C, D.
        - Level A: Planets in the nakshatra of the occupants of the house.
        - Level B: Occupants of the house.
        - Level C: Planets in the nakshatra of the lord of the house.
        - Level D: Lord of the house.
        """
        significators = {h: {"A": [], "B": [], "C": [], "D": []} for h in range(1, 13)}
        
        house_lords = {}
        for house in chart.houses:
            house_lords[house.number] = house.lord
            
        house_occupants = {h: [] for h in range(1, 13)}
        for planet in chart.planets:
            h = planet.house
            if h and 1 <= h <= 12:
                house_occupants[h].append(planet.name)
                
        planet_star_lords = {}
        for planet_name, sub_detail in planet_subs.items():
            if planet_name == "Ascendant":
                continue
            star_lord = sub_detail.get("star_lord")
            planet_star_lords[planet_name] = star_lord.value if hasattr(star_lord, "value") else star_lord

        for h in range(1, 13):
            lord = house_lords.get(h)
            occupants = house_occupants.get(h, [])
            
            if lord:
                significators[h]["D"].append(lord)
                
            for occ in occupants:
                significators[h]["B"].append(occ)
                
            for p_name, star_lord in planet_star_lords.items():
                if star_lord in occupants:
                    significators[h]["A"].append(p_name)
                if star_lord == lord:
                    significators[h]["C"].append(p_name)
                    
            for lvl in ["A", "B", "C", "D"]:
                significators[h][lvl] = list(dict.fromkeys(significators[h][lvl]))
                
        return significators

    def _compute_all_sub_lords(self, chart: Chart) -> dict:
        """Compute star, sub, and sub-sub lord for each planet."""
        results = {}
        for p in chart.planets:
            lord_detail = self.get_sub_lord_detail(p.longitude)
            results[p.name] = {
                "longitude": round(p.longitude, 4),
                **lord_detail,
            }
            
        # Also do Ascendant
        lord_detail = self.get_sub_lord_detail(chart.ascendant.longitude)
        results["Ascendant"] = {
            "longitude": round(chart.ascendant.longitude, 4),
            **lord_detail,
        }
        
        return results

    def get_sub_lord(self, longitude: float) -> tuple[Planet, Planet]:
        """
        Calculates the Nakshatra Lord (Star Lord) and the Sub Lord
        for a given longitude (0-360).
        """
        detail = self.get_sub_lord_detail(longitude)
        return detail["star_lord"], detail["sub_lord"]

    def get_sub_lord_detail(self, longitude: float) -> dict:
        """
        Calculate KP star lord, sub lord, and sub-sub lord.

        KP divides each nakshatra into 9 unequal Vimshottari-proportional
        subs, then divides the selected sub again from its own lord.
        """
        # 1. Find Nakshatra and its Lord
        normalized_longitude = longitude % 360.0
        nakshatra_num = int(normalized_longitude / NAKSHATRA_SPAN)
        if nakshatra_num >= 27:
            nakshatra_num = 26
            
        star_lord = NAKSHATRA_LORDS[nakshatra_num]
        
        # 2. Find position inside the nakshatra (0 to 13.333)
        degree_in_nakshatra = normalized_longitude % NAKSHATRA_SPAN
        
        # 3. Locate the sub-lord, then recursively locate the sub-sub-lord.
        sub_lord, sub_start, sub_span = self._locate_vimshottari_slice(
            start_lord=star_lord,
            offset_degrees=degree_in_nakshatra,
            total_span_degrees=NAKSHATRA_SPAN,
        )
        degree_in_sub = degree_in_nakshatra - sub_start
        sub_sub_lord, sub_sub_start, sub_sub_span = self._locate_vimshottari_slice(
            start_lord=sub_lord,
            offset_degrees=degree_in_sub,
            total_span_degrees=sub_span,
        )

        return {
            "star_lord": star_lord,
            "sub_lord": sub_lord,
            "sub_sub_lord": sub_sub_lord,
            "degree_in_nakshatra": round(degree_in_nakshatra, 6),
            "degree_in_sub": round(degree_in_sub, 6),
            "degree_in_sub_sub": round(degree_in_sub - sub_sub_start, 6),
            "sub_span_degrees": round(sub_span, 6),
            "sub_sub_span_degrees": round(sub_sub_span, 6),
        }

    @staticmethod
    def _locate_vimshottari_slice(
        start_lord: Planet,
        offset_degrees: float,
        total_span_degrees: float,
    ) -> tuple[Planet, float, float]:
        """Return lord, slice start, and slice span for a proportional KP division."""
        start_idx = VIMSHOTTARI_ORDER.index(start_lord)
        current_start = 0.0

        for i in range(9):
            lord = VIMSHOTTARI_ORDER[(start_idx + i) % 9]
            span = (
                VIMSHOTTARI_YEARS[lord] / VIMSHOTTARI_TOTAL_YEARS
            ) * total_span_degrees
            current_end = current_start + span

            if offset_degrees < current_end or i == 8:
                return lord, current_start, span

            current_start = current_end

        final_lord = VIMSHOTTARI_ORDER[(start_idx + 8) % 9]
        return final_lord, current_start, 0.0

    def _compute_cusp_sub_lords(
        self,
        chart: Chart,
        planet_significators: dict,
    ) -> dict:
        """Compute KP star/sub/sub-sub lords and signified houses for each cusp."""
        results = {}

        for house in chart.houses:
            lord_detail = self.get_sub_lord_detail(house.cusp_longitude)
            sub_lord = lord_detail["sub_lord"].value
            sub_sub_lord = lord_detail["sub_sub_lord"].value

            results[house.number] = {
                "cusp_longitude": round(house.cusp_longitude, 6),
                "sign": house.sign,
                "sign_number": house.sign_number,
                **lord_detail,
                "sub_lord_significators": planet_significators.get(
                    sub_lord, {}
                ).get("signified_houses", []),
                "sub_sub_lord_significators": planet_significators.get(
                    sub_sub_lord, {}
                ).get("signified_houses", []),
            }

        return results

    def _compute_planet_significators(self, chart: Chart, planet_subs: dict) -> dict:
        """
        Compute a bounded KP significator set per planet.

        This exposes the core data needed for later A/B/C/D ranking:
        placement, ownership, star lord, sub lord, and the star lord's houses.
        """
        results = {}

        for planet in chart.planets:
            subs = planet_subs.get(planet.name, {})
            owned_houses = [
                house.number for house in chart.houses if house.lord == planet.name
            ]

            star_lord = subs.get("star_lord")
            star_lord_name = star_lord.value if isinstance(star_lord, Planet) else None
            star_lord_planet = chart.get_planet(star_lord_name) if star_lord_name else None
            star_lord_owned_houses = [
                house.number for house in chart.houses if house.lord == star_lord_name
            ]

            star_lord_houses = []
            if star_lord_planet:
                star_lord_houses.append(star_lord_planet.house)
            star_lord_houses.extend(star_lord_owned_houses)

            signified_houses = self._unique_house_numbers(
                [planet.house, *owned_houses, *star_lord_houses]
            )

            results[planet.name] = {
                "placed_house": planet.house,
                "owned_houses": owned_houses,
                "star_lord": star_lord_name,
                "sub_lord": (
                    subs["sub_lord"].value
                    if isinstance(subs.get("sub_lord"), Planet)
                    else None
                ),
                "sub_sub_lord": (
                    subs["sub_sub_lord"].value
                    if isinstance(subs.get("sub_sub_lord"), Planet)
                    else None
                ),
                "star_lord_houses": self._unique_house_numbers(star_lord_houses),
                "signified_houses": signified_houses,
            }

        return results

    @staticmethod
    def _unique_house_numbers(houses: list[int]) -> list[int]:
        """Return 1-12 house numbers in first-seen order."""
        unique = []
        for house in houses:
            if house is not None and 1 <= house <= 12 and house not in unique:
                unique.append(house)
        return unique

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
                
                # Vedic day starts at sunrise. Compute actual sunrise to determine Vedic day lord.
                from jyotisha.engines.astronomy import AstronomicalEngine
                astro = AstronomicalEngine()
                
                local_midnight_dt = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                utc_midnight_dt = local_midnight_dt - timedelta(hours=chart.birth_event.utc_offset_hours)
                
                midnight_jd = astro.datetime_to_jd(utc_midnight_dt)
                sunrise_jd = astro.compute_sunrise(
                    jd=midnight_jd,
                    lat=chart.birth_event.location.latitude,
                    lon=chart.birth_event.location.longitude,
                    alt=chart.birth_event.location.altitude or 0.0
                )
                
                if chart.birth_event.julian_day < sunrise_jd:
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

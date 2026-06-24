"""
Prashna Engine — Layer L

Implements Prashna (Horary) astrology:
1. Classical Prashna: analyzes relationships between Lagna (querent), 7th house (matter), and Moon (mind).
2. KP Horary: maps a number between 1 and 249 to a precise zodiacal Ascendant, casts the Placidus chart, and evaluates cuspal sub-lords.
"""

from __future__ import annotations
from typing import Optional
import json

from jyotisha.models.schemas import Chart, Location, BirthEvent
from jyotisha.engines.chart import ChartEngine
from jyotisha.engines.astronomy import AstronomicalEngine
from jyotisha.schools.kp import KPModule


class PrashnaEngine:
    """
    Engine for Horary (Prashna) astrology calculations.
    """

    def __init__(
        self,
        chart_engine: Optional[ChartEngine] = None,
        kp_module: Optional[KPModule] = None,
    ):
        self.chart_engine = chart_engine or ChartEngine()
        self.kp_module = kp_module or KPModule()

    def evaluate_classical_prashna(
        self,
        birth_chart: Chart,
        question: str,
    ) -> dict:
        """
        Evaluate classical Prashna based on the chart cast at the moment of the question.
        - Ascendant (1st house) = Querent
        - 7th house = Matter asked about
        - Moon = Mind/Focus
        """
        lagna_lord = birth_chart.get_house_lord(1)
        target_lord = birth_chart.get_house_lord(7)
        moon = birth_chart.get_planet("Moon")
        
        if not lagna_lord or not target_lord or not moon:
            return {
                "question": question,
                "verdict": "Unfavorable",
                "confidence": 0.0,
                "reasoning": "Could not determine critical chart points (Lagna Lord, 7th Lord, or Moon).",
            }

        reasons = []
        score = 0
        total_checks = 3
        
        # Check 1: Relation between Lagna Lord and 7th Lord
        ll_pos = birth_chart.get_planet(lagna_lord)
        tl_pos = birth_chart.get_planet(target_lord)
        
        if ll_pos and tl_pos:
            # Check if they are conjunct or in aspects
            if ll_pos.sign_number == tl_pos.sign_number:
                score += 1.0
                reasons.append(f"Lagna Lord ({lagna_lord}) and 7th Lord ({target_lord}) are conjunct in {ll_pos.sign}.")
            else:
                house_diff = abs(ll_pos.house - tl_pos.house)
                if house_diff in {3, 4, 5, 9, 10, 11}:
                    score += 0.5
                    reasons.append(f"Lagna Lord and 7th Lord are in a supportive relative placement (distance: {house_diff} houses).")
                elif house_diff in {6, 8, 12}:
                    score -= 0.5
                    reasons.append(f"Lagna Lord and 7th Lord are in a difficult relative placement (Shadashtaka or similar: {house_diff} houses).")
                else:
                    reasons.append("Lagna Lord and 7th Lord have a neutral relative placement.")
        
        # Check 2: Moon position and aspects
        # Favorable if Moon is in Kendra (1, 4, 7, 10) or Trikona (5, 9)
        if moon.house in {1, 4, 7, 10, 5, 9}:
            score += 1.0
            reasons.append(f"Moon is placed favorably in the {moon.house} house, indicating clarity of purpose.")
        else:
            reasons.append(f"Moon is in the {moon.house} house (neutral/weak).")

        # Check 3: Benefic associations of Lagna or 7th house
        # Favorable if Lagna contains a benefic (Jupiter, Venus, Mercury, waxing Moon)
        benefics = {"Jupiter", "Venus", "Mercury", "Moon"}
        lagna_occupants = [p.name for p in birth_chart.planets_in_house(1)]
        target_occupants = [p.name for p in birth_chart.planets_in_house(7)]
        
        has_benefic_lagna = any(occ in benefics for occ in lagna_occupants)
        has_benefic_target = any(occ in benefics for occ in target_occupants)
        
        if has_benefic_lagna or has_benefic_target:
            score += 1.0
            reasons.append("Benefic planets occupy the Ascendant or the 7th house, supporting a positive outcome.")
        else:
            reasons.append("No primary benefics in the Ascendant or 7th house.")

        # Calculate final verdict
        confidence = max(0.0, min(1.0, (score / total_checks)))
        verdict = "Highly Favorable" if confidence >= 0.8 else "Favorable" if confidence >= 0.5 else "Neutral/Uncertain" if confidence >= 0.3 else "Unfavorable"
        
        return {
            "question": question,
            "verdict": verdict,
            "confidence": round(confidence, 2),
            "reasoning": " ".join(reasons),
            "details": {
                "lagna_lord": lagna_lord,
                "target_lord": target_lord,
                "moon_house": moon.house
            }
        }

    def _get_249_divisions(self) -> list[dict]:
        """
        Generate the 249 KP sub-lord divisions of the zodiac.
        """
        VIMSHOTTARI_ORDER = ['Ketu', 'Venus', 'Sun', 'Moon', 'Mars', 'Rahu', 'Jupiter', 'Saturn', 'Mercury']
        VIMSHOTTARI_YEARS = {
            'Ketu': 7, 'Venus': 20, 'Sun': 6, 'Moon': 10, 'Mars': 7, 'Rahu': 18, 'Jupiter': 16, 'Saturn': 19, 'Mercury': 17
        }
        NAKSHATRA_SPAN = 360.0 / 27.0
        
        divisions = []
        for nak_idx in range(27):
            nak_start = nak_idx * NAKSHATRA_SPAN
            star_lord = VIMSHOTTARI_ORDER[nak_idx % 9]
            start_lord_idx = VIMSHOTTARI_ORDER.index(star_lord)
            
            cumulative_years = 0
            for sub_offset in range(9):
                sub_lord = VIMSHOTTARI_ORDER[(start_lord_idx + sub_offset) % 9]
                years = VIMSHOTTARI_YEARS[sub_lord]
                
                sub_start = nak_start + (cumulative_years * NAKSHATRA_SPAN) / 120.0
                sub_end = nak_start + ((cumulative_years + years) * NAKSHATRA_SPAN) / 120.0
                
                sub_start = round(sub_start, 9)
                sub_end = round(sub_end, 9)
                
                crossed = None
                for b in [30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0]:
                    if sub_start < b < sub_end:
                        crossed = b
                        break
                        
                if crossed is not None:
                    divisions.append({
                        "start": sub_start,
                        "end": crossed,
                        "star_lord": star_lord,
                        "sub_lord": sub_lord
                    })
                    divisions.append({
                        "start": crossed,
                        "end": sub_end,
                        "star_lord": star_lord,
                        "sub_lord": sub_lord
                    })
                else:
                    divisions.append({
                        "start": sub_start,
                        "end": sub_end,
                        "star_lord": star_lord,
                        "sub_lord": sub_lord
                    })
                    
                cumulative_years += years
        return divisions

    def _find_jd_for_ascendant(
        self,
        base_jd: float,
        lat: float,
        lon: float,
        target_lon: float,
    ) -> float:
        """
        Adjust the base_jd so that the computed Placidus Ascendant longitude is exactly target_lon.
        """
        def get_asc(t_jd: float) -> float:
            res = self.chart_engine.astro.compute_ascendant(t_jd, lat, lon, "P")
            return res["ascendant"]["longitude"]

        step = 0.00347  # ~5 minutes
        jd_start = base_jd - 0.5
        crossings = []
        
        prev_diff = (get_asc(jd_start) - target_lon) % 360.0
        for i in range(1, 290):
            t_jd = jd_start + i * step
            curr_diff = (get_asc(t_jd) - target_lon) % 360.0
            
            if prev_diff > 180.0 > curr_diff:
                crossings.append((t_jd - step, t_jd))
            prev_diff = curr_diff

        if crossings:
            low, high = crossings[0]
            for _ in range(15):
                mid = (low + high) / 2.0
                diff = (get_asc(mid) - target_lon) % 360.0
                if diff < 180.0:
                    high = mid
                else:
                    low = mid
            return (low + high) / 2.0

        return base_jd

    def evaluate_kp_horary(
        self,
        birth_chart: Chart,
        question: str,
        number: int,
    ) -> dict:
        """
        Cast and evaluate a KP Horary chart.
        Maps the given number (1-249) to an Ascendant longitude, adjusts birth time,
        and computes KP significators and cuspal sub-lords.
        """
        if not (1 <= number <= 249):
            raise ValueError("Horary number must be between 1 and 249")
            
        # 1. Map number to zodiac longitude
        divisions = self._get_249_divisions()
        div = divisions[number - 1]
        target_lon = div["start"]
        
        # 2. Adjust Julian Day so Ascendant matches target_lon
        lat = birth_chart.birth_event.location.latitude if birth_chart.birth_event else 0.0
        lon = birth_chart.birth_event.location.longitude if birth_chart.birth_event else 0.0
        base_jd = birth_chart.birth_event.julian_day if birth_chart.birth_event else 2449745.5
        
        jd_adjusted = self._find_jd_for_ascendant(base_jd, lat, lon, target_lon)
        
        # 3. Generate the Placidus chart at adjusted JD
        chart_engine_pl = ChartEngine(house_system="P")
        event_time_utc = AstronomicalEngine.jd_to_datetime(jd_adjusted)
        
        loc = Location(
            latitude=lat,
            longitude=lon,
            altitude=birth_chart.birth_event.location.altitude if birth_chart.birth_event else 0.0,
            timezone=birth_chart.birth_event.location.timezone if birth_chart.birth_event else None
        )
        
        horary_event = BirthEvent(
            datetime_utc=event_time_utc,
            julian_day=jd_adjusted,
            location=loc,
            utc_offset_hours=birth_chart.birth_event.utc_offset_hours if birth_chart.birth_event else 0.0
        )
        
        horary_chart = chart_engine_pl.generate_chart_from_event(horary_event)
        
        # 4. Run KP Prediction
        kp_res = self.kp_module.predict(horary_chart, question)
        
        sign_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        sign_name = sign_names[int(target_lon // 30.0)]
        
        return {
            "question": question,
            "horary_number": number,
            "target_longitude": round(target_lon, 4),
            "sign": sign_name,
            "star_lord": div["star_lord"],
            "sub_lord": div["sub_lord"],
            "adjusted_jd": round(jd_adjusted, 6),
            "adjusted_time_utc": event_time_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "verdict": kp_res.answer,
            "confidence": kp_res.confidence,
            "reasoning": kp_res.reasoning,
            "structured_data": kp_res.structured_data
        }

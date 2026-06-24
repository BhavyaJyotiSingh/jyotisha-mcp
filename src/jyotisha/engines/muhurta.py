"""
Muhurta Engine — Layer K

Computes Tarabala, Chandrabala, and evaluates electional rules
for key life events (marriage, business, travel, house purchase, surgery)
to select auspicious timings.
"""

from __future__ import annotations
from typing import Optional
from datetime import datetime

from jyotisha.models.schemas import Chart
from jyotisha.engines.panchanga import PanchangaEngine
from jyotisha.engines.chart import ChartEngine


class MuhurtaEngine:
    """
    Computes Tarabala and Chandrabala, and evaluates electional rules
    for selecting auspicious times (Muhurta).
    """

    TARA_NAMES = {
        1: ("Janma", "Danger/Body constraints", False),
        2: ("Sampat", "Wealth and prosperity", True),
        3: ("Vipat", "Losses and accidents", False),
        4: ("Kshema", "Well-being and safety", True),
        5: ("Pratyari", "Obstacles and enemies", False),
        6: ("Sadhaka", "Success and achievements", True),
        7: ("Vadha", "Death and extreme danger", False),
        8: ("Mitra", "Friendship and help", True),
        9: ("Atimitra", "Intimate friendship and supreme help", True),
    }

    def __init__(self, chart_engine: Optional[ChartEngine] = None):
        self.chart_engine = chart_engine or ChartEngine()
        self.panchanga_engine = PanchangaEngine(astro_engine=self.chart_engine.astro)

    def compute_tarabala(self, birth_nak_idx: int, transit_nak_idx: int) -> dict:
        """
        Compute Tarabala from birth nakshatra index (0-26) to transit nakshatra index (0-26).
        """
        # Calculate 1-based count from birth to transit
        diff = ((transit_nak_idx - birth_nak_idx) % 27) + 1
        tara_idx = (diff - 1) % 9 + 1
        
        name, description, is_auspicious = self.TARA_NAMES[tara_idx]
        
        return {
            "tara_number": tara_idx,
            "tara_name": name,
            "description": description,
            "is_auspicious": is_auspicious,
        }

    def compute_chandrabala(self, birth_moon_sign: int, transit_moon_sign: int) -> dict:
        """
        Compute Chandrabala from birth Moon's sign number (0-11) to transit Moon's sign number (0-11).
        """
        house_from_moon = ((transit_moon_sign - birth_moon_sign) % 12) + 1
        
        # Favorable houses: 1, 3, 6, 7, 10, 11
        favorable_houses = {1, 3, 6, 7, 10, 11}
        is_auspicious = house_from_moon in favorable_houses
        
        # 8th and 12th houses are considered highly inauspicious (Ashtama Chandra / Dwadasha Chandra)
        severity = "high" if house_from_moon in {8, 12} else "medium" if not is_auspicious else "none"
        
        description = (
            f"Transit Moon is in the {house_from_moon} house from natal Moon."
            + (" (Auspicious)" if is_auspicious else " (Inauspicious)" if severity == "medium" else " (Severely Inauspicious)")
        )
        
        return {
            "house_from_moon": house_from_moon,
            "is_auspicious": is_auspicious,
            "severity": severity,
            "description": description,
        }

    def evaluate_muhurta(
        self,
        birth_chart: Chart,
        transit_date_str: str,
        event_type: str,
    ) -> dict:
        """
        Evaluate a target transit date for Muhurta suitability for a specific event type.
        
        Supported event_types: 'marriage', 'business', 'travel', 'house_purchase', 'surgery'
        """
        # 1. Cast transit chart to get positions
        transit_event = self.chart_engine.calendar.normalize_birth_event(
            date_str=transit_date_str,
            time_str="12:00:00",
            latitude=birth_chart.birth_event.location.latitude if birth_chart.birth_event else 0.0,
            longitude=birth_chart.birth_event.location.longitude if birth_chart.birth_event else 0.0,
        )
        
        # 2. Get Panchanga for target time
        panchanga = self.panchanga_engine.compute_panchanga(
            jd=transit_event.julian_day,
            lat=transit_event.location.latitude,
            lon=transit_event.location.longitude,
            alt=transit_event.location.altitude,
            utc_offset_hours=transit_event.utc_offset_hours,
            tz_name=transit_event.location.timezone,
        )
        
        # 3. Compute Tarabala & Chandrabala
        natal_moon = birth_chart.get_planet("Moon")
        if not natal_moon:
            raise ValueError("Natal Moon position not found in chart")
            
        transit_moon_lon = self.chart_engine.astro.compute_planet_positions(transit_event.julian_day)["Moon"]["longitude"]
        transit_moon_sign = int(transit_moon_lon // 30.0)
        from jyotisha.constants import NAKSHATRA_SPAN
        transit_moon_nak = int(transit_moon_lon // NAKSHATRA_SPAN)
        if transit_moon_nak >= 27:
            transit_moon_nak = 26
            
        tarabala = self.compute_tarabala(natal_moon.nakshatra_number, transit_moon_nak)
        chandrabala = self.compute_chandrabala(natal_moon.sign_number, transit_moon_sign)
        
        # 4. Evaluate Event Rules
        event_lower = event_type.lower()
        score = 0
        total_checks = 4
        reasons = []
        
        # Check Tarabala & Chandrabala
        if tarabala["is_auspicious"]:
            score += 1
            reasons.append("Tarabala is auspicious.")
        else:
            reasons.append(f"Tarabala is inauspicious: {tarabala['tara_name']}.")
            
        if chandrabala["is_auspicious"]:
            score += 1
            reasons.append("Chandrabala is auspicious.")
        else:
            reasons.append(f"Chandrabala is inauspicious: Transit Moon is in the {chandrabala['house_from_moon']} house from natal Moon.")
            
        # Check Panchanga Elements based on event
        tithi = panchanga.tithi.number
        nak = panchanga.nakshatra.number
        
        if event_lower == "marriage":
            # Favorable Nakshatras: Rohini, Mrigashira, Uttara Phalguni, Hasta, Chitra, Anuradha, Uttara Ashadha, Uttara Bhadrapada, Revati
            fav_naks = {4, 5, 12, 13, 14, 17, 21, 26, 27}
            # Favorable Tithis: 2, 3, 5, 7, 10, 11, 12, 13, 15
            fav_tithis = {2, 3, 5, 7, 10, 11, 12, 13, 15}
            
            if nak in fav_naks:
                score += 1
                reasons.append(f"Nakshatra {panchanga.nakshatra.name} is favorable for marriage.")
            else:
                reasons.append(f"Nakshatra {panchanga.nakshatra.name} is not traditionally recommended for marriage.")
                
            if tithi in fav_tithis:
                score += 1
                reasons.append(f"Tithi {panchanga.tithi.name} is favorable for marriage.")
            else:
                reasons.append(f"Tithi {panchanga.tithi.name} is not recommended for marriage.")
                
        elif event_lower == "business":
            # Favorable Nakshatras: Ashwini, Rohini, Pushya, Uttara Phalguni, Hasta, Chitra, Anuradha, Uttara Ashadha, Shravana, Dhanistha, Shatabhisha, Uttara Bhadrapada, Revati
            fav_naks = {1, 4, 8, 12, 13, 14, 17, 21, 22, 23, 24, 26, 27}
            fav_tithis = {2, 3, 5, 7, 10, 11, 12, 13, 15}
            
            if nak in fav_naks:
                score += 1
                reasons.append(f"Nakshatra {panchanga.nakshatra.name} is favorable for business startup.")
            else:
                reasons.append(f"Nakshatra {panchanga.nakshatra.name} is neutral/not ideal for business startup.")
                
            if tithi in fav_tithis:
                score += 1
                reasons.append(f"Tithi {panchanga.tithi.name} is favorable for business startup.")
            else:
                reasons.append(f"Tithi {panchanga.tithi.name} is not recommended for starting business.")
                
        elif event_lower == "travel":
            # Favorable Nakshatras: Ashwini, Punarvasu, Hasta, Swati, Shravana, Dhanistha, Shatabhisha, Revati
            fav_naks = {1, 7, 13, 15, 22, 23, 24, 27}
            # Avoid Rikta (4, 9, 14)
            
            if nak in fav_naks:
                score += 1
                reasons.append(f"Nakshatra {panchanga.nakshatra.name} is favorable for travel.")
            else:
                reasons.append(f"Nakshatra {panchanga.nakshatra.name} is neutral/not ideal for travel.")
                
            if tithi not in {4, 9, 14}:
                score += 1
                reasons.append(f"Tithi {panchanga.tithi.name} is suitable (avoiding Rikta).")
            else:
                reasons.append(f"Tithi {panchanga.tithi.name} (Rikta) is inauspicious for travel.")
                
        elif event_lower == "house_purchase":
            # Favorable Nakshatras: Rohini, Mrigashira, Punarvasu, Uttara Phalguni, Hasta, Chitra, Anuradha, Uttara Ashadha, Shravana, Dhanistha, Shatabhisha, Uttara Bhadrapada, Revati
            fav_naks = {4, 5, 7, 12, 13, 14, 17, 21, 22, 23, 24, 26, 27}
            fav_tithis = {2, 3, 5, 7, 10, 11, 12, 13, 15}
            
            if nak in fav_naks:
                score += 1
                reasons.append(f"Nakshatra {panchanga.nakshatra.name} is favorable for property purchase.")
            else:
                reasons.append(f"Nakshatra {panchanga.nakshatra.name} is neutral/not ideal for property purchase.")
                
            if tithi in fav_tithis:
                score += 1
                reasons.append(f"Tithi {panchanga.tithi.name} is favorable for property purchase.")
            else:
                reasons.append(f"Tithi {panchanga.tithi.name} is inauspicious for purchasing property.")
                
        elif event_lower == "surgery":
            # Ugra or Tikshna Nakshatras are good for surgery (Bharani, Ardra, Ashlesha, Magha, Purva Phalguni, Jyeshtha, Mula, Purva Ashadha, Purva Bhadrapada)
            fav_naks = {2, 6, 9, 10, 11, 18, 19, 20, 25}
            # Avoid Rikta (4, 9, 14) and Amavasya (30)
            
            if nak in fav_naks:
                score += 1
                reasons.append(f"Nakshatra {panchanga.nakshatra.name} (Fierce/Sharp) is favorable for surgery.")
            else:
                reasons.append(f"Nakshatra {panchanga.nakshatra.name} is not recommended for surgery.")
                
            if tithi not in {4, 9, 14, 30}:
                score += 1
                reasons.append(f"Tithi {panchanga.tithi.name} is suitable for surgery (not Rikta/Amavasya).")
            else:
                reasons.append(f"Tithi {panchanga.tithi.name} is inauspicious for surgical operations.")
        else:
            # Generic/Default event
            score += 2
            reasons.append("Generic rules applied.")

        # Calculate suitability rating
        rating_pct = (score / total_checks) * 100
        suitability = "High" if rating_pct >= 75 else "Medium" if rating_pct >= 50 else "Low"
        
        return {
            "date": transit_date_str,
            "event_type": event_type,
            "suitability": suitability,
            "suitability_percentage": rating_pct,
            "tarabala": tarabala,
            "chandrabala": chandrabala,
            "tithi": panchanga.tithi.model_dump(),
            "nakshatra": panchanga.nakshatra.model_dump(),
            "reasons": reasons,
        }

"""
Transit Engine — Layer I

Calculates transits (Gochar) of planets for a specific date
against a natal birth chart.
"""

from __future__ import annotations
from typing import Optional

from jyotisha.models.schemas import Chart, TransitResult, TransitHit
from jyotisha.engines.astronomy import AstronomicalEngine
from jyotisha.engines.calendar import CalendarEngine
from jyotisha.constants import SPECIAL_ASPECTS

class TransitEngine:
    """
    Computes transiting planetary positions and their relation
    to the natal chart (especially Gochar from natal Moon).
    """

    def __init__(self, astro_engine: Optional[AstronomicalEngine] = None):
        self.astro = astro_engine or AstronomicalEngine()
        self.calendar = CalendarEngine()

    def compute_transits(self, natal_chart: Chart, target_date_str: str) -> TransitResult:
        """
        Compute transits for a specific UTC target date (YYYY-MM-DD) or datetime.
        """
        if "T" in target_date_str:
            date_part, time_part = target_date_str.split("T")
        else:
            date_part = target_date_str
            time_part = "12:00:00"

        # 1. Create a dummy event for the target date to get JD
        target_event = self.calendar.normalize_birth_event(
            date_str=date_part,
            time_str=time_part,
            latitude=natal_chart.birth_event.location.latitude if natal_chart.birth_event else 0.0,
            longitude=natal_chart.birth_event.location.longitude if natal_chart.birth_event else 0.0,
            location_name="Transit Location"
        )
        
        # 2. Get transiting planet positions
        transit_planets = []
        positions_dict = self.astro.compute_planet_positions(target_event.julian_day)
        
        for p_name, pos_data in positions_dict.items():
            if p_name in ["Ascendant", "mc"]:
                continue
            
            # Map dict to PlanetPosition
            from jyotisha.models.schemas import PlanetPosition, DignityInfo
            
            # Just create a basic DignityInfo as transits usually don't need deep dignity resolution 
            # unless specifically requested. We'll set it to neutral.
            dignity = DignityInfo(status="Neutral")
            
            pos = PlanetPosition(
                name=pos_data["name"],
                longitude=pos_data["longitude"],
                latitude=pos_data["latitude"],
                distance=pos_data["distance"],
                speed=pos_data["speed"],
                sign=pos_data["sign"],
                sign_number=pos_data["sign_number"],
                house=1, # Default, not computing houses for pure transits yet
                degree_in_sign=pos_data["degree_in_sign"],
                retrograde=pos_data["retrograde"],
                combust=pos_data["combust"],
                nakshatra=pos_data["nakshatra"],
                nakshatra_number=pos_data["nakshatra_number"],
                pada=pos_data["pada"],
                nakshatra_lord=pos_data["nakshatra_lord"],
                dignity=dignity
            )
            transit_planets.append(pos)
                
        # 3. Calculate Gochar from Natal Moon
        gochara = {}
        natal_moon = natal_chart.get_planet("Moon")
        if natal_moon:
            moon_sign = natal_moon.sign_number
            for tp in transit_planets:
                # 1-indexed house from natal moon
                house_from_moon = ((tp.sign_number - moon_sign) % 12) + 1
                gochara[tp.name] = house_from_moon
                
        # 4. Check for exact hits (orb <= 1.0 degree)
        hits = []
        for tp in transit_planets:
            for np in natal_chart.planets:
                # Same sign conjunction
                if tp.sign_number == np.sign_number:
                    orb = abs(tp.degree_in_sign - np.degree_in_sign)
                    if orb <= 3.0:
                        hits.append(TransitHit(
                            transit_planet=tp.name,
                            natal_point=np.name,
                            aspect_type="Conjunction",
                            orb=round(orb, 2),
                            is_exact=orb <= 1.0
                        ))
                
                # Check 7th house aspect (Opposition)
                opp_sign = (tp.sign_number + 6) % 12
                if np.sign_number == opp_sign:
                    orb = abs(tp.degree_in_sign - np.degree_in_sign)
                    if orb <= 3.0:
                        hits.append(TransitHit(
                            transit_planet=tp.name,
                            natal_point=np.name,
                            aspect_type="Opposition (7th Aspect)",
                            orb=round(orb, 2),
                            is_exact=orb <= 1.0
                        ))
                        
                # Check special aspects
                if tp.name in SPECIAL_ASPECTS:
                    for asp_house in SPECIAL_ASPECTS[tp.name]:
                        asp_sign = (tp.sign_number + asp_house - 1) % 12
                        if np.sign_number == asp_sign:
                            orb = abs(tp.degree_in_sign - np.degree_in_sign)
                            if orb <= 3.0:
                                hits.append(TransitHit(
                                    transit_planet=tp.name,
                                    natal_point=np.name,
                                    aspect_type=f"{asp_house}th Aspect",
                                    orb=round(orb, 2),
                                    is_exact=orb <= 1.0
                                ))

        return TransitResult(
            date=target_date_str,
            transit_planets=transit_planets,
            hits=hits,
            gochara_from_moon=gochara
        )

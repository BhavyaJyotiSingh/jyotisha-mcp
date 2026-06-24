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
from jyotisha.constants import SPECIAL_ASPECTS, Planet

class TransitEngine:
    """
    Computes transiting planetary positions and their relation
    to the natal chart (especially Gochar from natal Moon).
    """

    GOCHARA_FAVORABLE_HOUSES = {
        "Sun": {3, 6, 10, 11},
        "Moon": {1, 3, 6, 7, 10, 11},
        "Mars": {3, 6, 11},
        "Mercury": {2, 4, 6, 8, 10, 11},
        "Jupiter": {2, 5, 7, 9, 11},
        "Venus": {1, 2, 3, 4, 5, 8, 9, 11, 12},
        "Saturn": {3, 6, 11},
    }

    VEDHA_MAP = {
        "Sun": {3: 9, 6: 12, 10: 4, 11: 5},
        "Moon": {1: 5, 3: 9, 6: 12, 7: 2, 10: 4, 11: 8},
        "Mars": {3: 12, 6: 9, 11: 5},
        "Mercury": {2: 5, 4: 3, 6: 1, 8: 12, 10: 8, 11: 9},
        "Jupiter": {2: 12, 5: 4, 7: 3, 9: 10, 11: 8},
        "Venus": {1: 8, 2: 7, 3: 1, 4: 10, 5: 9, 8: 5, 9: 11, 11: 3, 12: 6},
        "Saturn": {3: 12, 6: 9, 11: 5},
    }

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
        gochara_assessment = self.compute_gochara_assessment(gochara)
        sade_sati = self.compute_sade_sati_status(gochara)
        double_transit_activations = self.compute_double_transit_activations(
            natal_chart=natal_chart,
            transit_planets=transit_planets,
        )
                
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
                try:
                    tp_enum = Planet(tp.name)
                except ValueError:
                    tp_enum = None
                if tp_enum in SPECIAL_ASPECTS:
                    for asp_house in SPECIAL_ASPECTS[tp_enum]:
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
            gochara_from_moon=gochara,
            gochara_assessment=gochara_assessment,
            double_transit_activations=double_transit_activations,
            sade_sati=sade_sati,
        )

    @classmethod
    def compute_gochara_assessment(cls, gochara_from_moon: dict[str, int]) -> dict:
        """
        Assess transit favorability from natal Moon using the BPHS gochar table,
        incorporating Vedha (obstruction) rules.
        """
        assessment = {}
        for planet, house_from_moon in gochara_from_moon.items():
            favorable_houses = cls.GOCHARA_FAVORABLE_HOUSES.get(planet)
            if favorable_houses is None or house_from_moon is None:
                assessment[planet] = {
                    "house_from_moon": house_from_moon,
                    "status": "unknown",
                    "is_favorable": None,
                    "reason": "No gochar favorability rule is configured for this planet.",
                    "vedha_house": None,
                    "vedha_blocked": False,
                    "vedha_blocker": None,
                }
                continue

            is_favorable = house_from_moon in favorable_houses
            status = "favorable" if is_favorable else "unfavorable"
            
            vedha_house = cls.VEDHA_MAP.get(planet, {}).get(house_from_moon)
            vedha_blocked = False
            vedha_blocker = None
            
            if is_favorable and vedha_house is not None:
                for other_planet, other_house in gochara_from_moon.items():
                    if other_planet == planet:
                        continue
                    if other_planet not in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
                        continue
                    if other_house == vedha_house:
                        # Check exceptions
                        is_exception = (
                            (planet == "Sun" and other_planet == "Saturn") or
                            (planet == "Saturn" and other_planet == "Sun") or
                            (planet == "Moon" and other_planet == "Mercury") or
                            (planet == "Mercury" and other_planet == "Moon")
                        )
                        if not is_exception:
                            vedha_blocked = True
                            vedha_blocker = other_planet
                            break

            final_status = "blocked" if vedha_blocked else status

            assessment[planet] = {
                "house_from_moon": house_from_moon,
                "status": final_status,
                "is_favorable": is_favorable and not vedha_blocked,
                "favorable_houses": sorted(favorable_houses),
                "vedha_house": vedha_house,
                "vedha_blocked": vedha_blocked,
                "vedha_blocker": vedha_blocker,
                "reason": (
                    f"{planet} transit in house {house_from_moon} from natal Moon is blocked by "
                    f"{vedha_blocker} in house {vedha_house}." if vedha_blocked else
                    f"{planet} is {status} in house {house_from_moon} from natal Moon."
                ),
            }

        return assessment

    @staticmethod
    def compute_double_transit_activations(
        natal_chart: Chart,
        transit_planets: list,
    ) -> list[dict]:
        """
        Identify natal houses activated by both transiting Jupiter and Saturn.

        A house is counted as activated when its natal sign is occupied or
        fully aspected by both planets. Jupiter uses 5th/7th/9th aspects;
        Saturn uses 3rd/7th/10th aspects.
        """
        transit_by_name = {planet.name: planet for planet in transit_planets}
        jupiter = transit_by_name.get("Jupiter")
        saturn = transit_by_name.get("Saturn")
        if jupiter is None or saturn is None:
            return []

        jupiter_targets = TransitEngine._transit_activated_signs(
            jupiter.sign_number,
            aspect_houses={5, 7, 9},
        )
        saturn_targets = TransitEngine._transit_activated_signs(
            saturn.sign_number,
            aspect_houses={3, 7, 10},
        )
        jointly_activated_signs = jupiter_targets & saturn_targets

        activations = []
        for house in natal_chart.houses:
            if house.sign_number not in jointly_activated_signs:
                continue

            activations.append(
                {
                    "house": house.number,
                    "sign": house.sign,
                    "sign_number": house.sign_number,
                    "jupiter_relation": TransitEngine._transit_relation_to_sign(
                        jupiter.sign_number,
                        house.sign_number,
                        aspect_houses={5, 7, 9},
                    ),
                    "saturn_relation": TransitEngine._transit_relation_to_sign(
                        saturn.sign_number,
                        house.sign_number,
                        aspect_houses={3, 7, 10},
                    ),
                }
            )

        return activations

    @staticmethod
    def _transit_activated_signs(
        sign_number: int,
        aspect_houses: set[int],
    ) -> set[int]:
        """Return occupied and fully aspected signs for a transiting planet."""
        return {sign_number} | {
            (sign_number + aspect_house - 1) % 12
            for aspect_house in aspect_houses
        }

    @staticmethod
    def _transit_relation_to_sign(
        transit_sign_number: int,
        target_sign_number: int,
        aspect_houses: set[int],
    ) -> str:
        """Describe whether a transit occupies or aspects a target sign."""
        if target_sign_number == transit_sign_number:
            return "occupation"

        for aspect_house in sorted(aspect_houses):
            if target_sign_number == (transit_sign_number + aspect_house - 1) % 12:
                return f"{aspect_house}th aspect"

        return "none"

    @staticmethod
    def compute_sade_sati_status(gochara_from_moon: dict[str, int]) -> dict:
        """
        Determine Sade Sati from Saturn's transit relative to the natal Moon.

        Sade Sati is active when Saturn transits the 12th, 1st, or 2nd house
        counted from the natal Moon sign.
        """
        saturn_house = gochara_from_moon.get("Saturn")
        phases = {
            12: ("Rising", "Saturn transits the 12th house from natal Moon."),
            1: ("Peak", "Saturn transits the natal Moon sign."),
            2: ("Setting", "Saturn transits the 2nd house from natal Moon."),
        }

        phase_data = phases.get(saturn_house)
        if phase_data is None:
            return {
                "active": False,
                "saturn_house_from_moon": saturn_house,
                "phase": None,
                "severity": "none",
                "description": "Saturn is not transiting 12th, 1st, or 2nd from natal Moon.",
            }

        phase, description = phase_data
        severity = "high" if saturn_house == 1 else "medium"
        return {
            "active": True,
            "saturn_house_from_moon": saturn_house,
            "phase": phase,
            "severity": severity,
            "description": description,
        }

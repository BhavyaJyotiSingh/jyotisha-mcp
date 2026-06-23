"""
Chart Generation Engine — Layer C & D

Generates Rashi (D1) and all Divisional (Varga) charts.
Combines astronomical positions with house assignments,
dignity calculations, aspect computations, planetary war,
and Pushkara Navamsha.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

from jyotisha.constants import (
    SIGN_NAMES, SIGN_LORDS, Sign, Ayanamsha,
)
from jyotisha.models.schemas import (
    Chart, ChartMetadata, PlanetPosition, Ascendant, House, BirthEvent,
)
from jyotisha.engines.astronomy import (
    AstronomicalEngine, compute_dignity, compute_aspects,
)
from jyotisha.engines.houses import get_house_strategy
from jyotisha.engines.calendar import CalendarEngine


def is_pushkara_navamsa(sign_number: int, degree_in_sign: float) -> bool:
    """
    Check if a planet is in Pushkara Navamsha based on its sign and degree.
    """
    element_type = sign_number % 4
    if element_type == 0:  # Fire (Aries, Leo, Sagittarius)
        return (20.0 <= degree_in_sign <= 23.33333) or (26.66667 <= degree_in_sign <= 30.0)
    elif element_type == 1:  # Earth (Taurus, Virgo, Capricorn)
        return (6.66667 <= degree_in_sign <= 10.0) or (13.33333 <= degree_in_sign <= 16.66667)
    elif element_type == 2:  # Air (Gemini, Libra, Aquarius)
        return (16.66667 <= degree_in_sign <= 20.0) or (23.33333 <= degree_in_sign <= 26.66667)
    elif element_type == 3:  # Water (Cancer, Scorpio, Pisces)
        return (0.0 <= degree_in_sign <= 3.33333) or (6.66667 <= degree_in_sign <= 10.0)
    return False


def compute_graha_yuddhas(planets_data: dict[str, dict]) -> dict[str, str]:
    """
    Computes Graha Yuddha (planetary war).
    Returns a dict mapping planet name to its war status.
    """
    from jyotisha.constants import Planet
    warring = [Planet.SUN.value, Planet.MOON.value, Planet.MARS.value, Planet.MERCURY.value, Planet.JUPITER.value, Planet.VENUS.value, Planet.SATURN.value, Planet.RAHU.value, Planet.KETU.value]
    results = {}
    
    # Compare all pairs
    for i in range(len(warring)):
        for j in range(i + 1, len(warring)):
            p1 = warring[i]
            p2 = warring[j]
            if p1 in planets_data and p2 in planets_data:
                lon1 = planets_data[p1]["longitude"]
                lon2 = planets_data[p2]["longitude"]
                diff = abs(lon1 - lon2) % 360.0
                diff = min(diff, 360.0 - diff)
                
                if diff <= 1.0:
                    # Winner is the one with higher (more northern) latitude (classical rule)
                    lat1 = planets_data[p1].get("latitude", 0.0)
                    lat2 = planets_data[p2].get("latitude", 0.0)
                    if lat1 > lat2:
                        results[p1] = f"Won against {p2}"
                        results[p2] = f"Lost to {p1}"
                    else:
                        results[p2] = f"Won against {p1}"
                        results[p1] = f"Lost to {p2}"
    return results


class ChartEngine:
    """
    Generates complete Vedic charts (Rashi + Divisional).
    """

    def __init__(
        self,
        ayanamsha: int = Ayanamsha.LAHIRI,
        house_system: str = "W",  # Whole Sign
        true_nodes: bool = True,
        topocentric: bool = False,
    ):
        self.astro = AstronomicalEngine(
            ayanamsha=ayanamsha,
            true_nodes=true_nodes,
            topocentric=topocentric,
        )
        self.calendar = CalendarEngine()
        self.house_system = house_system
        self.ayanamsha = ayanamsha
        self.topocentric = topocentric

    def generate_birth_chart(
        self,
        datetime_str: str,
        latitude: float,
        longitude: float,
        time_str: Optional[str] = None,
        location_name: Optional[str] = None,
    ) -> Chart:
        """
        Generate a complete Vedic birth chart (D1/Rashi).
        """
        # Parse datetime
        if "T" in datetime_str and time_str is None:
            date_part = datetime_str.split("T")[0]
            time_part = datetime_str.split("T")[1]
        else:
            date_part = datetime_str
            time_part = time_str

        # Normalize birth event
        event = self.calendar.normalize_birth_event(
            date_str=date_part,
            time_str=time_part,
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
        )

        return self.generate_chart_from_event(event)

    def generate_chart_from_event(self, event: BirthEvent) -> Chart:
        """Generate a chart from a normalized BirthEvent."""
        jd = event.julian_day
        lat = event.location.latitude
        lon = event.location.longitude

        # Compute planet positions
        raw_positions = self.astro.compute_planet_positions(jd, lat, lon)

        # Compute ascendant and houses
        asc_data = self.astro.compute_ascendant(jd, lat, lon, self.house_system)
        asc_sign_num = asc_data["ascendant"]["sign_number"]

        # Build ascendant model
        asc_raw = asc_data["ascendant"]
        ascendant = Ascendant(
            longitude=asc_raw["longitude"],
            sign=asc_raw["sign"],
            sign_number=asc_raw["sign_number"],
            degree_in_sign=asc_raw["degree_in_sign"],
            nakshatra=asc_raw["nakshatra"],
            nakshatra_number=asc_raw["nakshatra_number"],
            pada=asc_raw["pada"],
            lord=SIGN_LORDS[Sign(asc_raw["sign_number"])].value,
        )

        # Create house strategy
        strategy = get_house_strategy(self.house_system)
        houses = strategy.build_houses(asc_sign_num, asc_data.get("cusps", []))

        # Compute planetary war (Graha Yuddha)
        war_results = compute_graha_yuddhas(raw_positions)

        # Build planet models
        planets = []
        for name, data in raw_positions.items():
            # House number will be updated by the strategy later
            house_num = 1

            # Compute dignity
            dignity = compute_dignity(name, data["sign_number"], data["degree_in_sign"])

            # Check vargottama
            from jyotisha.engines.varga import VargaEngine
            varga_engine = VargaEngine()
            navamsa_sign = varga_engine.compute_varga_sign(data["longitude"], 9)
            is_vargottama = (data["sign_number"] == navamsa_sign)

            # Check Pushkara Navamsha
            p_pushkara = is_pushkara_navamsa(data["sign_number"], data["degree_in_sign"])

            planet = PlanetPosition(
                name=name,
                longitude=data["longitude"],
                latitude=data.get("latitude", 0.0),
                distance=data.get("distance", 0.0),
                speed=data.get("speed", 0.0),
                sign=data["sign"],
                sign_number=data["sign_number"],
                house=house_num,
                degree_in_sign=data["degree_in_sign"],
                retrograde=data["retrograde"],
                combust=data.get("combust", False),
                planetary_war=war_results.get(name),
                nakshatra=data["nakshatra"],
                nakshatra_number=data["nakshatra_number"],
                pada=data["pada"],
                nakshatra_lord=data["nakshatra_lord"].value,
                dignity=dignity,
                vargottama=is_vargottama,
                pushkara_navamsa=p_pushkara,
            )
            planets.append(planet)

        # Assign planets to houses using strategy
        houses = strategy.assign_planets(houses, planets)

        # Compute aspects
        aspects = compute_aspects(raw_positions)
        houses = self._assign_lords_and_aspects_to_houses(
            houses, planets, aspects
        )

        ayan_value = self.astro.get_ayanamsha_value(jd)
        ayan_names = {
            Ayanamsha.LAHIRI: "Lahiri",
            Ayanamsha.RAMAN: "Raman",
            Ayanamsha.KRISHNAMURTI: "KP (Krishnamurti)",
            Ayanamsha.YUKTESWAR: "Yukteswar",
            Ayanamsha.FAGAN_BRADLEY: "Fagan-Bradley",
            Ayanamsha.TRUE_CITRA: "True Chitrapaksha",
        }

        metadata = ChartMetadata(
            chart_type="D1",
            ayanamsha=ayan_names.get(self.ayanamsha, f"ID_{self.ayanamsha}"),
            ayanamsha_value=round(ayan_value, 4),
            house_system="Whole Sign" if self.house_system == "W" else self.house_system,
            true_nodes=self.astro.true_nodes,
            topocentric=self.topocentric,
            computed_at=datetime.now(timezone.utc),
        )

        return Chart(
            ascendant=ascendant,
            planets=planets,
            houses=houses,
            metadata=metadata,
            birth_event=event,
        )

    # ─────────────────────────────────────────────────────────
    # Divisional Charts (Vargas)
    # ─────────────────────────────────────────────────────────

    def generate_divisional_chart(
        self,
        base_chart: Chart,
        division: int = 9,
    ) -> Chart:
        """
        Generate a divisional chart from a base D1 chart.
        """
        from jyotisha.engines.varga import VargaEngine
        varga_engine = VargaEngine()

        if division not in varga_engine.get_supported_vargas():
            raise ValueError(
                f"Division D{division} not supported. "
                f"Supported: {sorted(varga_engine.get_supported_vargas())}"
            )

        # Compute new lagna sign
        asc_varga_sign = varga_engine.compute_varga_sign(base_chart.ascendant.longitude, division)
        varga_asc_degree = varga_engine.compute_varga_degree(base_chart.ascendant.longitude, division)
        varga_asc_longitude = (asc_varga_sign * 30.0) + varga_asc_degree

        # Compute planet positions in the varga
        varga_planets = []
        for planet in base_chart.planets:
            new_sign = varga_engine.compute_varga_sign(planet.longitude, division)
            house_num = ((new_sign - asc_varga_sign) % 12) + 1
            
            # Vargas mathematically represent sub-divisions. We compute their exact fractional projection.
            varga_degree = varga_engine.compute_varga_degree(planet.longitude, division)
            varga_longitude = (new_sign * 30.0) + varga_degree
            dignity = compute_dignity(planet.name, new_sign, varga_degree)

            varga_planet = PlanetPosition(
                name=planet.name,
                longitude=varga_longitude,
                latitude=planet.latitude,
                distance=planet.distance,
                speed=planet.speed,
                sign=SIGN_NAMES[new_sign],
                sign_number=new_sign,
                house=house_num,
                degree_in_sign=varga_degree,
                retrograde=planet.retrograde,
                combust=planet.combust,
                in_war=planet.in_war,
                war_winner=planet.war_winner,
                nakshatra=planet.nakshatra,
                nakshatra_number=planet.nakshatra_number,
                pada=planet.pada,
                nakshatra_lord=planet.nakshatra_lord,
                dignity=dignity,
                vargottama=planet.vargottama,
                pushkara_navamsa=planet.pushkara_navamsa,
            )
            varga_planets.append(varga_planet)

        # Build houses for varga (always Whole Sign for D-charts)
        varga_strategy = get_house_strategy("W")
        houses = varga_strategy.build_houses(asc_varga_sign)
        houses = varga_strategy.assign_planets(houses, varga_planets)
        houses = self._assign_lords_and_aspects_to_houses(
            houses, varga_planets, {}
        )

        metadata = ChartMetadata(
            chart_type=f"D{division}",
            ayanamsha=base_chart.metadata.ayanamsha,
            ayanamsha_value=base_chart.metadata.ayanamsha_value,
            house_system="Whole Sign", # Vargas fundamentally use sign-based houses
            computed_at=datetime.now(timezone.utc),
        )

        return Chart(
            ascendant=Ascendant(
                longitude=varga_asc_longitude,
                sign=SIGN_NAMES[asc_varga_sign],
                sign_number=asc_varga_sign,
                degree_in_sign=varga_asc_degree,
                nakshatra=base_chart.ascendant.nakshatra,
                nakshatra_number=base_chart.ascendant.nakshatra_number,
                pada=base_chart.ascendant.pada,
                lord=SIGN_LORDS[Sign(asc_varga_sign)].value,
            ),
            planets=varga_planets,
            houses=houses,
            metadata=metadata,
            birth_event=base_chart.birth_event,
        )

    # ─────────────────────────────────────────────────────────
    # House Construction
    # ─────────────────────────────────────────────────────────

    def _assign_lords_and_aspects_to_houses(
        self,
        houses: list[House],
        planets: list[PlanetPosition],
        aspects: dict,
    ) -> list[House]:
        # Assign lord house positions
        for house in houses:
            lord_name = house.lord
            for planet in planets:
                if planet.name == lord_name:
                    house.lord_house = planet.house
                    break

        # Assign aspects
        for aspecting_planet, aspected_planets in aspects.items():
            for target in aspected_planets:
                for planet in planets:
                    if planet.name == target:
                        for house in houses:
                            if house.sign_number == planet.sign_number:
                                if aspecting_planet not in house.aspects_received:
                                    house.aspects_received.append(aspecting_planet)
                                break
                        break

        return houses

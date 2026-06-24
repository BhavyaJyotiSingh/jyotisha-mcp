"""
Chart Generation Engine — Layer C & D

Generates Rashi (D1) and all Divisional (Varga) charts.
Combines astronomical positions with house assignments,
dignity calculations, aspect computations, planetary war,
and Pushkara Navamsha.
"""

from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from typing import Optional

from jyotisha.constants import (
    Ayanamsha,
    NAKSHATRA_LORDS,
    NAKSHATRA_NAMES,
    NAKSHATRA_SPAN,
    SIGN_LORDS,
    SIGN_NAMES,
    Sign,
)
from jyotisha.models.schemas import (
    Chart, ChartMetadata, PlanetPosition, Ascendant, House, BirthEvent,
)
from jyotisha.engines.astronomy import (
    AstronomicalEngine,
    compute_aspects,
    compute_dignity,
    compute_graha_yuddhas as _compute_graha_yuddhas,
)
from jyotisha.engines.houses import get_house_strategy
from jyotisha.engines.calendar import CalendarEngine
from jyotisha.engines.varga import VargaEngine


def compute_graha_yuddhas(planets_data: dict[str, dict]) -> dict[str, str]:
    """Compatibility export for the canonical astronomy implementation."""
    return _compute_graha_yuddhas(planets_data)


def _nakshatra_fields(longitude: float) -> tuple[str, int, int, str]:
    longitude %= 360.0
    number = min(int(longitude / NAKSHATRA_SPAN), 26)
    offset = longitude - number * NAKSHATRA_SPAN
    pada = min(int(offset / (NAKSHATRA_SPAN / 4.0)) + 1, 4)
    return (
        NAKSHATRA_NAMES[number],
        number,
        pada,
        NAKSHATRA_LORDS[number].value,
    )


def is_pushkara_navamsa(sign_number: int, degree_in_sign: float) -> bool:
    """
    Check if a planet is in Pushkara Navamsha based on its sign and degree.
    """
    element_type = sign_number % 4
    one_ninth = 30.0 / 9.0
    if element_type == 0:  # Fire
        return (6 * one_ninth <= degree_in_sign < 7 * one_ninth) or (
            8 * one_ninth <= degree_in_sign < 30.0
        )
    if element_type == 1:  # Earth
        return (2 * one_ninth <= degree_in_sign < 3 * one_ninth) or (
            4 * one_ninth <= degree_in_sign < 5 * one_ninth
        )
    if element_type == 2:  # Air
        return (5 * one_ninth <= degree_in_sign < 6 * one_ninth) or (
            7 * one_ninth <= degree_in_sign < 8 * one_ninth
        )
    if element_type == 3:  # Water
        return (0.0 <= degree_in_sign < one_ninth) or (
            2 * one_ninth <= degree_in_sign < 3 * one_ninth
        )
    return False


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
        self.varga = VargaEngine()

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

        # Build planet models
        planets = []
        for name, data in raw_positions.items():
            # House number will be updated by the strategy later
            house_num = 1

            # Compute dignity
            dignity = compute_dignity(name, data["sign_number"], data["degree_in_sign"])

            # Check vargottama
            navamsa_sign = self.varga.compute_varga_sign(data["longitude"], 9)
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
                in_war=data.get("in_war", False),
                war_winner=data.get("war_winner", False),
                planetary_war=data.get("planetary_war"),
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

        computation_input = {
            "julian_day": jd,
            "latitude": lat,
            "longitude": lon,
            "altitude": event.location.altitude,
            "ayanamsha_id": int(self.ayanamsha),
            "house_system": self.house_system,
            "true_nodes": self.astro.true_nodes,
            "topocentric": self.topocentric,
            "ephemeris_version": self.astro.ephemeris_version,
        }
        computation_hash = hashlib.sha256(
            json.dumps(
                computation_input, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
        metadata = ChartMetadata(
            chart_type="D1",
            ayanamsha=ayan_names.get(self.ayanamsha, f"ID_{self.ayanamsha}"),
            ayanamsha_value=round(ayan_value, 4),
            house_system="Whole Sign" if self.house_system == "W" else self.house_system,
            true_nodes=self.astro.true_nodes,
            topocentric=self.topocentric,
            ephemeris_version=self.astro.ephemeris_version,
            delta_t_seconds=self.astro.get_delta_t(jd),
            computation_hash=computation_hash,
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
        varga_engine = self.varga

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
            nakshatra, nakshatra_number, pada, nakshatra_lord = (
                _nakshatra_fields(varga_longitude)
            )

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
                nakshatra=nakshatra,
                nakshatra_number=nakshatra_number,
                pada=pada,
                nakshatra_lord=nakshatra_lord,
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

        asc_nakshatra, asc_nakshatra_number, asc_pada, _ = _nakshatra_fields(
            varga_asc_longitude
        )
        return Chart(
            ascendant=Ascendant(
                longitude=varga_asc_longitude,
                sign=SIGN_NAMES[asc_varga_sign],
                sign_number=asc_varga_sign,
                degree_in_sign=varga_asc_degree,
                nakshatra=asc_nakshatra,
                nakshatra_number=asc_nakshatra_number,
                pada=asc_pada,
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

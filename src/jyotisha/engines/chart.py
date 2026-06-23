"""
Chart Generation Engine — Layer C & D

Generates Rashi (D1) and all Divisional (Varga) charts.
Combines astronomical positions with house assignments,
dignity calculations, and aspect computations.
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
from jyotisha.engines.calendar import CalendarEngine


class ChartEngine:
    """
    Generates complete Vedic charts (Rashi + Divisional).

    Orchestrates the astronomical engine, calendar normalization,
    and chart construction pipeline.
    """

    def __init__(
        self,
        ayanamsha: int = Ayanamsha.LAHIRI,
        house_system: str = "W",  # Whole Sign
        true_nodes: bool = True,
    ):
        self.astro = AstronomicalEngine(
            ayanamsha=ayanamsha,
            true_nodes=true_nodes,
        )
        self.calendar = CalendarEngine()
        self.house_system = house_system
        self.ayanamsha = ayanamsha

    # ─────────────────────────────────────────────────────────
    # Primary Chart Generation
    # ─────────────────────────────────────────────────────────

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

        Args:
            datetime_str: Date in "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SS"
            latitude: Geographic latitude
            longitude: Geographic longitude
            time_str: Optional time in "HH:MM" (if not included in datetime_str)
            location_name: Optional place name

        Returns:
            Complete Chart object with planets, houses, aspects.
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
            lord=SIGN_LORDS[Sign(asc_raw["sign_number"])],
        )

        # Assign houses (Whole Sign: house 1 = ascendant sign)
        houses = self._build_houses(asc_sign_num)

        # Build planet models with house assignments
        planets = []
        for name, data in raw_positions.items():
            # Compute house number (Whole Sign)
            house_num = ((data["sign_number"] - asc_sign_num) % 12) + 1

            # Compute dignity
            dignity = compute_dignity(name, data["sign_number"], data["degree_in_sign"])

            # Check vargottama (same sign in D1 and D9)
            navamsa_sign = self._compute_navamsa_sign(data["longitude"])
            is_vargottama = (data["sign_number"] == navamsa_sign)

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
                nakshatra=data["nakshatra"],
                nakshatra_number=data["nakshatra_number"],
                pada=data["pada"],
                nakshatra_lord=data["nakshatra_lord"],
                dignity=dignity,
                vargottama=is_vargottama,
            )
            planets.append(planet)

        # Compute aspects and add to houses
        aspects = compute_aspects(raw_positions)
        houses = self._assign_planets_and_aspects_to_houses(
            houses, planets, aspects, asc_sign_num
        )

        # Get ayanamsha value
        ayan_value = self.astro.get_ayanamsha_value(jd)

        # Ayanamsha name mapping
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

        Args:
            base_chart: The D1 (Rashi) chart
            division: Varga division number (2, 3, 4, 7, 9, 10, 12, etc.)

        Returns:
            Chart object for the specified division.
        """
        varga_methods = {
            2: self._compute_hora_sign,      # D2
            3: self._compute_drekkana_sign,   # D3
            4: self._compute_chaturthamsa_sign,  # D4
            7: self._compute_saptamsa_sign,   # D7
            9: self._compute_navamsa_sign,    # D9
            10: self._compute_dasamsa_sign,   # D10
            12: self._compute_dwadasamsa_sign,  # D12
            16: self._compute_shodasamsa_sign,  # D16
            20: self._compute_vimsamsa_sign,  # D20
            24: self._compute_siddhamsa_sign, # D24
            27: self._compute_bhamsa_sign,    # D27
            30: self._compute_trimsamsa_sign, # D30
            60: self._compute_shashtiamsa_sign, # D60
        }

        if division not in varga_methods:
            raise ValueError(
                f"Division D{division} not supported. "
                f"Supported: {sorted(varga_methods.keys())}"
            )

        compute_sign = varga_methods[division]

        # Compute new lagna sign
        asc_varga_sign = compute_sign(base_chart.ascendant.longitude)

        # Compute planet positions in the varga
        varga_planets = []
        for planet in base_chart.planets:
            new_sign = compute_sign(planet.longitude)
            house_num = ((new_sign - asc_varga_sign) % 12) + 1
            dignity = compute_dignity(planet.name, new_sign, 15.0)

            varga_planet = PlanetPosition(
                name=planet.name,
                longitude=planet.longitude,  # Keep original longitude for reference
                latitude=planet.latitude,
                distance=planet.distance,
                speed=planet.speed,
                sign=SIGN_NAMES[new_sign],
                sign_number=new_sign,
                house=house_num,
                degree_in_sign=planet.degree_in_sign,  # Original degree
                retrograde=planet.retrograde,
                combust=planet.combust,
                nakshatra=planet.nakshatra,
                nakshatra_number=planet.nakshatra_number,
                pada=planet.pada,
                nakshatra_lord=planet.nakshatra_lord,
                dignity=dignity,
                vargottama=planet.vargottama,
            )
            varga_planets.append(varga_planet)

        # Build houses for varga
        houses = self._build_houses(asc_varga_sign)
        houses = self._assign_planets_and_aspects_to_houses(
            houses, varga_planets, {}, asc_varga_sign
        )

        metadata = ChartMetadata(
            chart_type=f"D{division}",
            ayanamsha=base_chart.metadata.ayanamsha,
            ayanamsha_value=base_chart.metadata.ayanamsha_value,
            house_system=base_chart.metadata.house_system,
            computed_at=datetime.now(timezone.utc),
        )

        return Chart(
            ascendant=Ascendant(
                longitude=base_chart.ascendant.longitude,
                sign=SIGN_NAMES[asc_varga_sign],
                sign_number=asc_varga_sign,
                degree_in_sign=base_chart.ascendant.degree_in_sign,
                nakshatra=base_chart.ascendant.nakshatra,
                nakshatra_number=base_chart.ascendant.nakshatra_number,
                pada=base_chart.ascendant.pada,
                lord=SIGN_LORDS[Sign(asc_varga_sign)],
            ),
            planets=varga_planets,
            houses=houses,
            metadata=metadata,
            birth_event=base_chart.birth_event,
        )

    # ─────────────────────────────────────────────────────────
    # House Construction
    # ─────────────────────────────────────────────────────────

    def _build_houses(self, asc_sign_num: int) -> list[House]:
        """Build 12 houses starting from the ascendant sign (Whole Sign system)."""
        houses = []
        for i in range(12):
            sign_num = (asc_sign_num + i) % 12
            sign = Sign(sign_num)
            houses.append(House(
                number=i + 1,
                sign=SIGN_NAMES[sign_num],
                sign_number=sign_num,
                lord=SIGN_LORDS[sign],
                planets_in_house=[],
                aspects_received=[],
            ))
        return houses

    def _assign_planets_and_aspects_to_houses(
        self,
        houses: list[House],
        planets: list[PlanetPosition],
        aspects: dict,
        asc_sign_num: int,
    ) -> list[House]:
        """Populate houses with planet occupants and received aspects."""
        # Assign planets to houses
        for planet in planets:
            for house in houses:
                if house.sign_number == planet.sign_number:
                    house.planets_in_house.append(planet.name)
                    break

        # Assign lord house positions
        for house in houses:
            lord_name = house.lord
            for planet in planets:
                if planet.name == lord_name:
                    house.lord_house = planet.house
                    break

        # Assign aspects received
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

    # ─────────────────────────────────────────────────────────
    # Varga Sign Computation Methods
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def _compute_navamsa_sign(longitude: float) -> int:
        """D9 Navamsa: divide each sign into 9 parts of 3°20'."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / (30.0 / 9))
        # Starting sign based on element
        element = sign % 4
        starts = [0, 9, 6, 3]  # Fire→Aries, Earth→Cap, Air→Libra, Water→Cancer
        return (starts[element] + part) % 12

    @staticmethod
    def _compute_hora_sign(longitude: float) -> int:
        """D2 Hora: 2 parts of 15° each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        if deg < 15:
            # Odd signs → Sun (Leo), Even signs → Moon (Cancer)
            return Sign.LEO if sign % 2 == 0 else Sign.CANCER
        else:
            return Sign.CANCER if sign % 2 == 0 else Sign.LEO

    @staticmethod
    def _compute_drekkana_sign(longitude: float) -> int:
        """D3 Drekkana: 3 parts of 10° each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 10)
        # 1st decanate = same sign, 2nd = 5th sign, 3rd = 9th sign
        offsets = [0, 4, 8]
        return (sign + offsets[part]) % 12

    @staticmethod
    def _compute_chaturthamsa_sign(longitude: float) -> int:
        """D4 Chaturthamsha: 4 parts of 7°30' each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 7.5)
        if part > 3:
            part = 3
        return (sign + part * 3) % 12

    @staticmethod
    def _compute_saptamsa_sign(longitude: float) -> int:
        """D7 Saptamsha: 7 parts of 4°17'8.57\" each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / (30.0 / 7))
        if part > 6:
            part = 6
        # Odd signs start from same sign, even signs start from 7th sign
        if sign % 2 == 0:  # Odd sign (0-indexed)
            return (sign + part) % 12
        else:
            return (sign + 6 + part) % 12

    @staticmethod
    def _compute_dasamsa_sign(longitude: float) -> int:
        """D10 Dasamsha: 10 parts of 3° each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 3)
        if part > 9:
            part = 9
        # Odd signs start from same, even from 9th
        if sign % 2 == 0:
            return (sign + part) % 12
        else:
            return (sign + 8 + part) % 12

    @staticmethod
    def _compute_dwadasamsa_sign(longitude: float) -> int:
        """D12 Dwadashamsha: 12 parts of 2°30' each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 2.5)
        if part > 11:
            part = 11
        return (sign + part) % 12

    @staticmethod
    def _compute_shodasamsa_sign(longitude: float) -> int:
        """D16 Shodashamsha: 16 parts of 1°52'30\" each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / (30.0 / 16))
        if part > 15:
            part = 15
        # Movable→Aries, Fixed→Leo, Dual→Sagittarius
        modality = sign % 3
        starts = [0, 4, 8]
        return (starts[modality] + part) % 12

    @staticmethod
    def _compute_vimsamsa_sign(longitude: float) -> int:
        """D20 Vimshamsha: 20 parts of 1°30' each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / (30.0 / 20))
        if part > 19:
            part = 19
        # Movable→Aries, Fixed→Sagittarius, Dual→Leo
        modality = sign % 3
        starts = [0, 8, 4]
        return (starts[modality] + part) % 12

    @staticmethod
    def _compute_siddhamsa_sign(longitude: float) -> int:
        """D24 Siddhamsha: 24 parts of 1°15' each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / (30.0 / 24))
        if part > 23:
            part = 23
        # Odd signs start from Leo, even from Cancer
        if sign % 2 == 0:
            return (Sign.LEO + part) % 12
        else:
            return (Sign.CANCER + part) % 12

    @staticmethod
    def _compute_bhamsa_sign(longitude: float) -> int:
        """D27 Bhamsha/Nakshatramsha: 27 parts per sign."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / (30.0 / 27))
        if part > 26:
            part = 26
        # Fire signs→Aries, Earth→Cancer, Air→Libra, Water→Capricorn
        element = sign % 4
        starts = [0, 3, 6, 9]
        return (starts[element] + part) % 12

    @staticmethod
    def _compute_trimsamsa_sign(longitude: float) -> int:
        """
        D30 Trimshamsha: irregular division per BPHS.
        Odd signs: Mars(5°), Saturn(5°), Jupiter(8°), Mercury(7°), Venus(5°)
        Even signs: reverse order
        """
        sign = int(longitude // 30)
        deg = longitude % 30

        if sign % 2 == 0:  # Odd sign
            segments = [
                (5, Sign.ARIES),      # Mars
                (10, Sign.AQUARIUS),   # Saturn
                (18, Sign.SAGITTARIUS),  # Jupiter
                (25, Sign.GEMINI),     # Mercury
                (30, Sign.LIBRA),      # Venus
            ]
        else:  # Even sign
            segments = [
                (5, Sign.LIBRA),       # Venus
                (12, Sign.GEMINI),     # Mercury
                (20, Sign.SAGITTARIUS),  # Jupiter
                (25, Sign.AQUARIUS),   # Saturn
                (30, Sign.ARIES),      # Mars
            ]

        for boundary, result_sign in segments:
            if deg < boundary:
                return result_sign
        return segments[-1][1]

    @staticmethod
    def _compute_shashtiamsa_sign(longitude: float) -> int:
        """D60 Shashtiamsha: 60 parts of 0°30' each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 0.5)
        if part > 59:
            part = 59
        return (sign + part) % 12

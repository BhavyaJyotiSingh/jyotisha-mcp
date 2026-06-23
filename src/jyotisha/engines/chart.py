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
    Computes Graha Yuddha (planetary war) between Mars, Mercury, Jupiter, Venus, Saturn.
    Returns a dict mapping planet name to its war status.
    """
    warring = ["Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
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
            navamsa_sign = self._compute_navamsa_sign(data["longitude"])
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
        varga_methods = {
            2: self._compute_hora_sign,
            3: self._compute_drekkana_sign,
            4: self._compute_chaturthamsa_sign,
            5: self._compute_panchamsa_sign,
            6: self._compute_shasthamsa_sign,
            7: self._compute_saptamsa_sign,
            8: self._compute_ashtamsa_sign,
            9: self._compute_navamsa_sign,
            10: self._compute_dasamsa_sign,
            11: self._compute_rudramsa_sign,
            12: self._compute_dwadasamsa_sign,
            16: self._compute_shodasamsa_sign,
            20: self._compute_vimsamsa_sign,
            24: self._compute_siddhamsa_sign,
            27: self._compute_bhamsa_sign,
            30: self._compute_trimsamsa_sign,
            40: self._compute_khavedamsa_sign,
            45: self._compute_akshavedamsa_sign,
            60: self._compute_shashtiamsa_sign,
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
            
            # Vargas mathematically represent sub-divisions. We set them to the center of the sign
            # to prevent downstream code from misinterpreting D1 degrees as varga coordinates.
            varga_degree = 15.0
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
                planetary_war=planet.planetary_war,
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

        varga_asc_longitude = (asc_varga_sign * 30.0) + 15.0
        return Chart(
            ascendant=Ascendant(
                longitude=varga_asc_longitude,
                sign=SIGN_NAMES[asc_varga_sign],
                sign_number=asc_varga_sign,
                degree_in_sign=15.0,
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

    # ─────────────────────────────────────────────────────────
    # Varga Sign Computation Methods
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def _compute_navamsa_sign(longitude: float) -> int:
        """D9 Navamsa: divide each sign into 9 parts of 3°20'."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / (30.0 / 9))
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
            return Sign.LEO.value if sign % 2 == 0 else Sign.CANCER.value
        else:
            return Sign.CANCER.value if sign % 2 == 0 else Sign.LEO.value

    @staticmethod
    def _compute_drekkana_sign(longitude: float) -> int:
        """D3 Drekkana: 3 parts of 10° each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 10)
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
    def _compute_panchamsa_sign(longitude: float) -> int:
        """D5 Panchamsha: 5 parts of 6° each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 6.0)
        if part > 4:
            part = 4

        # Odd signs (Mesha, Mithuna, Simha, Tula, Dhanu, Kumbha)
        odd_map = [Sign.ARIES.value, Sign.AQUARIUS.value, Sign.SAGITTARIUS.value, Sign.GEMINI.value, Sign.LIBRA.value]
        # Even signs
        even_map = [Sign.TAURUS.value, Sign.VIRGO.value, Sign.PISCES.value, Sign.CAPRICORN.value, Sign.SCORPIO.value]

        if sign % 2 == 0:  # Odd sign (0-indexed: Aries is 0)
            return odd_map[part]
        else:
            return even_map[part]

    @staticmethod
    def _compute_shasthamsa_sign(longitude: float) -> int:
        """D6 Shasthamsa: 6 parts of 5° each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 5.0)
        if part > 5:
            part = 5

        # Odd signs start from Aries, Even signs start from Libra
        start = Sign.ARIES.value if sign % 2 == 0 else Sign.LIBRA.value
        return (start + part) % 12

    @staticmethod
    def _compute_saptamsa_sign(longitude: float) -> int:
        """D7 Saptamsha: 7 parts of 4°17'8.57\" each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / (30.0 / 7))
        if part > 6:
            part = 6
        if sign % 2 == 0:  # Odd sign
            return (sign + part) % 12
        else:
            return (sign + 6 + part) % 12

    @staticmethod
    def _compute_ashtamsa_sign(longitude: float) -> int:
        """D8 Ashtamsha: 8 parts of 3°45' each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 3.75)
        if part > 7:
            part = 7

        modality = sign % 3  # 0 = Movable, 1 = Fixed, 2 = Dual
        if modality == 0:
            start = sign
        elif modality == 1:
            start = (sign + 8) % 12
        else:
            start = (sign + 4) % 12
        return (start + part) % 12

    @staticmethod
    def _compute_dasamsa_sign(longitude: float) -> int:
        """D10 Dasamsha: 10 parts of 3° each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 3.0)
        if part > 9:
            part = 9
        if sign % 2 == 0:
            return (sign + part) % 12
        else:
            return (sign + 8 + part) % 12

    @staticmethod
    def _compute_rudramsa_sign(longitude: float) -> int:
        """D11 Rudramsa: 11 parts of 2°43'38\" each."""
        deg = longitude % 30
        part = int(deg / (30.0 / 11.0))
        if part > 10:
            part = 10
        # Starts from Aries for all signs
        return part % 12

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
        if sign % 2 == 0:
            return (Sign.LEO.value + part) % 12
        else:
            return (Sign.CANCER.value + part) % 12

    @staticmethod
    def _compute_bhamsa_sign(longitude: float) -> int:
        """D27 Bhamsha/Nakshatramsha: 27 parts per sign."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / (30.0 / 27))
        if part > 26:
            part = 26
        element = sign % 4
        starts = [0, 3, 6, 9]
        return (starts[element] + part) % 12

    @staticmethod
    def _compute_trimsamsa_sign(longitude: float) -> int:
        """
        D30 Trimshamsha: irregular division per BPHS.
        """
        sign = int(longitude // 30)
        deg = longitude % 30

        if sign % 2 == 0:  # Odd sign
            segments = [
                (5, Sign.ARIES.value),      # Mars
                (10, Sign.AQUARIUS.value),   # Saturn
                (18, Sign.SAGITTARIUS.value),  # Jupiter
                (25, Sign.GEMINI.value),     # Mercury
                (30, Sign.LIBRA.value),      # Venus
            ]
        else:  # Even sign
            segments = [
                (5, Sign.LIBRA.value),       # Venus
                (12, Sign.GEMINI.value),     # Mercury
                (20, Sign.SAGITTARIUS.value),  # Jupiter
                (25, Sign.AQUARIUS.value),   # Saturn
                (30, Sign.ARIES.value),      # Mars
            ]

        for boundary, result_sign in segments:
            if deg < boundary:
                return result_sign
        return segments[-1][1]

    @staticmethod
    def _compute_khavedamsa_sign(longitude: float) -> int:
        """D40 Khavedamsha: 40 parts of 0°45' each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 0.75)
        if part > 39:
            part = 39

        start = Sign.ARIES.value if sign % 2 == 0 else Sign.LIBRA.value
        return (start + part) % 12

    @staticmethod
    def _compute_akshavedamsa_sign(longitude: float) -> int:
        """D45 Akshavedamsha: 45 parts of 0°40' each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / (30.0 / 45.0))
        if part > 44:
            part = 44

        modality = sign % 3  # Movable, Fixed, Dual
        starts = [Sign.ARIES.value, Sign.LEO.value, Sign.SAGITTARIUS.value]
        return (starts[modality] + part) % 12

    @staticmethod
    def _compute_shashtiamsa_sign(longitude: float) -> int:
        """D60 Shashtiamsha: 60 parts of 0°30' each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 0.5)
        if part > 59:
            part = 59
        return (sign + part) % 12

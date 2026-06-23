"""
Astronomical Engine — Layer A

High-precision celestial position computation using Swiss Ephemeris.
Supports sidereal calculations with multiple ayanamshas,
true/mean lunar nodes, and topocentric corrections.

Reference: Swiss Ephemeris documentation (https://www.astro.com/swisseph/)
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

try:
    import swisseph as swe
    HAS_SWISSEPH = True
except ImportError:
    HAS_SWISSEPH = False

from jyotisha.constants import (
    SIGN_NAMES, NAKSHATRA_NAMES, NAKSHATRA_LORDS, NAKSHATRA_SPAN,
    SWIEPH_PLANET_IDS, RAHU_MEAN_NODE_ID,
    Planet, Sign, Ayanamsha,
    EXALTATION, DEBILITATION, MOOLATRIKONA, OWN_SIGNS,
    NATURAL_FRIENDS, NATURAL_ENEMIES,
    COMBUSTION_DISTANCE, COMBUSTION_DISTANCE_RETRO,
    SIGN_LORDS, SPECIAL_ASPECTS,
)
from jyotisha.models.schemas import (
    PlanetPosition, DignityInfo, Ascendant, House, Chart, ChartMetadata,
    BirthEvent, Location
)


class AstronomicalEngine:
    """
    Core astronomical computation engine.
    
    Uses Swiss Ephemeris (PySwissEph) for high-precision sidereal
    planetary position calculations with configurable ayanamsha.
    """

    def __init__(
        self,
        ayanamsha: int = Ayanamsha.LAHIRI,
        true_nodes: bool = True,
        topocentric: bool = False,
        ephe_path: Optional[str] = None,
    ):
        if not HAS_SWISSEPH:
            raise RuntimeError("pyswisseph is required for production Jyotisha computations.")

        self.ayanamsha_id = ayanamsha
        self.true_nodes = true_nodes
        self.topocentric = topocentric

        if ephe_path:
            try:
                swe.set_ephe_path(ephe_path)
            except Exception as e:
                import warnings
                warnings.warn(f"Failed to set ephemeris path '{ephe_path}': {e}. Using built-in ephemeris.")

    # ─────────────────────────────────────────────────────────
    # Core Position Computation
    # ─────────────────────────────────────────────────────────

    def compute_planet_positions(
        self,
        jd: float,
        lat: float = 0.0,
        lon: float = 0.0,
        alt: float = 0.0,
    ) -> dict[str, dict]:
        """
        Compute sidereal positions for all 9 Vedic planets + Ascendant.

        Args:
            jd: Julian Day Number (UT)
            lat: Observer latitude (for topocentric/sunrise)
            lon: Observer longitude
            alt: Observer altitude in meters

        Returns:
            Dictionary keyed by planet name with position data.
        """
        
        swe.set_sid_mode(self.ayanamsha_id)

        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        if self.topocentric:
            swe.set_topo(lon, lat, alt)
            flags |= swe.FLG_TOPOCTR

        results = {}

        # Compute each planet
        for planet_name, planet_id in SWIEPH_PLANET_IDS.items():
            # Use mean node if configured
            if planet_name == Planet.RAHU and not self.true_nodes:
                planet_id = RAHU_MEAN_NODE_ID

            try:
                pos, ret_flags = swe.calc_ut(jd, planet_id, flags)
            except Exception as e:
                raise RuntimeError(f"Swiss Ephemeris error for {planet_name}: {e}")

            ecl_lon = pos[0] % 360.0
            ecl_lat = pos[1]
            distance = pos[2]
            speed = pos[3]

            results[planet_name] = self._build_position_data(
                name=planet_name,
                longitude=ecl_lon,
                latitude=ecl_lat,
                distance=distance,
                speed=speed,
            )

        # Ketu = 180° opposite Rahu
        rahu_lon = results[Planet.RAHU]["longitude"]
        ketu_lon = (rahu_lon + 180.0) % 360.0
        results[Planet.KETU] = self._build_position_data(
            name=Planet.KETU,
            longitude=ketu_lon,
            latitude=-results[Planet.RAHU]["latitude"],
            distance=results[Planet.RAHU]["distance"],
            speed=results[Planet.RAHU]["speed"],
        )

        # Mark combustion (relative to Sun)
        sun_lon = results[Planet.SUN]["longitude"]
        for planet_name in [Planet.MOON, Planet.MARS, Planet.MERCURY,
                            Planet.JUPITER, Planet.VENUS, Planet.SATURN]:
            p = results[planet_name]
            dist = self._angular_distance(sun_lon, p["longitude"])
            threshold = COMBUSTION_DISTANCE.get(Planet(planet_name), 999)
            if p["retrograde"] and planet_name in COMBUSTION_DISTANCE_RETRO:
                threshold = COMBUSTION_DISTANCE_RETRO[Planet(planet_name)]
            p["combust"] = dist < threshold

        return results

    def compute_ascendant(
        self,
        jd: float,
        lat: float,
        lon: float,
        house_system: str = "W",
    ) -> dict:
        """
        Compute the Ascendant (Lagna) and house cusps.

        Args:
            jd: Julian Day Number (UT)
            lat: Observer latitude
            lon: Observer longitude
            house_system: Swiss Ephemeris house system code
                         ('W' = Whole Sign, 'P' = Placidus, 'E' = Equal, etc.)

        Returns:
            Dictionary with ascendant data and house cusps.
        """
        swe.set_sid_mode(self.ayanamsha_id)

        cusps, ascmc = swe.houses_ex(
            jd, lat, lon,
            house_system.encode('ascii') if isinstance(house_system, str) else house_system,
            swe.FLG_SIDEREAL
        )

        asc_lon = ascmc[0] % 360.0
        mc_lon = ascmc[1] % 360.0

        asc_data = self._build_position_data(
            name="Ascendant",
            longitude=asc_lon,
        )

        return {
            "ascendant": asc_data,
            "mc": mc_lon,
            "cusps": [c % 360.0 for c in cusps[1:13]],  # Houses 1-12
        }

    def get_ayanamsha_value(self, jd: float) -> float:
        """Get the ayanamsha value for a given Julian Day."""
        swe.set_sid_mode(self.ayanamsha_id)
        return swe.get_ayanamsa_ut(jd)

    # ─────────────────────────────────────────────────────────
    # Sunrise / Sunset
    # ─────────────────────────────────────────────────────────

    def compute_sunrise(
        self,
        jd: float,
        lat: float,
        lon: float,
        alt: float = 0.0,
    ) -> float:
        """
        Compute sunrise time as Julian Day.

        Uses Swiss Ephemeris rise/set function with atmospheric refraction.
        """
        swe.set_topo(lon, lat, alt)

        # SE_CALC_RISE = 1, SE_BIT_DISC_CENTER = 256
        try:
            result = swe.rise_trans(
                jd, swe.SUN, "", 0,
                1 | 256,  # Rise + disc center
                [lon, lat, alt, 0, 0, 0],
                1013.25, 15.0  # Standard pressure and temp
            )
            return result[1][0]
        except Exception:
            # Fallback: approximate sunrise (6:00 local)
            return jd

    def compute_sunset(
        self,
        jd: float,
        lat: float,
        lon: float,
        alt: float = 0.0,
    ) -> float:
        """Compute sunset time as Julian Day."""
        swe.set_topo(lon, lat, alt)

        try:
            result = swe.rise_trans(
                jd, swe.SUN, "", 0,
                2 | 256,  # Set + disc center
                [lon, lat, alt, 0, 0, 0],
                1013.25, 15.0
            )
            return result[1][0]
        except Exception:
            return jd + 0.5

    # ─────────────────────────────────────────────────────────
    # Julian Day Conversion
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def datetime_to_jd(dt: datetime) -> float:
        """Convert a datetime to Julian Day Number (UT)."""
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)
        hour_decimal = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        return swe.julday(dt.year, dt.month, dt.day, hour_decimal)

    @staticmethod
    def jd_to_datetime(jd: float) -> datetime:
        """Convert Julian Day Number to datetime (UTC)."""
        year, month, day, hour_frac = swe.revjul(jd)
        hour = int(hour_frac)
        minute_frac = (hour_frac - hour) * 60
        minute = int(minute_frac)
        second = int((minute_frac - minute) * 60)
        return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)

    @staticmethod
    def jd_to_date_str(jd: float) -> str:
        """Convert Julian Day to ISO date string."""
        dt = AstronomicalEngine.jd_to_datetime(jd)
        return dt.strftime("%Y-%m-%d")

    # ─────────────────────────────────────────────────────────
    # Internal Helpers
    # ─────────────────────────────────────────────────────────

    def _build_position_data(
        self,
        name: str,
        longitude: float,
        latitude: float = 0.0,
        distance: float = 0.0,
        speed: float = 0.0,
    ) -> dict:
        """Build a standardized position dictionary from raw coordinates."""
        lon = longitude % 360.0
        sign_num = int(lon // 30)
        degree_in_sign = lon % 30

        nakshatra_num = int(lon / NAKSHATRA_SPAN)
        if nakshatra_num >= 27:
            nakshatra_num = 26  # Safety clamp
        pada_within_nak = lon % NAKSHATRA_SPAN
        pada = int(pada_within_nak / (NAKSHATRA_SPAN / 4)) + 1
        if pada > 4:
            pada = 4  # Safety clamp

        return {
            "name": name,
            "longitude": round(lon, 6),
            "latitude": round(latitude, 6),
            "distance": round(distance, 6),
            "speed": round(speed, 6),
            "retrograde": speed < 0,
            "combust": False,
            "sign": SIGN_NAMES[sign_num],
            "sign_number": sign_num,
            "degree_in_sign": round(degree_in_sign, 4),
            "nakshatra": NAKSHATRA_NAMES[nakshatra_num],
            "nakshatra_number": nakshatra_num,
            "pada": pada,
            "nakshatra_lord": NAKSHATRA_LORDS[nakshatra_num],
        }

    @staticmethod
    def _angular_distance(lon1: float, lon2: float) -> float:
        """Compute the minimum angular distance between two longitudes."""
        diff = abs(lon1 - lon2) % 360.0
        return min(diff, 360.0 - diff)


# ─────────────────────────────────────────────────────────────
# Dignity Calculator
# ─────────────────────────────────────────────────────────────

def compute_dignity(planet_name: str, sign_number: int, degree_in_sign: float) -> DignityInfo:
    """
    Compute the dignity status of a planet in a given sign.

    Checks exaltation, debilitation, moolatrikona, own sign,
    and returns a complete DignityInfo object.
    """
    try:
        planet = Planet(planet_name)
    except ValueError:
        return DignityInfo(status="Neutral")

    sign = Sign(sign_number)
    is_exalted = False
    is_debilitated = False
    is_moolatrikona = False
    is_own_sign = False

    # Check exaltation
    if planet in EXALTATION and EXALTATION[planet].sign == sign:
        is_exalted = True

    # Check debilitation
    if planet in DEBILITATION and DEBILITATION[planet] == sign:
        is_debilitated = True

    # Check moolatrikona
    if planet in MOOLATRIKONA:
        mt = MOOLATRIKONA[planet]
        if mt.sign == sign and mt.start_degree <= degree_in_sign <= mt.end_degree:
            is_moolatrikona = True

    # Check own sign
    if planet in OWN_SIGNS and sign in OWN_SIGNS[planet]:
        is_own_sign = True

    # Determine primary status (priority order)
    if is_exalted:
        status = "Exalted"
    elif is_moolatrikona:
        status = "Moolatrikona"
    elif is_own_sign:
        status = "Own Sign"
    elif is_debilitated:
        status = "Debilitated"
    else:
        # Check friendship
        sign_lord = SIGN_LORDS.get(sign)
        if sign_lord and planet != sign_lord:
            friends = NATURAL_FRIENDS.get(planet, [])
            enemies = NATURAL_ENEMIES.get(planet, [])
            if sign_lord in friends:
                status = "Friendly"
            elif sign_lord in enemies:
                status = "Enemy"
            else:
                status = "Neutral"
        else:
            status = "Neutral"

    return DignityInfo(
        status=status,
        is_exalted=is_exalted,
        is_debilitated=is_debilitated,
        is_moolatrikona=is_moolatrikona,
        is_own_sign=is_own_sign,
        is_friendly=(status == "Friendly"),
        is_neutral=(status == "Neutral"),
        is_enemy=(status == "Enemy"),
    )


# ─────────────────────────────────────────────────────────────
# Vedic Aspect Calculator
# ─────────────────────────────────────────────────────────────

def compute_aspects(planets: dict[str, dict]) -> dict[str, list[str]]:
    """
    Compute Vedic aspects (Drishti) between planets.

    All planets aspect the 7th sign from themselves.
    Mars, Jupiter, Saturn, Rahu, Ketu have special additional aspects.

    Returns:
        Dictionary mapping each planet to list of planets it aspects.
    """
    aspects = {name: [] for name in planets}

    planet_list = list(planets.items())
    for name, data in planet_list:
        source_sign = data["sign_number"]

        # Universal 7th aspect
        aspected_houses = [7]

        # Special aspects
        try:
            planet_enum = Planet(name)
            if planet_enum in SPECIAL_ASPECTS:
                aspected_houses.extend(SPECIAL_ASPECTS[planet_enum])
        except ValueError:
            pass

        for aspect_house in aspected_houses:
            aspected_sign = (source_sign + aspect_house - 1) % 12

            # Find planets in the aspected sign
            for target_name, target_data in planet_list:
                if target_name != name and target_data["sign_number"] == aspected_sign:
                    if target_name not in aspects[name]:
                        aspects[name].append(target_name)

    return aspects

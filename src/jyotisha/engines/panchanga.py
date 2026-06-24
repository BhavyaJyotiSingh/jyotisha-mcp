"""
Daily Panchanga Engine — Layer J

Computes the five key daily elements (Tithi, Vara, Nakshatra, Yoga, Karana)
along with sunrise, sunset, and precise start/end boundary times.
Also rates each element for quality and applicable activities for Muhurta.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional

from jyotisha.constants import (
    NAKSHATRA_SPAN, NAKSHATRA_NAMES, TITHI_NAMES, WEEKDAY_NAMES,
    WEEKDAY_LORDS, YOGA_NAMES, KARANA_NAMES,
)
from jyotisha.models.schemas import Panchanga, PanchangaElement, Location
from jyotisha.engines.astronomy import AstronomicalEngine


class PanchangaEngine:
    """
    Computes daily Panchanga elements for a specific time and location,
    calculating precise boundaries and Muhurta qualities.
    """

    def __init__(self, astro_engine: Optional[AstronomicalEngine] = None):
        self.astro = astro_engine or AstronomicalEngine()

    def _find_element_boundaries(
        self,
        jd: float,
        lat: float,
        lon: float,
        alt: float,
        element_type: str,
        current_idx: int,
    ) -> tuple[float, float]:
        """
        Find the start and end Julian Days of the current Panchanga element.
        """
        def get_idx(t_jd: float) -> int:
            pos = self.astro.compute_planet_positions(t_jd, lat, lon, alt)
            s_lon = pos["Sun"]["longitude"]
            m_lon = pos["Moon"]["longitude"]
            if element_type == "tithi":
                diff = (m_lon - s_lon) % 360.0
                val = int(diff // 12.0)
                return 29 if val >= 30 else val
            elif element_type == "nakshatra":
                val = int(m_lon // NAKSHATRA_SPAN)
                return 26 if val >= 27 else val
            elif element_type == "yoga":
                y_sum = (s_lon + m_lon) % 360.0
                val = int(y_sum // NAKSHATRA_SPAN)
                return 26 if val >= 27 else val
            elif element_type == "karana":
                diff = (m_lon - s_lon) % 360.0
                val = int(diff // 6.0)
                return 59 if val >= 60 else val
            return 0

        # Step backward to find start
        step = 0.04  # ~1 hour
        start_jd = jd
        max_steps = 40  # ~40 hours max
        jd_curr = jd
        for _ in range(max_steps):
            jd_prev = jd_curr - step
            if get_idx(jd_prev) != current_idx:
                # Bracket found: [jd_prev, jd_curr]
                low = jd_prev
                high = jd_curr
                for _ in range(12):
                    mid = (low + high) / 2.0
                    if get_idx(mid) == current_idx:
                        high = mid
                    else:
                        low = mid
                start_jd = high
                break
            jd_curr = jd_prev
        else:
            start_jd = jd - 0.5

        # Step forward to find end
        end_jd = jd
        jd_curr = jd
        for _ in range(max_steps):
            jd_next = jd_curr + step
            if get_idx(jd_next) != current_idx:
                # Bracket found: [jd_curr, jd_next]
                low = jd_curr
                high = jd_next
                for _ in range(12):
                    mid = (low + high) / 2.0
                    if get_idx(mid) == current_idx:
                        low = mid
                    else:
                        high = mid
                end_jd = low
                break
            jd_next = jd_next
            jd_curr = jd_next
        else:
            end_jd = jd + 0.5

        return start_jd, end_jd

    def compute_panchanga(
        self,
        jd: float,
        lat: float,
        lon: float,
        alt: float = 0.0,
        utc_offset_hours: float = 0.0,
        tz_name: Optional[str] = None,
    ) -> Panchanga:
        """
        Compute daily Panchanga for a given Julian Day and location.
        """
        # 1. Compute Sun and Moon positions
        positions = self.astro.compute_planet_positions(jd, lat, lon, alt)
        sun_lon = positions["Sun"]["longitude"]
        moon_lon = positions["Moon"]["longitude"]

        # 2. Compute sunrise & sunset
        utc_dt = AstronomicalEngine.jd_to_datetime(jd)
        local_dt = utc_dt + timedelta(hours=utc_offset_hours)
        local_midnight_dt = datetime(local_dt.year, local_dt.month, local_dt.day, 0, 0, 0)
        utc_midnight_dt = local_midnight_dt - timedelta(hours=utc_offset_hours)
        midnight_jd = AstronomicalEngine.datetime_to_jd(utc_midnight_dt)

        sunrise_jd = self.astro.compute_sunrise(midnight_jd, lat, lon, alt)
        sunset_jd = self.astro.compute_sunset(midnight_jd, lat, lon, alt)

        # 3. Vara (Vedic weekday starting at sunrise)
        base_weekday = local_dt.weekday()  # Monday=0, Sunday=6
        if jd < sunrise_jd:
            base_weekday = (base_weekday - 1) % 7

        vara_name = WEEKDAY_NAMES[base_weekday]
        vara_lord = WEEKDAY_LORDS[vara_name].value

        # 4. Tithi (Moon - Sun difference in 12° intervals)
        diff = (moon_lon - sun_lon) % 360.0
        tithi_number = int(diff // 12.0) + 1
        if tithi_number > 30:
            tithi_number = 30
        tithi_name = TITHI_NAMES[tithi_number - 1]
        paksha = "Shukla" if tithi_number <= 15 else "Krishna"

        # 5. Nakshatra (Moon position in 13°20' intervals)
        nak_number = int(moon_lon // NAKSHATRA_SPAN)
        if nak_number >= 27:
            nak_number = 26
        nak_name = NAKSHATRA_NAMES[nak_number]

        # 6. Yoga (Sun + Moon position in 13°20' intervals)
        yoga_sum = (sun_lon + moon_lon) % 360.0
        yoga_number = int(yoga_sum // NAKSHATRA_SPAN)
        if yoga_number >= 27:
            yoga_number = 26
        yoga_name = YOGA_NAMES[yoga_number]

        # 7. Karana (Half-tithi, 6° intervals)
        karana_idx = int(diff // 6.0)
        if karana_idx == 0:
            karana_name = "Kimstughna"
            karana_num = 11
        elif karana_idx == 59:
            karana_name = "Naga"
            karana_num = 10
        elif karana_idx == 58:
            karana_name = "Chatushpada"
            karana_num = 9
        elif karana_idx == 57:
            karana_name = "Shakuni"
            karana_num = 8
        else:
            cycle_idx = (karana_idx - 1) % 7
            karana_name = KARANA_NAMES[cycle_idx]
            karana_num = cycle_idx + 1

        # Format sunrise/sunset as ISO strings
        sunrise_dt = AstronomicalEngine.jd_to_datetime(sunrise_jd) + timedelta(hours=utc_offset_hours)
        sunset_dt = AstronomicalEngine.jd_to_datetime(sunset_jd) + timedelta(hours=utc_offset_hours)

        # 8. Boundary Calculations
        t_start_jd, t_end_jd = self._find_element_boundaries(jd, lat, lon, alt, "tithi", tithi_number - 1)
        n_start_jd, n_end_jd = self._find_element_boundaries(jd, lat, lon, alt, "nakshatra", nak_number)
        y_start_jd, y_end_jd = self._find_element_boundaries(jd, lat, lon, alt, "yoga", yoga_number)
        k_start_jd, k_end_jd = self._find_element_boundaries(jd, lat, lon, alt, "karana", karana_idx)

        def jd_to_local_time_str(jd_val: float) -> str:
            dt = AstronomicalEngine.jd_to_datetime(jd_val) + timedelta(hours=utc_offset_hours)
            return dt.strftime("%H:%M:%S")

        # 9. Quality and Activity Mappings
        TITHI_INFO = {
            1: ("Neutral", ["Fasting", "Simple beginnings"]),
            2: ("Good", ["Marriage", "Construction", "Buying property"]),
            3: ("Good", ["Marriage", "Education", "New journeys"]),
            4: ("Bad", ["Combat", "Clearing debts", "Destroying obstacles"]),
            5: ("Good", ["Auspicious starts", "Worship", "Administering medicine"]),
            6: ("Good", ["New clothes", "Coronation", "Travel"]),
            7: ("Good", ["Buying vehicles", "Journeys", "Business starts"]),
            8: ("Good", ["Religious rites", "Physical exercise"]),
            9: ("Bad", ["Courts and litigation", "Combat", "Competition"]),
            10: ("Good", ["Marriage", "House entering", "Business deals"]),
            11: ("Good", ["Fasting (Ekadashi)", "Spiritual reflection", "Charity"]),
            12: ("Good", ["Worship", "Public speeches", "Social events"]),
            13: ("Good", ["Romance", "Purchasing jewelry", "Friendship"]),
            14: ("Bad", ["Combat", "Spiritual retreats"]),
            15: ("Good", ["Purnima - All auspicious undertakings", "Charity", "Celebration"]),
            16: ("Neutral", ["Fasting", "Routine work"]),
            17: ("Good", ["Social work", "Marriage", "Friendship"]),
            18: ("Good", ["Artistic studies", "Journeys"]),
            19: ("Bad", ["Combat", "Clearing debts"]),
            20: ("Good", ["Spiritual work", "Charity"]),
            21: ("Good", ["Gardening", "Worship"]),
            22: ("Good", ["Buying property", "Education"]),
            23: ("Good", ["Worship", "Quiet study"]),
            24: ("Bad", ["Litigation", "Combat"]),
            25: ("Good", ["Marriage", "New deals"]),
            26: ("Good", ["Fasting (Ekadashi)", "Charity"]),
            27: ("Good", ["Spiritual study", "Reflection"]),
            28: ("Good", ["Worship", "Family gatherings"]),
            29: ("Bad", ["Combat", "Clearing debts"]),
            30: ("Bad", ["Amavasya - Ancestral rites", "Meditation", "Avoid new beginnings"]),
        }

        NAKSHATRA_INFO = {
            1: ("Good", ["Medicine", "Travel", "Starting education"]),
            2: ("Bad", ["Demolition", "Litigation", "Physical combat"]),
            3: ("Neutral", ["Fire sacrifices", "Cooking", "Metals"]),
            4: ("Good", ["Laying foundation", "Agriculture", "Marriage"]),
            5: ("Good", ["Romance", "Fine arts", "Music", "Journeys"]),
            6: ("Bad", ["Spells", "Confrontations", "Renovation"]),
            7: ("Good", ["Travel", "Buying vehicles", "Starting business"]),
            8: ("Good", ["Pushya - All auspicious starts", "Buying assets", "Medicine"]),
            9: ("Bad", ["Worship of fierce deities", "Combat"]),
            10: ("Bad", ["Ancestral worship", "Worship of ancestors"]),
            11: ("Bad", ["Combat", "Physical labor", "Demolition"]),
            12: ("Good", ["Marriage", "Taking oath", "Long-term decisions"]),
            13: ("Good", ["Art", "Business", "Short travel", "Crafts"]),
            14: ("Good", ["Design", "Wearing new clothes", "Romance"]),
            15: ("Good", ["Buying vehicles", "Travel", "Sowing seeds"]),
            16: ("Neutral", ["Worship", "Debate", "Routine work"]),
            17: ("Good", ["Marriage", "Travel", "Friendship", "Worship"]),
            18: ("Bad", ["Combat", "Litigation", "Fierce acts"]),
            19: ("Bad", ["Gardening", "Deep study", "Litigation"]),
            20: ("Bad", ["Worship of water deities", "Combat", "Fasting"]),
            21: ("Good", ["Laying foundation", "Long-term business"]),
            22: ("Good", ["Education", "Journeys", "Installing deities"]),
            23: ("Good", ["Music", "Installing machinery", "Travel"]),
            24: ("Good", ["Medicine", "Journeys", "Contracts"]),
            25: ("Bad", ["Spiritual reflection", "Physical combat"]),
            26: ("Good", ["Marriage", "Long-term investments", "Construction"]),
            27: ("Good", ["Romance", "Wear new clothes", "Journeys", "Art"]),
        }

        YOGA_INFO = {
            1: ("Bad", ["Fierce activities"]),
            2: ("Good", ["Friendship", "Peace-making"]),
            3: ("Good", ["Longevity rites", "Long-term work"]),
            4: ("Good", ["Socializing", "Auspicious work"]),
            5: ("Good", ["Charity", "Decoration"]),
            6: ("Bad", ["Avoid auspicious work"]),
            7: ("Good", ["Travel", "Buying vehicles"]),
            8: ("Good", ["Worship", "Public speeches"]),
            9: ("Bad", ["Avoid auspicious starts"]),
            10: ("Good", ["Settling differences"]),
            11: ("Bad", ["Avoid travel or partnerships"]),
            12: ("Good", ["Long-term projects"]),
            13: ("Bad", ["Combat", "Competition"]),
            14: ("Good", ["Marriage", "Signing contracts"]),
            15: ("Bad", ["Avoid financial transactions"]),
            16: ("Good", ["Social undertakings"]),
            17: ("Bad", ["Avoid all auspicious activities"]),
            18: ("Good", ["Prosperity undertakings"]),
            19: ("Bad", ["Avoid beginning travel"]),
            20: ("Good", ["Installing deities", "Worship"]),
            21: ("Good", ["Religious rites", "Peaceful work"]),
            22: ("Good", ["Long journeys", "Study"]),
            23: ("Good", ["Auspicious starts", "Marriage"]),
            24: ("Good", ["Charity", "Worship"]),
            25: ("Good", ["Cleanliness", "Routine tasks"]),
            26: ("Good", ["Leadership", "Taking oath"]),
            27: ("Bad", ["Avoid all new activities"]),
        }

        KARANA_INFO = {
            1: ("Good", ["Agriculture", "Construction", "Permanent starts"]),
            2: ("Good", ["Charity", "Religious work", "Study"]),
            3: ("Good", ["Romance", "Socializing", "Treaties"]),
            4: ("Good", ["Public events", "Gardening", "Construction"]),
            5: ("Good", ["Buying land", "Agriculture", "Repairs"]),
            6: ("Good", ["Business transactions", "Trade", "Selling"]),
            7: ("Bad", ["Vishti (Bhadra) - Avoid all auspicious starts", "Combat", "Destruction"]),
            8: ("Neutral", ["Ancestral rites", "Medicine", "Worship"]),
            9: ("Neutral", ["Charity", "Spiritual guidance", "Worship"]),
            10: ("Neutral", ["Combat", "Litigation", "Worship of fierce deities"]),
            11: ("Good", ["Kimstughna - All auspicious actions", "Education", "Marriage"]),
        }

        t_qual, t_act = TITHI_INFO.get(tithi_number, ("Neutral", []))
        n_qual, n_act = NAKSHATRA_INFO.get(nak_number + 1, ("Neutral", []))
        y_qual, y_act = YOGA_INFO.get(yoga_number + 1, ("Neutral", []))
        k_qual, k_act = KARANA_INFO.get(karana_num, ("Neutral", []))

        return Panchanga(
            date=local_dt.strftime("%Y-%m-%d"),
            location=Location(
                latitude=lat,
                longitude=lon,
                altitude=alt,
                timezone=tz_name,
            ),
            tithi=PanchangaElement(
                number=tithi_number,
                name=tithi_name,
                start_time=jd_to_local_time_str(t_start_jd),
                end_time=jd_to_local_time_str(t_end_jd),
                quality=t_qual,
                applicable_activities=t_act
            ),
            paksha=paksha,
            vara=vara_name,
            vara_lord=vara_lord,
            nakshatra=PanchangaElement(
                number=nak_number + 1,
                name=nak_name,
                start_time=jd_to_local_time_str(n_start_jd),
                end_time=jd_to_local_time_str(n_end_jd),
                quality=n_qual,
                applicable_activities=n_act
            ),
            yoga=PanchangaElement(
                number=yoga_number + 1,
                name=yoga_name,
                start_time=jd_to_local_time_str(y_start_jd),
                end_time=jd_to_local_time_str(y_end_jd),
                quality=y_qual,
                applicable_activities=y_act
            ),
            karana=PanchangaElement(
                number=karana_num,
                name=karana_name,
                start_time=jd_to_local_time_str(k_start_jd),
                end_time=jd_to_local_time_str(k_end_jd),
                quality=k_qual,
                applicable_activities=k_act
            ),
            sunrise=sunrise_dt.strftime("%H:%M:%S"),
            sunset=sunset_dt.strftime("%H:%M:%S"),
        )

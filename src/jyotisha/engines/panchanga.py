"""
Daily Panchanga Engine — Layer J

Computes the five key daily elements (Tithi, Vara, Nakshatra, Yoga, Karana)
along with sunrise and sunset timings.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional

from jyotisha.constants import (
    NAKSHATRA_SPAN, NAKSHATRA_NAMES, TITHI_NAMES, WEEKDAY_NAMES,
    WEEKDAY_LORDS, YOGA_NAMES, KARANA_NAMES, Planet,
)
from jyotisha.models.schemas import Panchanga, PanchangaElement, Location
from jyotisha.engines.astronomy import AstronomicalEngine


class PanchangaEngine:
    """
    Computes daily Panchanga elements for a specific time and location.
    """

    def __init__(self, astro_engine: Optional[AstronomicalEngine] = None):
        self.astro = astro_engine or AstronomicalEngine()

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
        # Use Julian Day at midnight local to find correct sunrise/sunset of that day
        utc_dt = AstronomicalEngine.jd_to_datetime(jd)
        local_dt = utc_dt + timedelta(hours=utc_offset_hours)
        local_midnight_dt = datetime(local_dt.year, local_dt.month, local_dt.day, 0, 0, 0)
        utc_midnight_dt = local_midnight_dt - timedelta(hours=utc_offset_hours)
        midnight_jd = AstronomicalEngine.datetime_to_jd(utc_midnight_dt)

        sunrise_jd = self.astro.compute_sunrise(midnight_jd, lat, lon, alt)
        sunset_jd = self.astro.compute_sunset(midnight_jd, lat, lon, alt)

        # 3. Vara (Vedic weekday starting at sunrise)
        base_weekday = local_dt.weekday()  # Monday=0, Sunday=6
        
        # If birth is before sunrise of that day, it belongs to the previous Vedic weekday
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
        
        # Determine Karana name and number (1-indexed sequence)
        if karana_idx == 0:
            # First half of Shukla Pratipada: Kimstughna
            karana_name = "Kimstughna"
            karana_num = 11
        elif karana_idx == 59:
            # Second half of Krishna Chaturdashi: Naga
            karana_name = "Naga"
            karana_num = 10
        elif karana_idx == 58:
            # First half of Krishna Chaturdashi: Chatushpada
            karana_name = "Chatushpada"
            karana_num = 9
        elif karana_idx == 57:
            # Second half of Krishna Trayodashi: Shakuni
            karana_name = "Shakuni"
            karana_num = 8
        else:
            # Movable Karanas repeating 8 times
            cycle_idx = (karana_idx - 1) % 7
            karana_name = KARANA_NAMES[cycle_idx]
            karana_num = cycle_idx + 1

        # Format sunrise/sunset as ISO strings
        sunrise_dt = AstronomicalEngine.jd_to_datetime(sunrise_jd) + timedelta(hours=utc_offset_hours)
        sunset_dt = AstronomicalEngine.jd_to_datetime(sunset_jd) + timedelta(hours=utc_offset_hours)

        return Panchanga(
            date=local_dt.strftime("%Y-%m-%d"),
            location=Location(
                latitude=lat,
                longitude=lon,
                altitude=alt,
                timezone=tz_name,
            ),
            tithi=PanchangaElement(number=tithi_number, name=tithi_name),
            paksha=paksha,
            vara=vara_name,
            vara_lord=vara_lord,
            nakshatra=PanchangaElement(number=nak_number + 1, name=nak_name),
            yoga=PanchangaElement(number=yoga_number + 1, name=yoga_name),
            karana=PanchangaElement(number=karana_num, name=karana_name),
            sunrise=sunrise_dt.strftime("%H:%M:%S"),
            sunset=sunset_dt.strftime("%H:%M:%S"),
        )

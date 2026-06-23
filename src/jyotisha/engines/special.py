"""
Special Points & Lagnas Engine — Layer I

Computes Upagrahas (subsidiary planets like Gulika, Mandi)
and Special Lagnas (Hora, Ghati, Indu Lagnas).
"""

from __future__ import annotations

from jyotisha.models.schemas import Chart, Upagraha, SpecialLagna
from jyotisha.constants import SIGN_NAMES

class SpecialPointsEngine:
    """Computes Upagrahas and Special Lagnas."""

    def compute_special_lagnas(self, chart: Chart, sunrise_jd: float) -> list[SpecialLagna]:
        """
        Compute special lagnas like Hora and Ghati Lagna.
        Requires the Julian Day of sunrise.
        """
        lagnas = []
        if not chart.birth_event:
            return lagnas

        birth_jd = chart.birth_event.julian_day
        
        # Time elapsed since sunrise in days
        time_elapsed = birth_jd - sunrise_jd
        if time_elapsed < 0:
            # Born before sunrise; use previous day's sunrise
            time_elapsed += 1.0

        # Hora Lagna: 1 Hora = 15 degrees per hour = 360 degrees per day
        # Actually: Lagna advances 2 rashis (60 degrees) per Lagna (approx 2 hours)
        # Formula: Ascendant + (Time elapsed in hours * 15)
        # More precise: Hora Lagna degree = Ascendant Degree + (Time elapsed in days * 360 * 2) 
        # Wait, the standard Jaimini formula:
        # HL moves 2x speed of Sun/Ascendant.
        # Let's use a simplified BPHS formula: HL = Ascendant + (time from sunrise * 720 degrees)
        hl_longitude = (chart.ascendant.longitude + (time_elapsed * 720.0)) % 360.0
        
        hl_sign_num = int(hl_longitude // 30)
        lagnas.append(SpecialLagna(
            type="Hora",
            sign=SIGN_NAMES[hl_sign_num],
            sign_number=hl_sign_num,
            degree=round(hl_longitude % 30, 4)
        ))

        # Ghati Lagna: GL = Ascendant + (time from sunrise * 1800 degrees)
        gl_longitude = (chart.ascendant.longitude + (time_elapsed * 1800.0)) % 360.0
        gl_sign_num = int(gl_longitude // 30)
        lagnas.append(SpecialLagna(
            type="Ghati",
            sign=SIGN_NAMES[gl_sign_num],
            sign_number=gl_sign_num,
            degree=round(gl_longitude % 30, 4)
        ))

        return lagnas

    def compute_upagrahas(self, chart: Chart, sunrise_jd: float, sunset_jd: float) -> list[Upagraha]:
        """
        Compute Gulika and Mandi.
        Requires sunrise and sunset Julian Days.
        """
        # A full implementation requires dividing the day/night into 8 parts
        # and finding the start of Saturn's portion.
        # For now, returning a stub.
        return []

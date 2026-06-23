"""
Calendar & Location Normalization Engine — Layer B

Normalizes birth/date inputs to standard UTC with verified coordinates.
Handles historical timezone/DST, Julian/Gregorian calendar conversion,
and unknown birth time proxies.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

try:
    from timezonefinder import TimezoneFinder
    import pytz
    HAS_TZ_LIBS = True
except ImportError:
    HAS_TZ_LIBS = False

try:
    import swisseph as swe
    HAS_SWISSEPH = True
except ImportError:
    HAS_SWISSEPH = False

from jyotisha.models.schemas import BirthEvent, Location


# Singleton TimezoneFinder (expensive to init)
_tz_finder: Optional[TimezoneFinder] = None

def _get_tz_finder() -> TimezoneFinder:
    global _tz_finder
    if _tz_finder is None:
        _tz_finder = TimezoneFinder()
    return _tz_finder


class CalendarEngine:
    """
    Normalizes birth event inputs into standardized UTC + Julian Day format.

    Handles:
    - Timezone resolution from coordinates
    - DST detection for historical dates
    - Julian calendar conversion (pre-1582)
    - Unknown birth time proxy (sunrise or noon)
    """

    def normalize_birth_event(
        self,
        date_str: str,
        time_str: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        location_name: Optional[str] = None,
        calendar: str = "Gregorian",
    ) -> BirthEvent:
        """
        Normalize a birth event to UTC with Julian Day number.

        Args:
            date_str: Date string in ISO format "YYYY-MM-DD"
            time_str: Time string in "HH:MM" or "HH:MM:SS" format, or None
            latitude: Geographic latitude (-90 to 90)
            longitude: Geographic longitude (-180 to 180)
            location_name: Optional place name (for reference only)
            calendar: "Gregorian" or "Julian"

        Returns:
            Normalized BirthEvent with UTC datetime and Julian Day.
        """
        notes = []

        # Handle missing birth time
        if time_str is None or time_str.strip() == "":
            time_str = "06:00"
            notes.append(
                "Birth time unknown; using approximate sunrise (06:00). "
                "Consider birth time rectification for accuracy."
            )

        # Require coordinates
        if latitude is None or longitude is None:
            raise ValueError(
                "Latitude and longitude are required. "
                "Please provide geographic coordinates for the birth location."
            )

        # Parse date and time
        try:
            if "T" in date_str:
                # Already combined
                local_naive = datetime.fromisoformat(date_str)
            else:
                local_naive = datetime.fromisoformat(f"{date_str}T{time_str}")
        except ValueError as e:
            raise ValueError(f"Invalid date/time format: {e}. Use YYYY-MM-DD and HH:MM.")

        # Determine timezone from coordinates
        tz_name, utc_offset, dst_active = self._resolve_timezone(
            latitude, longitude, local_naive
        )

        # Convert to UTC
        if HAS_TZ_LIBS and tz_name and local_naive.year >= 1900:
            tz = pytz.timezone(tz_name)
            try:
                local_aware = tz.localize(local_naive, is_dst=None)
            except pytz.exceptions.AmbiguousTimeError:
                local_aware = tz.localize(local_naive, is_dst=False)
                notes.append("Ambiguous DST time; assumed standard time.")
            except pytz.exceptions.NonExistentTimeError:
                local_aware = tz.localize(local_naive, is_dst=True)
                notes.append("Non-existent time due to DST transition; adjusted.")

            utc_dt = local_aware.astimezone(pytz.utc)
            utc_offset = local_aware.utcoffset().total_seconds() / 3600
            dst_active = bool(local_aware.dst())
        else:
            # Historical dates before standard time (pre-1900) or fallback
            # Use Local Mean Time (LMT) calculated directly from longitude
            # 15 degrees = 1 hour, so longitude / 15 = hours offset
            utc_offset = longitude / 15.0
            from datetime import timedelta
            utc_dt = (local_naive - timedelta(hours=utc_offset)).replace(tzinfo=timezone.utc)
            dst_active = False
            if local_naive.year < 1900:
                notes.append("Pre-1900 date detected. Enforcing strict Local Mean Time (LMT) derived from longitude.")
            else:
                notes.append("Timezone libraries unavailable; falling back to LMT based on longitude.")

        # Handle pre-Gregorian dates strictly (Before Oct 15, 1582)
        if utc_dt.year < 1582 or (utc_dt.year == 1582 and utc_dt.month < 10) or (utc_dt.year == 1582 and utc_dt.month == 10 and utc_dt.day < 15):
            if calendar == "Gregorian":
                calendar = "Julian"
                notes.append("Date before Oct 15, 1582; automatically using Julian calendar.")

        # Compute Julian Day
        jd = self._compute_julian_day(utc_dt, calendar)

        return BirthEvent(
            datetime_utc=utc_dt,
            julian_day=jd,
            location=Location(
                name=location_name,
                latitude=latitude,
                longitude=longitude,
                timezone=tz_name,
            ),
            calendar_type=calendar,
            dst_active=dst_active,
            utc_offset_hours=utc_offset,
            notes=notes,
        )

    def _resolve_timezone(
        self,
        lat: float,
        lon: float,
        dt: datetime,
    ) -> tuple[Optional[str], float, bool]:
        """
        Resolve timezone name from coordinates.

        Returns: (timezone_name, utc_offset_hours, dst_active)
        """
        if not HAS_TZ_LIBS:
            return None, 0.0, False

        tf = _get_tz_finder()
        tz_name = tf.timezone_at(lat=lat, lng=lon)

        if tz_name is None:
            # Fallback: estimate from longitude
            offset = round(lon / 15.0)
            return None, float(offset), False

        try:
            tz = pytz.timezone(tz_name)
            local = tz.localize(dt, is_dst=None)
            utc_offset = local.utcoffset().total_seconds() / 3600
            dst_active = bool(local.dst())
        except Exception:
            utc_offset = round(lon / 15.0)
            dst_active = False

        return tz_name, utc_offset, dst_active

    @staticmethod
    def _compute_julian_day(dt: datetime, calendar: str = "Gregorian") -> float:
        """Compute Julian Day Number from datetime."""
        if HAS_SWISSEPH:
            hour_decimal = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
            if calendar == "Julian":
                return swe.julday(dt.year, dt.month, dt.day, hour_decimal, swe.JUL_CAL)
            else:
                return swe.julday(dt.year, dt.month, dt.day, hour_decimal, swe.GREG_CAL)
        else:
            # Manual Julian Day computation (Meeus algorithm)
            y = dt.year
            m = dt.month
            d = dt.day + (dt.hour + dt.minute / 60.0 + dt.second / 3600.0) / 24.0

            if m <= 2:
                y -= 1
                m += 12

            if calendar == "Gregorian":
                A = int(y / 100)
                B = 2 - A + int(A / 4)
            else:
                B = 0

            return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5

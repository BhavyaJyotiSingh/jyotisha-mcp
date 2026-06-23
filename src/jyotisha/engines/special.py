"""
Special Points & Lagnas Engine — Layer I

Computes Upagrahas (subsidiary planets like Gulika, Mandi, Yamakantaka, etc.)
and Special Lagnas (Hora, Ghati, Indu, Pranapada Lagnas).
"""

from __future__ import annotations
from typing import Optional
from datetime import timedelta

from jyotisha.models.schemas import Chart, Upagraha, SpecialLagna
from jyotisha.constants import SIGN_NAMES, SIGN_LORDS, SIGN_MODALITIES, Sign, Planet
from jyotisha.engines.astronomy import AstronomicalEngine


class SpecialPointsEngine:
    """Computes Upagrahas and Special Lagnas."""

    def __init__(self, astro_engine: Optional[AstronomicalEngine] = None):
        self.astro = astro_engine or AstronomicalEngine()

    def compute_special_lagnas(self, chart: Chart, sunrise_jd: float) -> list[SpecialLagna]:
        """
        Compute special lagnas: Hora, Ghati, Indu, and Pranapada Lagna.
        """
        lagnas = []
        if not chart.birth_event:
            return lagnas

        birth_jd = chart.birth_event.julian_day
        
        # 1. Time elapsed since sunrise in days
        time_elapsed = birth_jd - sunrise_jd
        if time_elapsed < 0:
            time_elapsed += 1.0

        # Hora Lagna: HL = Ascendant + (time from sunrise * 720 degrees)
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

        # Indu Lagna (Wealth Ascendant)
        # Lord of 9th from Lagna
        lord_9_lagna = chart.get_house_lord(9)
        
        # Lord of 9th from Moon
        moon = chart.get_planet("Moon")
        if moon:
            moon_sign = moon.sign_number
            ninth_from_moon = (moon_sign + 8) % 12
            lord_9_moon = SIGN_LORDS[Sign(ninth_from_moon)].value
            
            # Rays (Kala units)
            rays = {
                "Sun": 30,
                "Moon": 16,
                "Mars": 6,
                "Mercury": 8,
                "Jupiter": 10,
                "Venus": 12,
                "Saturn": 1,
            }
            
            total_rays = rays.get(lord_9_lagna, 0) + rays.get(lord_9_moon, 0)
            rem = total_rays % 12
            if rem == 0:
                rem = 12
                
            # Count rem houses from Moon
            il_sign_num = (moon_sign + rem - 1) % 12
            lagnas.append(SpecialLagna(
                type="Indu",
                sign=SIGN_NAMES[il_sign_num],
                sign_number=il_sign_num,
                degree=round(moon.degree_in_sign, 4)  # Takes Moon's degree in sign by convention
            ))

        # Pranapada Lagna (Vitality Ascendant)
        sun = chart.get_planet("Sun")
        if sun:
            # 1 Ghati = 24 minutes, 1 Vighati = 24 seconds, so 3600 Vighatis in a day
            vighatis = time_elapsed * 3600.0
            
            # Pranapada moves 2 degrees per Vighati (7200 degrees per day)
            x_degrees = vighatis * 2.0
            
            # Modality correction of Sun's sign
            sun_modality = SIGN_MODALITIES[sun.sign_number]
            from jyotisha.constants import Modality
            if sun_modality == Modality.MOVABLE:
                offset = 0.0
            elif sun_modality == Modality.FIXED:
                offset = 240.0
            else:
                offset = 120.0
                
            pp_longitude = (sun.longitude + x_degrees + offset) % 360.0
            pp_sign_num = int(pp_longitude // 30)
            lagnas.append(SpecialLagna(
                type="Pranapada",
                sign=SIGN_NAMES[pp_sign_num],
                sign_number=pp_sign_num,
                degree=round(pp_longitude % 30, 4)
            ))

        return lagnas

    def compute_upagrahas(self, chart: Chart, sunrise_jd: float, sunset_jd: float) -> list[Upagraha]:
        """
        Compute positions of Gulika, Mandi, Yamakantaka, Mrityu, Kaala, Ardhaman,
        and Sun-derived Aprakasha Grahas: Dhuma, Vyatipata, Parivesha, Indrachapa, Upaketu.
        """
        upagrahas = []
        if not chart.birth_event:
            return upagrahas

        birth_jd = chart.birth_event.julian_day
        lat = chart.birth_event.location.latitude
        lon = chart.birth_event.location.longitude

        # 1. Determine day/night birth context
        if sunrise_jd <= birth_jd <= sunset_jd:
            is_day = True
            start_time = sunrise_jd
            duration = sunset_jd - sunrise_jd
        else:
            is_day = False
            if birth_jd < sunrise_jd:
                # Born before sunrise; previous day's sunset was approx sunset_jd - 1
                start_time = sunset_jd - 1.0
                duration = sunrise_jd - start_time
            else:
                # Born after sunset
                start_time = sunset_jd
                duration = (sunrise_jd + 1.0) - sunset_jd

        # 2. Determine Vedic weekday (Sunday=0, Monday=1, ..., Saturday=6)
        local_dt = chart.birth_event.datetime_utc + timedelta(hours=chart.birth_event.utc_offset_hours)
        base_weekday = local_dt.weekday()  # Monday=0, Sunday=6
        if birth_jd < sunrise_jd:
            base_weekday = (base_weekday - 1) % 7
        
        # Convert Monday=0 to Sunday=0, Monday=1 sequence
        vedic_weekday = (base_weekday + 1) % 7

        # segment duration (1/8 of day/night)
        segment_dur = duration / 8.0

        # Weekday lord indices for upagrahas
        upagrahas_lords = {
            "Kaala": 0,         # Sun
            "Mrityu": 2,        # Mars
            "Yamakantaka": 4,   # Jupiter
            "Ardhaman": 3,      # Mercury
            "Gulika": 6,        # Saturn
            "Mandi": 6,         # Saturn (midpoint)
        }

        # Calculate time-based upagrahas
        for name, lord in upagrahas_lords.items():
            if is_day:
                part = 1 + (lord - vedic_weekday) % 7
            else:
                # Night: starts from 5th lord (lord of weekday + 4)
                night_start_lord = (vedic_weekday + 4) % 7
                part = 1 + (lord - night_start_lord) % 7

            # Mandi is calculated at the midpoint of Saturn's part, Gulika at start
            if name == "Mandi":
                t_event = start_time + (part - 0.5) * segment_dur
            else:
                t_event = start_time + (part - 1) * segment_dur

            # Calculate Ascendant at that event time
            try:
                asc_data = self.astro.compute_ascendant(t_event, lat, lon)
                lon_val = asc_data["ascendant"]["longitude"]
                sign_num = int(lon_val // 30)
                
                upagrahas.append(Upagraha(
                    name=name,
                    sign=SIGN_NAMES[sign_num],
                    sign_number=sign_num,
                    degree=round(lon_val % 30, 4)
                ))
            except Exception:
                pass

        # 3. Calculate Sun-derived Aprakasha Grahas
        sun = chart.get_planet("Sun")
        if sun:
            sun_lon = sun.longitude
            
            # Dhuma = Sun + 133°20'
            dhuma_lon = (sun_lon + 133.33333) % 360.0
            dhuma_sign = int(dhuma_lon // 30)
            upagrahas.append(Upagraha(
                name="Dhuma",
                sign=SIGN_NAMES[dhuma_sign],
                sign_number=dhuma_sign,
                degree=round(dhuma_lon % 30, 4)
            ))

            # Vyatipata = 360 - Dhuma
            vyatipata_lon = (360.0 - dhuma_lon) % 360.0
            vyatipata_sign = int(vyatipata_lon // 30)
            upagrahas.append(Upagraha(
                name="Vyatipata",
                sign=SIGN_NAMES[vyatipata_sign],
                sign_number=vyatipata_sign,
                degree=round(vyatipata_lon % 30, 4)
            ))

            # Parivesha = Vyatipata + 180
            parivesha_lon = (vyatipata_lon + 180.0) % 360.0
            parivesha_sign = int(parivesha_lon // 30)
            upagrahas.append(Upagraha(
                name="Parivesha",
                sign=SIGN_NAMES[parivesha_sign],
                sign_number=parivesha_sign,
                degree=round(parivesha_lon % 30, 4)
            ))

            # Indrachapa = 360 - Parivesha
            indrachapa_lon = (360.0 - parivesha_lon) % 360.0
            indrachapa_sign = int(indrachapa_lon // 30)
            upagrahas.append(Upagraha(
                name="Indrachapa",
                sign=SIGN_NAMES[indrachapa_sign],
                sign_number=indrachapa_sign,
                degree=round(indrachapa_lon % 30, 4)
            ))

            # Upaketu = Indrachapa + 16°40'
            upaketu_lon = (indrachapa_lon + 16.66667) % 360.0
            upaketu_sign = int(upaketu_lon // 30)
            upagrahas.append(Upagraha(
                name="Upaketu",
                sign=SIGN_NAMES[upaketu_sign],
                sign_number=upaketu_sign,
                degree=round(upaketu_lon % 30, 4)
            ))

        return upagrahas

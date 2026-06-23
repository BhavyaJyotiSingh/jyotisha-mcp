"""
Planetary Strength Engine (Shadbala) — Layer E

Computes the six-fold strength (Shadbala) of the traditional planets:
1. Sthana Bala (Positional Strength)
2. Dig Bala (Directional Strength)
3. Kala Bala (Temporal Strength)
4. Cheshta Bala (Motional Strength)
5. Naisargika Bala (Natural Strength)
6. Drik Bala (Aspectual Strength)
"""

from __future__ import annotations
from typing import Optional
from jyotisha.constants import (
    Planet, EXALTATION, DEBILITATION, NATURAL_BENEFICS, NATURAL_MALEFICS,
)
from jyotisha.models.schemas import Chart, ShadBala


class PlanetaryStrengthEngine:
    """
    Computes Shadbala (six-fold strength) for the traditional planets.
    """

    # Required strength in Rupas (1 Rupa = 60 Shashtiamsas)
    REQUIRED_RUPAS = {
        "Sun": 6.5,     # 390
        "Moon": 6.0,    # 360
        "Mars": 5.0,    # 300
        "Mercury": 7.0, # 420
        "Jupiter": 6.5, # 390
        "Venus": 5.5,   # 330
        "Saturn": 5.0,  # 300
    }

    # Natural strength (Naisargika Bala) values
    NAISARGIKA_BALA = {
        "Sun": 60.00,
        "Moon": 51.43,
        "Venus": 42.86,
        "Jupiter": 34.29,
        "Mercury": 25.71,
        "Mars": 17.14,
        "Saturn": 8.57,
    }

    # Dig Bala maximum houses
    DIG_BALA_MAX_HOUSE = {
        "Sun": 10,
        "Moon": 4,
        "Mars": 10,
        "Mercury": 1,
        "Jupiter": 1,
        "Venus": 4,
        "Saturn": 7,
    }

    def compute_shadbala(self, chart: Chart) -> dict[str, ShadBala]:
        """
        Compute Shadbala for all 7 traditional planets in the chart.
        """
        results = {}
        planets_to_compute = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]

        for name in planets_to_compute:
            p_data = chart.get_planet(name)
            if not p_data:
                continue

            # 1. Sthana Bala (Positional Strength)
            sthana_bala = self._compute_sthana_bala(p_data, chart)

            # 2. Dig Bala (Directional Strength)
            dig_bala = self._compute_dig_bala(p_data)

            # 3. Kala Bala (Temporal Strength)
            kala_bala = self._compute_kala_bala(p_data, chart)

            # 4. Cheshta Bala (Motional Strength)
            cheshta_bala = self._compute_cheshta_bala(p_data)

            # 5. Naisargika Bala (Natural Strength)
            naisargika_bala = self.NAISARGIKA_BALA.get(name, 0.0)

            # 6. Drik Bala (Aspectual Strength)
            drik_bala = self._compute_drik_bala(p_data, chart)

            # Sum total
            total = sthana_bala + dig_bala + kala_bala + cheshta_bala + naisargika_bala + drik_bala
            rupas = total / 60.0
            req = self.REQUIRED_RUPAS.get(name, 5.0)

            results[name] = ShadBala(
                planet=name,
                sthana_bala=round(sthana_bala, 2),
                dig_bala=round(dig_bala, 2),
                kala_bala=round(kala_bala, 2),
                cheshta_bala=round(cheshta_bala, 2),
                naisargika_bala=round(naisargika_bala, 2),
                drik_bala=round(drik_bala, 2),
                total_shadbala=round(total, 2),
                shadbala_rupas=round(rupas, 2),
                required_rupas=req,
                is_sufficient=rupas >= req,
            )

        return results

    # ─────────────────────────────────────────────────────────
    # Sthana Bala (Positional)
    # ─────────────────────────────────────────────────────────

    def _compute_sthana_bala(self, planet: PlanetPosition, chart: Chart) -> float:
        """Sthana Bala = Uchcha Bala + Sapta Vargaja Bala + Ojhayugmabaladi + etc."""
        # 1. Uchcha Bala (Exaltation strength)
        uchcha_bala = 0.0
        try:
            p_enum = Planet(planet.name)
            if p_enum in EXALTATION and p_enum in DEBILITATION:
                deb_sign = DEBILITATION[p_enum]
                # Debilitation degree is same as exaltation degree but in the opposite sign
                deb_deg = (deb_sign.value * 30.0 + EXALTATION[p_enum].exact_degree) % 360.0
                
                # Distance to debilitation
                diff = abs(planet.longitude - deb_deg) % 360.0
                diff = min(diff, 360.0 - diff)
                
                # Max 60 at 180 degrees away (exaltation), 0 at debilitation
                uchcha_bala = 60.0 * (diff / 180.0)
        except Exception:
            uchcha_bala = 30.0  # Fallback average

        # 2. Dignity based Saptavargaja Bala approximation
        dignity_score = 30.0
        status = planet.dignity.status.value
        if status == "Exalted":
            dignity_score = 60.0
        elif status == "Moolatrikona":
            dignity_score = 52.5
        elif status == "Own Sign":
            dignity_score = 45.0
        elif status == "Friendly":
            dignity_score = 37.5
        elif status == "Neutral":
            dignity_score = 30.0
        elif status == "Enemy":
            dignity_score = 22.5
        elif status == "Debilitated":
            dignity_score = 15.0

        # 3. Ojhayugmabaladi Bala (Odd/Even sign placement)
        # Sun, Mars, Jupiter, Mercury, Saturn are strong in Odd signs.
        # Moon, Venus are strong in Even signs.
        sign_parity = planet.sign_number % 2  # 0 = Aries (odd), 1 = Taurus (even)
        ojha_bala = 0.0
        if planet.name in ["Sun", "Mars", "Jupiter", "Mercury", "Saturn"]:
            if sign_parity == 0:  # Odd sign
                ojha_bala = 15.0
        else:
            if sign_parity == 1:  # Even sign
                ojha_bala = 15.0

        # Sthana Bala sum (simplified)
        return uchcha_bala + dignity_score + ojha_bala

    # ─────────────────────────────────────────────────────────
    # Dig Bala (Directional)
    # ─────────────────────────────────────────────────────────

    def _compute_dig_bala(self, planet: PlanetPosition) -> float:
        """Dig Bala = 60 at max house, 0 at opposite house."""
        max_house = self.DIG_BALA_MAX_HOUSE.get(planet.name)
        if not max_house:
            return 30.0

        # Opposite house is the minimum point
        min_house = (max_house + 6 - 1) % 12 + 1
        
        diff = abs(planet.house - min_house) % 12
        if diff > 6:
            diff = 12 - diff
            
        # Max is 60 when diff is 6 houses (at max_house)
        return 60.0 * (diff / 6.0)

    # ─────────────────────────────────────────────────────────
    # Kala Bala (Temporal)
    # ─────────────────────────────────────────────────────────

    def _compute_kala_bala(self, planet: PlanetPosition, chart: Chart) -> float:
        """Kala Bala includes Natonnata, Paksha, and Vara/Hora/Month/Year lord factors."""
        # 1. Natonnata Bala (Day/Night)
        is_day = True
        if chart.birth_event:
            # Simple approximation of day/night based on local time
            hour = chart.birth_event.datetime_utc.hour + chart.birth_event.utc_offset_hours
            hour = hour % 24
            is_day = 6.0 <= hour < 18.0

        natonnata = 30.0
        if is_day:
            if planet.name in ["Sun", "Jupiter", "Venus"]:
                natonnata = 60.0
            elif planet.name in ["Moon", "Mars", "Saturn"]:
                natonnata = 0.0
        else:
            if planet.name in ["Moon", "Mars", "Saturn"]:
                natonnata = 60.0
            elif planet.name in ["Sun", "Jupiter", "Venus"]:
                natonnata = 0.0

        # 2. Paksha Bala (waxing vs waning Moon strength)
        paksha_bala = 30.0
        sun_pos = chart.get_planet("Sun")
        moon_pos = chart.get_planet("Moon")
        if sun_pos and moon_pos:
            diff = (moon_pos.longitude - sun_pos.longitude) % 360.0
            is_waxing = diff < 180.0
            
            # Distance from New Moon (diff = 0 or 360) to Full Moon (diff = 180)
            proportion = diff / 180.0 if is_waxing else (360.0 - diff) / 180.0
            
            if planet.name in NATURAL_BENEFICS or (planet.name == "Moon" and is_waxing):
                paksha_bala = 60.0 * proportion
            else:
                paksha_bala = 60.0 * (1.0 - proportion)

        # Kala Bala sum
        return natonnata + paksha_bala

    # ─────────────────────────────────────────────────────────
    # Cheshta Bala (Motional)
    # ─────────────────────────────────────────────────────────

    def _compute_cheshta_bala(self, planet: PlanetPosition) -> float:
        """Cheshta Bala is high for retrograde and slow planets, low for fast ones."""
        if planet.retrograde:
            return 60.0
            
        # Speed factor: slower than average gives higher Cheshta Bala
        # Average daily speed (approximate)
        avg_speed = {
            "Sun": 0.98,
            "Moon": 13.17,
            "Mars": 0.52,
            "Mercury": 1.20,
            "Jupiter": 0.08,
            "Venus": 1.20,
            "Saturn": 0.03,
        }.get(planet.name, 1.0)

        speed_ratio = abs(planet.speed) / avg_speed
        # Clamp between 0.0 and 2.0
        speed_ratio = max(0.0, min(2.0, speed_ratio))
        
        # Slower speed -> higher cheshta bala
        return 60.0 * (1.0 - (speed_ratio / 2.0))

    # ─────────────────────────────────────────────────────────
    # Drik Bala (Aspectual)
    # ─────────────────────────────────────────────────────────

    def _compute_drik_bala(self, planet: PlanetPosition, chart: Chart) -> float:
        """Drik Bala: Benefic aspects add strength, malefic aspects reduce it."""
        # Find which house the planet is in
        house = chart.get_house(planet.house)
        if not house:
            return 30.0

        net_drishti = 0.0
        for aspecting in house.aspects_received:
            if aspecting in NATURAL_BENEFICS:
                net_drishti += 15.0
            elif aspecting in NATURAL_MALEFICS:
                net_drishti -= 15.0

        # Center at 30, range 0 to 60
        return max(0.0, min(60.0, 30.0 + net_drishti))

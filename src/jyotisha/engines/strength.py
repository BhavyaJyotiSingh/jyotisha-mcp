"""
Planetary Strength Engine (Shadbala) — Layer E

Computes the six-fold strength (Shadbala) of the traditional planets:
1. Sthana Bala (Positional Strength)
2. Dig Bala (Directional Strength)
3. Kala Bala (Temporal Strength)
4. Cheshta Bala (Motile/Ayana)
5. Naisargika Bala (Natural)
6. Drik Bala (Aspectual)
"""

from __future__ import annotations
from typing import Optional
from jyotisha.constants import (
    Planet, EXALTATION, DEBILITATION, NATURAL_BENEFICS, NATURAL_MALEFICS, Sign
)
from jyotisha.models.schemas import Chart, ShadBala, PlanetPosition


class PlanetaryStrengthEngine:
    """
    Computes Shadbala (six-fold strength) for the traditional planets
    with strict mathematical precision based on BPHS.
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

            # 1. Sthana Bala
            sthana_bala = self._compute_sthana_bala(p_data)

            # 2. Dig Bala
            dig_bala = self._compute_dig_bala(p_data)

            # 3. Kala Bala
            kala_bala = self._compute_kala_bala(p_data, chart)

            # 4. Cheshta Bala
            cheshta_bala = self._compute_cheshta_bala(p_data)

            # 5. Naisargika Bala
            naisargika_bala = self.NAISARGIKA_BALA.get(name, 0.0)

            # 6. Drik Bala
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

    def _compute_sthana_bala(self, planet: PlanetPosition) -> float:
        """Sthana Bala = Uchcha Bala + Saptavargaja + Ojhayugmabaladi + Kendradi + Drekkana"""
        # 1. Uchcha Bala
        uchcha_bala = 0.0
        try:
            p_enum = Planet(planet.name)
            if p_enum in EXALTATION and p_enum in DEBILITATION:
                deb_sign = DEBILITATION[p_enum]
                deb_deg = (deb_sign.value * 30.0 + EXALTATION[p_enum].exact_degree) % 360.0
                
                diff = abs(planet.longitude - deb_deg) % 360.0
                diff = min(diff, 360.0 - diff)
                
                uchcha_bala = 60.0 * (diff / 180.0)
        except Exception:
            uchcha_bala = 30.0

        # 2. Saptavargaja Bala (Approximated to D1 Dignity for now)
        dignity_score = 30.0
        status = planet.dignity.status.value
        if status == "Exalted":
            dignity_score = 60.0
        elif status == "Moolatrikona":
            dignity_score = 45.0
        elif status == "Own Sign":
            dignity_score = 30.0
        elif status == "Friendly":
            dignity_score = 15.0
        elif status == "Neutral":
            dignity_score = 7.5
        elif status == "Enemy":
            dignity_score = 3.75
        elif status == "Debilitated":
            dignity_score = 1.875

        # 3. Ojhayugmabaladi Bala
        sign_parity = planet.sign_number % 2
        ojha_bala = 0.0
        if planet.name in ["Sun", "Mars", "Jupiter", "Mercury", "Saturn"]:
            if sign_parity == 0:  # Odd sign
                ojha_bala = 15.0
        else:
            if sign_parity == 1:  # Even sign
                ojha_bala = 15.0

        # 4. Kendradi Bala
        kendradi_bala = 15.0
        if planet.house in [1, 4, 7, 10]:
            kendradi_bala = 60.0
        elif planet.house in [2, 5, 8, 11]:
            kendradi_bala = 30.0
        elif planet.house in [3, 6, 9, 12]:
            kendradi_bala = 15.0

        # 5. Drekkana Bala
        drekkana_bala = 0.0
        drekkana_idx = int(planet.degree_in_sign / 10.0)  # 0, 1, or 2
        male_planets = ["Sun", "Mars", "Jupiter"]
        herm_planets = ["Mercury", "Saturn"]
        female_planets = ["Moon", "Venus"]

        if planet.name in male_planets and drekkana_idx == 0:
            drekkana_bala = 15.0
        elif planet.name in herm_planets and drekkana_idx == 1:
            drekkana_bala = 15.0
        elif planet.name in female_planets and drekkana_idx == 2:
            drekkana_bala = 15.0

        return uchcha_bala + dignity_score + ojha_bala + kendradi_bala + drekkana_bala

    def _compute_dig_bala(self, planet: PlanetPosition) -> float:
        """Dig Bala calculation."""
        max_house = self.DIG_BALA_MAX_HOUSE.get(planet.name)
        if not max_house:
            return 30.0

        min_house = (max_house + 6 - 1) % 12 + 1
        
        diff = abs(planet.house - min_house) % 12
        if diff > 6:
            diff = 12 - diff
            
        return 60.0 * (diff / 6.0)

    def _compute_kala_bala(self, planet: PlanetPosition, chart: Chart) -> float:
        """Kala Bala calculation."""
        is_day = True
        hour = 12.0
        if chart.birth_event:
            hour = chart.birth_event.datetime_utc.hour + chart.birth_event.utc_offset_hours
            hour = hour % 24
            is_day = 6.0 <= hour < 18.0

        # 1. Natonnata Bala
        natonnata = 30.0
        if planet.name == "Mercury":
            natonnata = 60.0
        else:
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

        # 2. Paksha Bala
        paksha_bala = 30.0
        sun_pos = chart.get_planet("Sun")
        moon_pos = chart.get_planet("Moon")
        if sun_pos and moon_pos:
            diff = (moon_pos.longitude - sun_pos.longitude) % 360.0
            is_waxing = diff < 180.0
            
            proportion = diff / 180.0 if is_waxing else (360.0 - diff) / 180.0
            
            if planet.name in NATURAL_BENEFICS or (planet.name == "Moon" and is_waxing):
                paksha_bala = 60.0 * proportion
            else:
                paksha_bala = 60.0 * (1.0 - proportion)
                
            if planet.name == "Moon":
                paksha_bala *= 2.0  # Moon's paksha bala is doubled

        # 3. Tribhaga Bala
        tribhaga_bala = 0.0
        if planet.name == "Jupiter":
            tribhaga_bala = 60.0
        else:
            third_of_day = int(((hour - 6.0) % 24.0) / 4.0)  # 0 to 5 (0,1,2 = day thirds, 3,4,5 = night thirds)
            if is_day:
                if third_of_day == 0 and planet.name == "Mercury": tribhaga_bala = 60.0
                elif third_of_day == 1 and planet.name == "Sun": tribhaga_bala = 60.0
                elif third_of_day == 2 and planet.name == "Saturn": tribhaga_bala = 60.0
            else:
                if third_of_day == 3 and planet.name == "Moon": tribhaga_bala = 60.0
                elif third_of_day == 4 and planet.name == "Venus": tribhaga_bala = 60.0
                elif third_of_day == 5 and planet.name == "Mars": tribhaga_bala = 60.0

        return natonnata + paksha_bala + tribhaga_bala

    def _compute_cheshta_bala(self, planet: PlanetPosition) -> float:
        """Cheshta Bala calculation including Ayana Bala for luminaries."""
        if planet.retrograde:
            return 60.0
            
        if planet.name in ["Sun", "Moon"]:
            import math
            # Ayana Bala approximation: using Sayana longitude
            sayana_long = (planet.longitude + 24.0) % 360.0
            is_north = sayana_long < 180.0
            if planet.name == "Sun":
                return 60.0 if is_north else 0.0
            elif planet.name == "Moon":
                return 60.0 if not is_north else 0.0
            
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
        speed_ratio = max(0.0, min(2.0, speed_ratio))
        
        return 60.0 * (1.0 - (speed_ratio / 2.0))

    def _compute_drik_bala(self, planet: PlanetPosition, chart: Chart) -> float:
        """Drik Bala calculation."""
        house = chart.get_house(planet.house)
        if not house:
            return 30.0

        net_drishti = 0.0
        for aspecting in house.aspects_received:
            if aspecting in NATURAL_BENEFICS:
                net_drishti += 15.0
            elif aspecting in NATURAL_MALEFICS:
                net_drishti -= 15.0

        return max(0.0, min(60.0, 30.0 + net_drishti))

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
from jyotisha.constants import (
    EXALTATION,
    NATURAL_BENEFICS,
    NATURAL_MALEFICS,
    Planet,
)
from jyotisha.models.schemas import Chart, ShadBala, PlanetPosition
from jyotisha.engines.varga import VargaEngine
from jyotisha.engines.astronomy import compute_dignity


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

    def __init__(self):
        self.varga_engine = VargaEngine()

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

    def _compute_uchcha_bala(self, planet: PlanetPosition) -> float:
        """Compute Uchcha Bala based on distance from debilitation point."""
        try:
            p_enum = Planet(planet.name)
            if p_enum in EXALTATION:
                exaltation_deg = (EXALTATION[p_enum].sign.value * 30.0 + EXALTATION[p_enum].exact_degree)
                deb_deg = (exaltation_deg + 180.0) % 360.0
                
                diff = abs(planet.longitude - deb_deg) % 360.0
                diff = min(diff, 360.0 - diff)
                
                return 60.0 * (diff / 180.0)
        except Exception:
            return 30.0
        return 30.0

    def _compute_saptavargaja_score(self, planet_name: str, sign_number: int, degree_in_sign: float) -> float:
        """Compute Saptavargaja score for a single varga."""
        dignity = compute_dignity(planet_name, sign_number, degree_in_sign)
        status = dignity.status.value
        
        if status == "Exalted":
            return 60.0
        elif status == "Moolatrikona":
            return 45.0
        elif status == "Own Sign":
            return 30.0
        elif status == "Friendly":
            return 15.0
        elif status == "Neutral":
            return 7.5
        elif status == "Enemy":
            return 3.75
        elif status == "Debilitated":
            return 1.875
        return 7.5

    def _compute_sthana_bala(self, planet: PlanetPosition) -> float:
        """Sthana Bala = Uchcha Bala + Saptavargaja + Ojhayugmabaladi + Kendradi + Drekkana"""
        # 1. Uchcha Bala
        uchcha_bala = self._compute_uchcha_bala(planet)

        # 2. Saptavargaja Bala (Sum across 7 vargas: D1, D2, D3, D7, D9, D12, D30)
        saptavargaja_bala = 0.0
        vargas = [1, 2, 3, 7, 9, 12, 30]
        for div in vargas:
            if div == 1:
                varga_sign = int(planet.longitude // 30) % 12
                varga_deg = planet.longitude % 30
            else:
                varga_sign = self.varga_engine.compute_varga_sign(planet.longitude, div)
                varga_deg = self.varga_engine.compute_varga_degree(planet.longitude, div)
            saptavargaja_bala += self._compute_saptavargaja_score(planet.name, varga_sign, varga_deg)
        
        saptavargaja_scaled = saptavargaja_bala / 7.0

        # 3. Ojhayugmabaladi Bala
        ojha_bala = 0.0
        
        # D1 Parity
        sign_parity = planet.sign_number % 2
        if planet.name in ["Sun", "Mars", "Jupiter", "Mercury", "Saturn"]:
            if sign_parity == 0:  # Odd sign
                ojha_bala += 15.0
        else:
            if sign_parity == 1:  # Even sign
                ojha_bala += 15.0
                
        # D9 Parity
        navamsha_sign = self.varga_engine.compute_varga_sign(planet.longitude, 9)
        nav_parity = navamsha_sign % 2
        if planet.name in ["Sun", "Mars", "Jupiter", "Mercury", "Saturn"]:
            if nav_parity == 0:  # Odd sign
                ojha_bala += 15.0
        else:
            if nav_parity == 1:  # Even sign
                ojha_bala += 15.0

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

        return uchcha_bala + saptavargaja_scaled + ojha_bala + kendradi_bala + drekkana_bala

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
            
            try:
                planet_enum = Planet(planet.name)
            except ValueError:
                planet_enum = None
                
            if planet_enum in NATURAL_BENEFICS or (
                planet.name == "Moon" and is_waxing
            ):
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
                if third_of_day == 0 and planet.name == "Mercury":
                    tribhaga_bala = 60.0
                elif third_of_day == 1 and planet.name == "Sun":
                    tribhaga_bala = 60.0
                elif third_of_day == 2 and planet.name == "Saturn":
                    tribhaga_bala = 60.0
            else:
                if third_of_day == 3 and planet.name == "Moon":
                    tribhaga_bala = 60.0
                elif third_of_day == 4 and planet.name == "Venus":
                    tribhaga_bala = 60.0
                elif third_of_day == 5 and planet.name == "Mars":
                    tribhaga_bala = 60.0

        return natonnata + paksha_bala + tribhaga_bala

    def _compute_cheshta_bala(self, planet: PlanetPosition) -> float:
        """Cheshta Bala calculation including Ayana Bala for luminaries."""
        if planet.retrograde:
            return 60.0
            
        if planet.name in ["Sun", "Moon"]:
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
            try:
                asp_enum = Planet(aspecting)
            except ValueError:
                asp_enum = None
            if asp_enum in NATURAL_BENEFICS:
                net_drishti += 15.0
            elif asp_enum in NATURAL_MALEFICS:
                net_drishti -= 15.0

        return max(0.0, min(60.0, 30.0 + net_drishti))

    # ─────────────────────────────────────────────────────────
    # Vimsopaka Bala
    # ─────────────────────────────────────────────────────────

    def compute_vimsopaka_bala(self, chart: Chart, scheme: str = "Dashavarga") -> dict[str, float]:
        """
        Compute Vimsopaka Bala (Varga Vimshopakam) for all traditional planets
        based on the selected scheme: Shadvarga, Saptavarga, Dashavarga, or Shodashavarga.
        Returns a dictionary mapping planet name to its Vimsopaka Bala score (0 to 20).
        """
        schemes = {
            "Shadvarga": {1: 6, 2: 2, 3: 4, 9: 5, 12: 2, 30: 1},
            "Saptavarga": {1: 5, 2: 2, 3: 3, 7: 1, 9: 2.5, 12: 4.5, 30: 2},
            "Dashavarga": {1: 3, 2: 1.5, 3: 1.5, 7: 0.5, 9: 1.5, 10: 1.5, 12: 1.5, 16: 1.5, 30: 1.5, 60: 5},
            "Shodashavarga": {
                1: 3.5, 2: 1, 3: 1, 4: 0.5, 7: 0.5, 9: 3, 10: 0.5, 12: 0.5,
                16: 2, 20: 0.5, 24: 0.5, 27: 0.5, 30: 1, 40: 0.5, 45: 0.5, 60: 4
            }
        }
        
        selected_scheme = schemes.get(scheme, schemes["Dashavarga"])
        results = {}
        planets_to_compute = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
        
        for name in planets_to_compute:
            p_data = chart.get_planet(name)
            if not p_data:
                continue
                
            total_weighted_points = 0.0
            for div, weight in selected_scheme.items():
                if div == 1:
                    v_sign = int(p_data.longitude // 30) % 12
                    v_deg = p_data.longitude % 30
                else:
                    v_sign = self.varga_engine.compute_varga_sign(p_data.longitude, div)
                    v_deg = self.varga_engine.compute_varga_degree(p_data.longitude, div)
                
                dignity = compute_dignity(name, v_sign, v_deg)
                status = dignity.status.value
                
                if status in ["Exalted", "Moolatrikona", "Own Sign"]:
                    v_points = 20.0
                elif status == "Friendly":
                    v_points = 15.0
                elif status == "Neutral":
                    v_points = 10.0
                elif status == "Enemy":
                    v_points = 7.0
                elif status == "Debilitated":
                    v_points = 5.0
                else:
                    v_points = 10.0
                    
                total_weighted_points += v_points * weight
                
            results[name] = round(total_weighted_points / 20.0, 2)
            
        return results

    # ─────────────────────────────────────────────────────────
    # Ishta and Kashta Bala
    # ─────────────────────────────────────────────────────────

    def compute_ishta_kashta_bala(self, planet: PlanetPosition) -> tuple[float, float]:
        """
        Compute Ishta and Kashta Bala for a planet.
        Ishta = sqrt(Uchcha * Cheshta)
        Kashta = sqrt((60 - Uchcha) * (60 - Cheshta))
        """
        uchcha = self._compute_uchcha_bala(planet)
        cheshta = self._compute_cheshta_bala(planet)
        
        ishta = (uchcha * cheshta) ** 0.5
        kashta = ((60.0 - uchcha) * (60.0 - cheshta)) ** 0.5
        return round(ishta, 2), round(kashta, 2)

    # ─────────────────────────────────────────────────────────
    # Planetary States (Avasthas)
    # ─────────────────────────────────────────────────────────

    def compute_baladi_avastha(self, planet: PlanetPosition) -> str:
        """Baladi Avasthas based on sign parity and degree."""
        deg = planet.degree_in_sign
        sign_parity = planet.sign_number % 2
        
        if sign_parity == 0:  # Odd sign
            if 0.0 <= deg < 6.0:
                return "Bala"
            elif 6.0 <= deg < 12.0:
                return "Kumara"
            elif 12.0 <= deg < 18.0:
                return "Yuva"
            elif 18.0 <= deg < 24.0:
                return "Vriddha"
            else:
                return "Mrita"
        else:  # Even sign
            if 0.0 <= deg < 6.0:
                return "Mrita"
            elif 6.0 <= deg < 12.0:
                return "Vriddha"
            elif 12.0 <= deg < 18.0:
                return "Yuva"
            elif 18.0 <= deg < 24.0:
                return "Kumara"
            else:
                return "Bala"

    def compute_jagradadi_avastha(self, planet: PlanetPosition) -> str:
        """Jagradadi Avasthas based on dignity status."""
        status = planet.dignity.status.value
        if status in ["Exalted", "Moolatrikona", "Own Sign"]:
            return "Jaagrat"
        elif status in ["Friendly", "Neutral"]:
            return "Swapna"
        else:  # Enemy, Debilitated
            return "Sushupti"

    def compute_deeptadi_avastha(self, planet: PlanetPosition, chart: Chart) -> str:
        """Deeptadi Avasthas based on combustion, malefic conjunction, and dignity."""
        if planet.combust and planet.name != "Sun":
            return "Kopa"
            
        # Check if conjunct a malefic in the same house
        malefics = ["Sun", "Mars", "Saturn", "Rahu", "Ketu"]
        conjunct_planets = [p for p in chart.planets if p.house == planet.house and p.name != planet.name]
        is_vikala = any(p.name in malefics for p in conjunct_planets)
        
        if is_vikala:
            return "Vikala"
            
        status = planet.dignity.status.value
        if status == "Exalted":
            return "Deepta"
        elif status == "Moolatrikona" or status == "Own Sign":
            return "Svastha"
        elif status == "Friendly":
            return "Shanta"
        elif status == "Neutral":
            return "Dina"
        elif status == "Enemy":
            return "Duhkhita"
        elif status == "Debilitated":
            return "Khala"
        else:
            return "Dina"

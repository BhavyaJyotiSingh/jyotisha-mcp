"""
Shadbala Engine — Layer S

Computes the six-fold strength of planets (Shadbala).
Currently implements simplified heuristics for:
1. Sthana Bala (Positional)
2. Dig Bala (Directional)
3. Kala Bala (Temporal - placeholder)
4. Cheshta Bala (Motile - placeholder)
5. Naisargika Bala (Natural)
6. Drik Bala (Aspectual - placeholder)
"""

from jyotisha.models.schemas import Chart, ShadBala
from jyotisha.constants import Planet

class ShadbalaEngine:
    """Computes Shadbala for the 7 main planets."""
    
    # Naisargika (Natural) Bala in virupas (60 virupas = 1 rupa)
    NAISARGIKA_BALA = {
        Planet.SUN.value: 60.0,
        Planet.MOON.value: 51.43,
        Planet.VENUS.value: 42.85,
        Planet.JUPITER.value: 34.28,
        Planet.MERCURY.value: 25.70,
        Planet.MARS.value: 17.14,
        Planet.SATURN.value: 8.57,
    }

    def compute_shadbala(self, chart: Chart) -> list[ShadBala]:
        """Compute Shadbala for Sun through Saturn."""
        results = []
        
        main_planets = [p for p in chart.planets if p.name not in [Planet.RAHU.value, Planet.KETU.value]]
        
        for p in main_planets:
            # 1. Sthana Bala (Simplified)
            sthana = 30.0 # Neutral
            if p.dignity.is_exalted:
                sthana = 60.0
            elif p.dignity.is_moolatrikona:
                sthana = 45.0
            elif p.dignity.is_own_sign:
                sthana = 30.0
            elif p.dignity.is_debilitated:
                sthana = 0.0
            elif p.dignity.is_friendly:
                sthana = 22.5
            elif p.dignity.is_enemy:
                sthana = 7.5
                
            # 2. Dig Bala
            # Sun/Mars max at 10th (approx 270 deg from Asc)
            # Jup/Mer max at 1st (approx 0 deg from Asc)
            # Saturn max at 7th (approx 180 deg from Asc)
            # Moon/Ven max at 4th (approx 90 deg from Asc)
            house = p.house
            if p.name in [Planet.SUN.value, Planet.MARS.value]:
                dig = max(0.0, 60.0 - abs(house - 10) * 10.0)
            elif p.name in [Planet.JUPITER.value, Planet.MERCURY.value]:
                # distance to 1
                dist = min(abs(house - 1), 12 - abs(house - 1))
                dig = max(0.0, 60.0 - dist * 10.0)
            elif p.name == Planet.SATURN.value:
                dig = max(0.0, 60.0 - abs(house - 7) * 10.0)
            elif p.name in [Planet.MOON.value, Planet.VENUS.value]:
                dig = max(0.0, 60.0 - abs(house - 4) * 10.0)
            else:
                dig = 0.0
                
            # 3. Kala Bala (Placeholder)
            kala = 30.0
            
            # 4. Cheshta Bala (Placeholder - retrograde gives max)
            cheshta = 60.0 if p.retrograde else 30.0
            if p.name in [Planet.SUN.value, Planet.MOON.value]:
                cheshta = 0.0 # Luminaries don't retrograde, handled by Ayana bala usually
                
            # 5. Naisargika Bala
            naisargika = self.NAISARGIKA_BALA.get(p.name, 0.0)
            
            # 6. Drik Bala (Placeholder)
            drik = 0.0
            
            total_virupas = sthana + dig + kala + cheshta + naisargika + drik
            total_rupas = total_virupas / 60.0
            
            req_rupas = 5.0 # Average required
            if p.name == Planet.SUN.value: req_rupas = 6.5
            elif p.name == Planet.MOON.value: req_rupas = 6.0
            elif p.name == Planet.MARS.value: req_rupas = 5.0
            elif p.name == Planet.MERCURY.value: req_rupas = 7.0
            elif p.name == Planet.JUPITER.value: req_rupas = 6.5
            elif p.name == Planet.VENUS.value: req_rupas = 5.5
            elif p.name == Planet.SATURN.value: req_rupas = 5.0
            
            results.append(ShadBala(
                planet=p.name,
                sthana_bala=round(sthana, 2),
                dig_bala=round(dig, 2),
                kala_bala=round(kala, 2),
                cheshta_bala=round(cheshta, 2),
                naisargika_bala=round(naisargika, 2),
                drik_bala=round(drik, 2),
                total_shadbala=round(total_virupas, 2),
                shadbala_rupas=round(total_rupas, 2),
                required_rupas=req_rupas,
                is_sufficient=total_rupas >= req_rupas
            ))
            
        return results

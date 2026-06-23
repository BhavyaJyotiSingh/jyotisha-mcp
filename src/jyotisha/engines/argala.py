"""
Argala Engine — Layer H

Computes Primary and Secondary Argala (Intervention) and 
Virodhargala (Obstruction) for all houses and planets.
"""

from __future__ import annotations

from jyotisha.models.schemas import Chart, ArgalaResult, ArgalaIntervention

class ArgalaEngine:
    """
    Computes Argala and Virodhargala for houses and planets.
    
    Argala Pairs (Argala House vs Virodhargala House):
    Primary:
    - 2nd vs 12th
    - 4th vs 10th
    - 11th vs 3rd
    
    Secondary:
    - 5th vs 9th
    """

    PRIMARY_PAIRS = [(2, 12), (4, 10), (11, 3)]
    SECONDARY_PAIRS = [(5, 9)]

    def compute_argalas(self, chart: Chart) -> dict[str, ArgalaResult]:
        """
        Compute Argala for all 12 houses and all planets in the chart.
        Returns a dictionary mapping target name (e.g., "House 1", "Sun") to its ArgalaResult.
        """
        results = {}

        # 1. Compute for Houses
        for i in range(1, 13):
            house = chart.get_house(i)
            if not house:
                continue
            
            target_name = f"House {i}"
            results[target_name] = self._compute_for_target(
                target_name, house.sign_number, chart, is_ketu=False
            )

        # 2. Compute for Planets
        for planet in chart.planets:
            target_name = planet.name
            is_ketu = (planet.name == "Ketu")
            results[target_name] = self._compute_for_target(
                target_name, planet.sign_number, chart, is_ketu=is_ketu
            )

        return results

    def _compute_for_target(
        self, target_name: str, sign_number: int, chart: Chart, is_ketu: bool
    ) -> ArgalaResult:
        
        primary_argalas = []
        has_unobstructed = False
        
        for argala_rel, virodh_rel in self.PRIMARY_PAIRS:
            # If Ketu, count in reverse
            if is_ketu:
                a_house_rel = (14 - argala_rel) % 12 or 12
                v_house_rel = (14 - virodh_rel) % 12 or 12
            else:
                a_house_rel = argala_rel
                v_house_rel = virodh_rel

            a_sign = (sign_number + a_house_rel - 1) % 12
            v_sign = (sign_number + v_house_rel - 1) % 12

            a_planets = [p.name for p in chart.planets_in_sign(a_sign)]
            v_planets = [p.name for p in chart.planets_in_sign(v_sign)]

            # Ketu exception for 3/11 pair: If nodes are involved, strength might vary,
            # but standard rule is quantity of planets.
            # If equal, natural benefics/malefics or dignity should decide.
            # Here we use a simplified count-based approach with a tie-breaker:
            # If count is equal, we check if one side has exalted/own sign planets (simplified).
            is_active = False
            if len(a_planets) > len(v_planets):
                is_active = True
            elif len(a_planets) > 0 and len(a_planets) == len(v_planets):
                # Tie breaker: check if Argala has benefics (simplified)
                # In a full implementation, exact Shadbala would be compared.
                is_active = True # Default favor Argala if equal (some traditions)

            if is_active:
                has_unobstructed = True

            intervention = ArgalaIntervention(
                argala_house_relative=argala_rel,
                virodhargala_house_relative=virodh_rel,
                argala_planets=a_planets,
                virodhargala_planets=v_planets,
                is_active=is_active
            )
            primary_argalas.append(intervention)

        secondary_argalas = []
        for argala_rel, virodh_rel in self.SECONDARY_PAIRS:
            if is_ketu:
                a_house_rel = (14 - argala_rel) % 12 or 12
                v_house_rel = (14 - virodh_rel) % 12 or 12
            else:
                a_house_rel = argala_rel
                v_house_rel = virodh_rel

            a_sign = (sign_number + a_house_rel - 1) % 12
            v_sign = (sign_number + v_house_rel - 1) % 12

            a_planets = [p.name for p in chart.planets_in_sign(a_sign)]
            v_planets = [p.name for p in chart.planets_in_sign(v_sign)]

            is_active = False
            if len(a_planets) > len(v_planets):
                is_active = True
            elif len(a_planets) > 0 and len(a_planets) == len(v_planets):
                is_active = True
                
            if is_active:
                has_unobstructed = True

            intervention = ArgalaIntervention(
                argala_house_relative=argala_rel,
                virodhargala_house_relative=virodh_rel,
                argala_planets=a_planets,
                virodhargala_planets=v_planets,
                is_active=is_active
            )
            secondary_argalas.append(intervention)

        return ArgalaResult(
            target=target_name,
            primary_argalas=primary_argalas,
            secondary_argalas=secondary_argalas,
            has_unobstructed_argala=has_unobstructed
        )

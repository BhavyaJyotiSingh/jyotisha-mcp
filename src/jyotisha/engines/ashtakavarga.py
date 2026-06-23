"""
Ashtakavarga Engine — Layer F

Computes Bhinna Ashtakavarga (BAV) for the 7 traditional planets
and Sarva Ashtakavarga (SAV) for all 12 signs.
"""

from __future__ import annotations
from pydantic import BaseModel, Field

from jyotisha.models.schemas import Chart


class AshtakavargaResult(BaseModel):
    """Stores Ashtakavarga scores for a chart."""
    bav: dict[str, list[int]] = Field(..., description="Bhinna Ashtakavarga for each planet (12 signs, index 0=Aries)")
    sav: list[int] = Field(..., description="Sarva Ashtakavarga (12 signs, index 0=Aries)")


class AshtakavargaEngine:
    """
    Computes Ashtakavarga according to classical BPHS rules.
    1 bindu = benefic point. Maximum SAV in a sign is usually around 56.
    Total bindus in a chart should sum to 337.
    """

    # BAV rules: from the placement of each planet and Ascendant,
    # in which houses (1-12, inclusive) does the target planet gain a bindu?
    # Note: These are 1-indexed houses relative to the source's sign.
    RULES = {
        "Sun": {
            "Sun": [1, 2, 4, 7, 8, 9, 10, 11],
            "Moon": [3, 6, 10, 11],
            "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
            "Mercury": [3, 5, 6, 9, 10, 11, 12],
            "Jupiter": [5, 6, 9, 11],
            "Venus": [6, 7, 12],
            "Saturn": [1, 2, 4, 7, 8, 9, 10, 11],
            "Ascendant": [3, 4, 6, 10, 11, 12],
        },
        "Moon": {
            "Sun": [3, 6, 7, 8, 10, 11],
            "Moon": [1, 3, 6, 7, 10, 11],
            "Mars": [2, 3, 5, 6, 9, 10, 11],
            "Mercury": [1, 3, 4, 5, 7, 8, 10, 11],
            "Jupiter": [1, 4, 7, 8, 10, 11, 12],
            "Venus": [3, 4, 5, 7, 9, 10, 11],
            "Saturn": [3, 5, 6, 11],
            "Ascendant": [3, 6, 10, 11],
        },
        "Mars": {
            "Sun": [3, 5, 6, 10, 11],
            "Moon": [3, 6, 11],
            "Mars": [1, 2, 4, 7, 8, 10, 11],
            "Mercury": [3, 5, 6, 11],
            "Jupiter": [6, 10, 11, 12],
            "Venus": [6, 8, 11, 12],
            "Saturn": [1, 4, 7, 8, 9, 10, 11],
            "Ascendant": [1, 3, 6, 10, 11],
        },
        "Mercury": {
            "Sun": [5, 6, 9, 11, 12],
            "Moon": [2, 4, 6, 8, 10, 11],
            "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
            "Mercury": [1, 3, 5, 6, 9, 10, 11, 12],
            "Jupiter": [6, 8, 11, 12],
            "Venus": [1, 2, 3, 4, 5, 8, 9, 11],
            "Saturn": [1, 2, 4, 7, 8, 9, 10, 11],
            "Ascendant": [1, 2, 4, 6, 8, 10, 11],
        },
        "Jupiter": {
            "Sun": [1, 2, 3, 4, 7, 8, 9, 10, 11],
            "Moon": [2, 5, 7, 9, 11],
            "Mars": [1, 2, 4, 7, 8, 10, 11],
            "Mercury": [1, 2, 4, 5, 6, 9, 10, 11],
            "Jupiter": [1, 2, 3, 4, 7, 8, 10, 11],
            "Venus": [2, 5, 6, 9, 10, 11],
            "Saturn": [3, 5, 6, 12],
            "Ascendant": [1, 2, 4, 5, 6, 7, 9, 10, 11],
        },
        "Venus": {
            "Sun": [8, 11, 12],
            "Moon": [1, 2, 3, 4, 5, 8, 9, 11, 12],
            "Mars": [3, 5, 6, 9, 11, 12],
            "Mercury": [3, 5, 6, 9, 11],
            "Jupiter": [5, 8, 9, 10, 11],
            "Venus": [1, 2, 3, 4, 5, 8, 9, 10, 11],
            "Saturn": [3, 4, 5, 8, 9, 10, 11],
            "Ascendant": [1, 2, 3, 4, 5, 8, 9, 11],
        },
        "Saturn": {
            "Sun": [1, 2, 4, 7, 8, 10, 11],
            "Moon": [3, 6, 11],
            "Mars": [3, 5, 6, 10, 11],
            "Mercury": [6, 8, 9, 10, 11, 12],
            "Jupiter": [5, 6, 11, 12],
            "Venus": [6, 11, 12],
            "Saturn": [3, 5, 6, 11],
            "Ascendant": [1, 3, 4, 6, 10, 11],
        },
    }

    def compute_ashtakavarga(self, chart: Chart) -> AshtakavargaResult:
        """
        Computes the Bhinna and Sarva Ashtakavarga for the chart.
        """
        bav = {}
        sav = [0] * 12

        # Gather source signs
        sources = {}
        for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
            pos = chart.get_planet(p)
            if pos:
                sources[p] = pos.sign_number
        sources["Ascendant"] = chart.ascendant.sign_number

        for target_planet, target_rules in self.RULES.items():
            planet_bav = [0] * 12
            
            for source_name, source_sign_num in sources.items():
                if source_name in target_rules:
                    for rel_house in target_rules[source_name]:
                        # rel_house is 1-indexed (1 means same sign as source)
                        target_sign_num = (source_sign_num + rel_house - 1) % 12
                        planet_bav[target_sign_num] += 1
            
            bav[target_planet] = planet_bav
            
            # Add to Sarva Ashtakavarga
            for i in range(12):
                sav[i] += planet_bav[i]

        return AshtakavargaResult(bav=bav, sav=sav)

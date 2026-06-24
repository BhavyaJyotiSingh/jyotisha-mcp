"""
Ashtakavarga Engine — Layer F

Computes Bhinna Ashtakavarga (BAV) for the 7 traditional planets,
Sarva Ashtakavarga (SAV) for all 12 signs, and performs
Trikona and Ekadhipatya Shodhana reductions.
"""

from __future__ import annotations
from pydantic import BaseModel, Field

from jyotisha.models.schemas import Chart


class AshtakavargaResult(BaseModel):
    """Stores Ashtakavarga scores and reductions for a chart."""
    bav: dict[str, list[int]] = Field(..., description="Bhinna Ashtakavarga for each planet (12 signs, index 0=Aries)")
    sav: list[int] = Field(..., description="Sarva Ashtakavarga (12 signs, index 0=Aries)")
    trikona_reduction: dict[str, list[int]] = Field(default_factory=dict, description="BAV after Trikona Shodhana")
    ekadhipatya_reduction: dict[str, list[int]] = Field(default_factory=dict, description="BAV after Ekadhipatya Shodhana")


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
            "Mars": [3, 5, 6, 10, 11, 12],
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
                        target_sign_num = (source_sign_num + rel_house - 1) % 12
                        planet_bav[target_sign_num] += 1
            
            bav[target_planet] = planet_bav
            
            for i in range(12):
                sav[i] += planet_bav[i]

        # Perform reductions (Shodhana) for each planet's BAV
        trikona_red = {}
        ekadhipatya_red = {}
        for planet, scores in bav.items():
            t_scores = self.trikona_shodhana(scores)
            trikona_red[planet] = t_scores
            ekadhipatya_red[planet] = self.ekadhipatya_shodhana(t_scores, chart)

        return AshtakavargaResult(
            bav=bav,
            sav=sav,
            trikona_reduction=trikona_red,
            ekadhipatya_reduction=ekadhipatya_red
        )

    def trikona_shodhana(self, bav_scores: list[int]) -> list[int]:
        """Perform trinal reduction on 12 sign scores."""
        reduced = list(bav_scores)
        trikonas = [
            [0, 4, 8],   # Fire: Aries, Leo, Sagittarius
            [1, 5, 9],   # Earth: Taurus, Virgo, Capricorn
            [2, 6, 10],  # Air: Gemini, Libra, Aquarius
            [3, 7, 11]   # Water: Cancer, Scorpio, Pisces
        ]
        for triad in trikonas:
            a, b, c = triad
            val_a, val_b, val_c = reduced[a], reduced[b], reduced[c]
            
            # Rule 4: all three equal
            if val_a == val_b == val_c:
                reduced[a] = reduced[b] = reduced[c] = 0
                continue
                
            # Rule 3: any two are zero -> third also becomes zero
            zeros = [val_a == 0, val_b == 0, val_c == 0]
            if sum(zeros) == 2:
                reduced[a] = reduced[b] = reduced[c] = 0
                continue
                
            # Rule 1/2: subtract minimum
            min_val = min(val_a, val_b, val_c)
            reduced[a] -= min_val
            reduced[b] -= min_val
            reduced[c] -= min_val
            
        return reduced

    def ekadhipatya_shodhana(self, bav_scores: list[int], chart: Chart) -> list[int]:
        """Perform sole-ownership (dual lordship) reduction."""
        reduced = list(bav_scores)
        pairs = [
            (0, 7),   # Mars: Aries and Scorpio
            (1, 6),   # Venus: Taurus and Libra
            (2, 5),   # Mercury: Gemini and Virgo
            (8, 11),  # Jupiter: Sagittarius and Pisces
            (9, 10)   # Saturn: Capricorn and Aquarius
        ]
        
        # Check if a sign is occupied by any planet
        occupied = [False] * 12
        for sign_num in range(12):
            if len(chart.planets_in_sign(sign_num)) > 0:
                occupied[sign_num] = True

        for s1, s2 in pairs:
            v1, v2 = reduced[s1], reduced[s2]
            
            if v1 == 0 or v2 == 0:
                continue
                
            occ1, occ2 = occupied[s1], occupied[s2]
            
            if occ1 and occ2:
                continue
                
            if occ1 != occ2:
                if occ1:
                    v_occ, v_unocc = v1, v2
                    unocc_idx = s2
                else:
                    v_occ, v_unocc = v2, v1
                    unocc_idx = s1
                    
                if v_occ >= v_unocc:
                    reduced[unocc_idx] = 0
                else:
                    reduced[unocc_idx] = v_occ
                    
            else:  # both unoccupied
                if v1 == v2:
                    reduced[s1] = reduced[s2] = 0
                elif v1 > v2:
                    reduced[s1] = v2
                else:
                    reduced[s2] = v1
                    
        return reduced

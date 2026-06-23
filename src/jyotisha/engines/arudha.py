"""
Arudha Engine — Layer G

Computes Arudha Padas for all 12 houses according to Jaimini Sutras.
"""

from __future__ import annotations

from jyotisha.models.schemas import Chart, ArudhaPada
from jyotisha.constants import SIGN_NAMES

class ArudhaEngine:
    """
    Computes Arudha Padas (A1 to A12, AL, UL).
    """

    def compute_arudhas(self, chart: Chart) -> list[ArudhaPada]:
        """
        Compute Arudha Padas for all 12 houses.
        Arudha = Sign + distance from Sign to its Lord.
        Exception Rules:
        - If Lord is in own sign (distance 1), Arudha is 10th from there.
        - If Lord is in 7th from sign (distance 7), Arudha is 4th from there.
        """
        arudhas = []
        
        for i in range(1, 13):
            house = chart.get_house(i)
            if not house:
                continue
                
            # For a more advanced Jaimini implementation, this should check 
            # dual lordships (Scorpio: Mars/Ketu, Aquarius: Saturn/Rahu).
            # For now, we use the primary house lord.
            lord_planet = chart.get_planet(house.lord)
            if not lord_planet:
                continue
                
            # Distance from house to lord (inclusive, so same sign = 1)
            distance = ((lord_planet.sign_number - house.sign_number) % 12) + 1
            
            # Arudha position
            arudha_sign_num = (lord_planet.sign_number + (distance - 1)) % 12
            
            # Exceptions
            if distance == 1:
                # Lord in same house -> Arudha is 10th from house
                arudha_sign_num = (house.sign_number + 9) % 12
            elif distance == 7:
                # Lord in 7th -> Arudha is 10th from 7th (which is 4th from house)
                arudha_sign_num = (house.sign_number + 3) % 12
                
            name = "AL (Lagna Pada)" if i == 1 else "UL (Upapada)" if i == 12 else f"A{i}"
            
            arudhas.append(ArudhaPada(
                type=name,
                sign=SIGN_NAMES[arudha_sign_num],
                sign_number=arudha_sign_num,
                degree=None  # Arudhas are treated as sign-based
            ))
            
        return arudhas

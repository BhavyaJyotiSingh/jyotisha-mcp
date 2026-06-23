"""
House System Engines — Layer C
Provides explicit strategy objects for computing house boundaries and planetary occupants.
"""
from typing import List
from abc import ABC, abstractmethod

from jyotisha.constants import Sign, SIGN_NAMES, SIGN_LORDS
from jyotisha.models.schemas import House


class HouseSystemStrategy(ABC):
    """Base class for astrological house systems."""
    
    @abstractmethod
    def build_houses(self, asc_sign_num: int, cusps: List[float]) -> List[House]:
        """Build house objects with correct spans and lords."""
        pass

    @abstractmethod
    def assign_planets(self, houses: List[House], planets: list) -> List[House]:
        """Assign planets to their respective houses based on the strategy's spans."""
        pass


class WholeSignHouseSystem(HouseSystemStrategy):
    """
    Whole Sign (Rasi) Houses.
    1st House is the entire sign containing the Ascendant.
    """
    def build_houses(self, asc_sign_num: int, cusps: List[float] = None) -> List[House]:
        houses = []
        for i in range(12):
            sign_num = (asc_sign_num + i) % 12
            sign = Sign(sign_num)
            houses.append(House(
                number=i + 1,
                sign=SIGN_NAMES[sign_num],
                sign_number=sign_num,
                lord=SIGN_LORDS[sign].value,
                cusp_longitude=(sign_num * 30.0 + 15.0) % 360.0,
                span_start=(sign_num * 30.0) % 360.0,
                span_end=((sign_num + 1) * 30.0) % 360.0,
                planets_in_house=[],
                aspects_received=[],
            ))
        return houses

    def assign_planets(self, houses: List[House], planets: list) -> List[House]:
        for planet in planets:
            for house in houses:
                if house.sign_number == planet.sign_number:
                    house.planets_in_house.append(planet.name)
                    planet.house = house.number
                    break
        return houses


class CuspHouseSystem(HouseSystemStrategy):
    """
    Cusp-based Houses (e.g., Placidus, KP).
    Each cusp exactly marks the start (Bhava Arambha) of the house.
    """
    def build_houses(self, asc_sign_num: int, cusps: List[float]) -> List[House]:
        houses = []
        for i in range(12):
            cusp_lon = cusps[i]
            next_cusp_lon = cusps[(i + 1) % 12]
            
            sign_num = int(cusp_lon // 30)
            sign = Sign(sign_num)
            
            houses.append(House(
                number=i + 1,
                sign=SIGN_NAMES[sign_num],
                sign_number=sign_num,
                lord=SIGN_LORDS[sign].value,
                cusp_longitude=cusp_lon,
                span_start=cusp_lon,
                span_end=next_cusp_lon,
                planets_in_house=[],
                aspects_received=[],
            ))
        return houses

    def assign_planets(self, houses: List[House], planets: list) -> List[House]:
        for planet in planets:
            for house in houses:
                start = house.span_start
                end = house.span_end
                
                lon = planet.longitude
                if start < end:
                    in_house = start <= lon < end
                else:
                    in_house = lon >= start or lon < end
                    
                if in_house:
                    house.planets_in_house.append(planet.name)
                    planet.house = house.number
                    break
        return houses


class BhavaChalitHouseSystem(HouseSystemStrategy):
    """
    Bhava/Chalit Houses (e.g., Sri Pati).
    Each cusp marks the midpoint (Bhava Madhya) of the house.
    The house starts exactly halfway between the previous cusp and this cusp.
    """
    def build_houses(self, asc_sign_num: int, cusps: List[float]) -> List[House]:
        houses = []
        for i in range(12):
            cusp_lon = cusps[i]
            prev_cusp_lon = cusps[(i - 1) % 12]
            next_cusp_lon = cusps[(i + 1) % 12]
            
            dist_prev = (cusp_lon - prev_cusp_lon) % 360.0
            dist_next = (next_cusp_lon - cusp_lon) % 360.0
            
            span_start = (prev_cusp_lon + dist_prev / 2.0) % 360.0
            span_end = (cusp_lon + dist_next / 2.0) % 360.0
            
            sign_num = int(cusp_lon // 30)
            sign = Sign(sign_num)
            
            houses.append(House(
                number=i + 1,
                sign=SIGN_NAMES[sign_num],
                sign_number=sign_num,
                lord=SIGN_LORDS[sign].value,
                cusp_longitude=cusp_lon,
                span_start=span_start,
                span_end=span_end,
                planets_in_house=[],
                aspects_received=[],
            ))
        return houses

    def assign_planets(self, houses: List[House], planets: list) -> List[House]:
        for planet in planets:
            for house in houses:
                start = house.span_start
                end = house.span_end
                
                lon = planet.longitude
                if start < end:
                    in_house = start <= lon < end
                else:
                    in_house = lon >= start or lon < end
                    
                if in_house:
                    house.planets_in_house.append(planet.name)
                    planet.house = house.number
                    break
        return houses

def get_house_strategy(house_system_code: str) -> HouseSystemStrategy:
    """Factory method to get the correct house strategy."""
    if house_system_code == "W":
        return WholeSignHouseSystem()
    elif house_system_code in ("E", "B"): # Equal or Bhava Chalit approximation
        return BhavaChalitHouseSystem()
    else: # P (Placidus), K (Koch/KP)
        return CuspHouseSystem()

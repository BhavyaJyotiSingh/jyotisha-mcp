import pytest
import json
import os
from pathlib import Path
from jyotisha.engines.chart import ChartEngine

GOLDEN_DIR = Path(__file__).parent / "golden_charts"

def get_golden_charts():
    if not GOLDEN_DIR.exists():
        return []
    return [f for f in GOLDEN_DIR.glob("*.json")]

@pytest.fixture
def chart_engine():
    return ChartEngine()

@pytest.mark.parametrize("json_file", get_golden_charts())
def test_golden_chart_json(chart_engine, json_file):
    """Data-driven test that loads 500+ golden charts in JSON format and validates them."""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Example JSON Structure:
    # {
    #   "name": "Mahatma Gandhi",
    #   "datetime_str": "1869-10-02T07:11:00",
    #   "latitude": 21.6422,
    #   "longitude": 69.6093,
    #   "expected_ascendant": "Libra",
    #   "expected_planets": {
    #       "Sun": "Virgo",
    #       "Moon": "Cancer"
    #   }
    # }
    
    chart = chart_engine.generate_birth_chart(
        datetime_str=data["datetime_str"],
        latitude=data["latitude"],
        longitude=data["longitude"],
        location_name=data.get("name")
    )
    
    if "expected_ascendant" in data:
        assert chart.ascendant.sign == data["expected_ascendant"], f"Ascendant mismatch in {data['name']}"
        
    if "expected_planets" in data:
        for p_name, expected_sign in data["expected_planets"].items():
            planet = chart.get_planet(p_name)
            assert planet is not None, f"Planet {p_name} missing in {data['name']}"
            assert planet.sign == expected_sign, f"{p_name} sign mismatch in {data['name']}"

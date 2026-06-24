import pytest
from jyotisha.engines.chart import ChartEngine
from jyotisha.engines.yoga import YogaEngine

@pytest.fixture
def dummy_chart():
    chart_engine = ChartEngine()
    return chart_engine.generate_birth_chart(
        datetime_str="1990-01-01T12:00:00",
        latitude=28.6139,
        longitude=77.2090,
        location_name="New Delhi"
    )

def test_yoga_engine_loads_rules():
    engine = YogaEngine()
    assert len(engine.rules) > 10

def test_yoga_detection_runs_successfully(dummy_chart):
    engine = YogaEngine()
    results = engine.detect_yogas(dummy_chart)
    # Check that it runs without errors and detects yogas
    assert isinstance(results, list)
    for r in results:
        assert r.name
        assert r.category
        assert r.conclusion

def test_custom_yoga_detection(dummy_chart):
    engine = YogaEngine()
    
    # Let's inspect some of the loaded rules to make sure they match expected names
    rule_names = [r["name"] for r in engine.rules]
    assert "Budhaditya Yoga" in rule_names
    assert "Durudhura Yoga" in rule_names
    assert "Viparita Raja Yoga (Sarala)" in rule_names
    assert "Viparita Raja Yoga (Vimala)" in rule_names
    assert "Saraswati Yoga" in rule_names
    assert "Dharma-Karma Adhipati Yoga" in rule_names
    assert "Lakshmi Yoga" in rule_names

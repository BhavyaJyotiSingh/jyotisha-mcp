import pytest
from jyotisha.engines.chart import ChartEngine
from jyotisha.engines.strength import PlanetaryStrengthEngine
from jyotisha.models.schemas import PlanetPosition, DignityInfo, Dignity

@pytest.fixture
def dummy_chart():
    chart_engine = ChartEngine()
    return chart_engine.generate_birth_chart(
        datetime_str="1990-01-01T12:00:00",
        latitude=28.6139,
        longitude=77.2090,
        location_name="New Delhi"
    )

def test_saptavargaja_bala(dummy_chart):
    engine = PlanetaryStrengthEngine()
    sun = dummy_chart.get_planet("Sun")
    score = engine._compute_saptavargaja_score("Sun", sun.sign_number, sun.degree_in_sign)
    assert score in [60.0, 45.0, 30.0, 15.0, 7.5, 3.75, 1.875]

def test_vimsopaka_bala(dummy_chart):
    engine = PlanetaryStrengthEngine()
    shadvarga = engine.compute_vimsopaka_bala(dummy_chart, scheme="Shadvarga")
    saptavarga = engine.compute_vimsopaka_bala(dummy_chart, scheme="Saptavarga")
    dashavarga = engine.compute_vimsopaka_bala(dummy_chart, scheme="Dashavarga")
    shodashavarga = engine.compute_vimsopaka_bala(dummy_chart, scheme="Shodashavarga")

    for name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
        assert 0.0 <= shadvarga[name] <= 20.0
        assert 0.0 <= saptavarga[name] <= 20.0
        assert 0.0 <= dashavarga[name] <= 20.0
        assert 0.0 <= shodashavarga[name] <= 20.0

def test_ishta_kashta_bala(dummy_chart):
    engine = PlanetaryStrengthEngine()
    for planet in dummy_chart.planets:
        if planet.name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
            ishta, kashta = engine.compute_ishta_kashta_bala(planet)
            assert 0.0 <= ishta <= 60.0
            assert 0.0 <= kashta <= 60.0

def test_avasthas(dummy_chart):
    engine = PlanetaryStrengthEngine()
    for planet in dummy_chart.planets:
        if planet.name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
            baladi = engine.compute_baladi_avastha(planet)
            assert baladi in ["Bala", "Kumara", "Yuva", "Vriddha", "Mrita"]
            
            jagradadi = engine.compute_jagradadi_avastha(planet)
            assert jagradadi in ["Jaagrat", "Swapna", "Sushupti"]
            
            deeptadi = engine.compute_deeptadi_avastha(planet, dummy_chart)
            assert deeptadi in ["Deepta", "Svastha", "Pramudita", "Shanta", "Dina", "Duhkhita", "Vikala", "Khala", "Kopa"]

def test_shadbala_integration(dummy_chart):
    engine = PlanetaryStrengthEngine()
    shadbala_results = engine.compute_shadbala(dummy_chart)
    for name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
        res = shadbala_results[name]
        assert res.planet == name
        assert res.sthana_bala > 0.0
        assert res.dig_bala >= 0.0
        assert res.kala_bala >= 0.0
        assert res.cheshta_bala >= 0.0
        assert res.naisargika_bala > 0.0
        assert res.drik_bala >= 0.0
        assert res.total_shadbala > 0.0
        assert res.shadbala_rupas == pytest.approx(res.total_shadbala / 60.0, abs=1e-2)
        assert res.is_sufficient == (res.shadbala_rupas >= res.required_rupas)

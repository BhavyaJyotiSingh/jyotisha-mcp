import pytest
from jyotisha.engines.chart import ChartEngine
from jyotisha.engines.ashtakavarga import AshtakavargaEngine

@pytest.fixture
def dummy_chart():
    chart_engine = ChartEngine()
    return chart_engine.generate_birth_chart(
        datetime_str="1990-01-01T12:00:00",
        latitude=28.6139,
        longitude=77.2090,
        location_name="New Delhi"
    )

def test_ashtakavarga_engine(dummy_chart):
    engine = AshtakavargaEngine()
    result = engine.compute_ashtakavarga(dummy_chart)
    
    # 7 planets BAV must exist
    assert len(result.bav) == 7
    # SAV must have 12 sign scores
    assert len(result.sav) == 12
    # Total SAV points in traditional system is 337
    assert sum(result.sav) == 337

def test_trikona_reduction():
    engine = AshtakavargaEngine()
    # Test equal values: should all become 0
    assert engine.trikona_shodhana([4, 1, 1, 1, 4, 1, 1, 1, 4, 1, 1, 1]) == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    
    # Test unequal values: subtract minimum
    # Aries: 5, Leo: 3, Sag: 4. Min is 3. Result: Aries: 2, Leo: 0, Sag: 1
    # Other triads all 0 to be simple
    bav = [0] * 12
    bav[0] = 5
    bav[4] = 3
    bav[8] = 4
    reduced = engine.trikona_shodhana(bav)
    assert reduced[0] == 2
    assert reduced[4] == 0
    assert reduced[8] == 1

def test_ekadhipatya_reduction(dummy_chart):
    engine = AshtakavargaEngine()
    # Let's verify that the dual lordship reduction runs without error
    result = engine.compute_ashtakavarga(dummy_chart)
    assert len(result.trikona_reduction) == 7
    assert len(result.ekadhipatya_reduction) == 7
    
    for planet in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
        # The reduced scores must be less than or equal to the trikona scores
        for sign in range(12):
            assert result.ekadhipatya_reduction[planet][sign] <= result.trikona_reduction[planet][sign]

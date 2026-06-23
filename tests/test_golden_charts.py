import pytest
from jyotisha.engines.chart import ChartEngine

@pytest.fixture
def chart_engine():
    return ChartEngine()

def test_gandhi_chart(chart_engine):
    """
    Mahatma Gandhi
    DOB: Oct 2, 1869
    Time: 07:11 AM LMT (Approx)
    Location: Porbandar, India (21.6422 N, 69.6093 E)
    """
    chart = chart_engine.generate_birth_chart(
        datetime_str="1869-10-02T07:11:00",
        latitude=21.6422,
        longitude=69.6093,
        location_name="Porbandar"
    )
    
    # Assertions based on standard Lahiri Ayanamsha for Gandhi
    assert chart.ascendant.sign in ["Virgo", "Libra"]  # Depending on exact LMT vs IST mapping
    
    sun = chart.get_planet("Sun")
    assert sun is not None
    assert sun.sign == "Virgo"
    
    moon = chart.get_planet("Moon")
    assert moon is not None
    assert moon.sign == "Cancer"
    
    jupiter = chart.get_planet("Jupiter")
    assert jupiter is not None
    assert jupiter.sign == "Aries"
    
def test_einstein_chart(chart_engine):
    """
    Albert Einstein
    DOB: Mar 14, 1879
    Time: 11:30 AM LMT
    Location: Ulm, Germany (48.3984 N, 9.9915 E)
    """
    chart = chart_engine.generate_birth_chart(
        datetime_str="1879-03-14T11:30:00",
        latitude=48.3984,
        longitude=9.9915,
        location_name="Ulm"
    )
    
    # Assertions based on standard Lahiri Ayanamsha for Einstein
    assert chart.ascendant.sign == "Gemini"
    
    sun = chart.get_planet("Sun")
    assert sun is not None
    assert sun.sign == "Pisces"
    
    moon = chart.get_planet("Moon")
    assert moon is not None
    assert moon.sign == "Scorpio"

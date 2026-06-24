import pytest
from jyotisha.engines.chart import ChartEngine
from jyotisha.schools.jaimini import JaiminiModule
from jyotisha.schools.kp import KPModule
from jyotisha.engines.dasha import DashaEngine
from jyotisha.constants import Planet, Sign

@pytest.fixture
def test_chart():
    chart_engine = ChartEngine()
    return chart_engine.generate_birth_chart(
        datetime_str="1995-10-15T10:30:00",
        latitude=13.0827,
        longitude=80.2707,
        location_name="Chennai"
    )

def test_jaimini_7_vs_8_karakas(test_chart):
    # Default 7 karakas
    jaimini_7 = JaiminiModule(use_8_karakas=False)
    karakas_7 = jaimini_7._compute_chara_karakas(test_chart)
    assert len(karakas_7) == 7
    assert "Pitrukaraka (PiK) - Father/Ancestors" not in karakas_7
    
    # 8 karakas
    jaimini_8 = JaiminiModule(use_8_karakas=True)
    karakas_8 = jaimini_8._compute_chara_karakas(test_chart)
    assert len(karakas_8) == 8
    assert "Pitrukaraka (PiK) - Father/Ancestors" in karakas_8
    
    # Check Atmakaraka exists in both and is consistent
    assert "Atmakaraka (AK) - Self/Soul" in karakas_7
    assert "Atmakaraka (AK) - Self/Soul" in karakas_8

def test_jaimini_karakamsa_swamsa(test_chart):
    jaimini = JaiminiModule()
    karakamsa = jaimini.compute_karakamsa(test_chart)
    assert "atmakaraka_planet" in karakamsa
    assert "karakamsa_sign" in karakamsa
    assert "swamsa_sign" in karakamsa
    assert karakamsa["karakamsa_sign"] == karakamsa["swamsa_sign"]

def test_narayana_dasha_calculation(test_chart):
    dasha_engine = DashaEngine()
    timeline = dasha_engine.compute_narayana_dasha(test_chart)
    assert timeline.system == "Narayana Dasha"
    assert len(timeline.timeline) == 12
    
    # Verify that all 12 signs are represented in the timeline
    signs_in_timeline = [p.lord for p in timeline.timeline]
    assert len(set(signs_in_timeline)) == 12
    for sign in ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]:
        assert sign in signs_in_timeline

def test_kp_house_significators(test_chart):
    kp = KPModule()
    planet_subs = kp._compute_all_sub_lords(test_chart)
    house_sig = kp._compute_house_significators(test_chart, planet_subs)
    
    # Verify we have significators for all 12 houses
    assert len(house_sig) == 12
    for h in range(1, 13):
        assert "A" in house_sig[h]
        assert "B" in house_sig[h]
        assert "C" in house_sig[h]
        assert "D" in house_sig[h]
        
        # Verify D contains the lord
        lord = test_chart.get_house_lord(h)
        if lord:
            assert lord in house_sig[h]["D"]

def test_kp_predictions(test_chart):
    kp = KPModule()
    
    # Test marriage promise
    res_marriage = kp.predict(test_chart, "marriage")
    assert res_marriage.school == kp.school_name
    assert res_marriage.confidence >= 0.0
    assert "favorable_houses_signified" in res_marriage.structured_data
    
    # Test career promise
    res_career = kp.predict(test_chart, "career")
    assert res_career.school == kp.school_name
    assert res_career.confidence >= 0.0
    
    # Test travel promise
    res_travel = kp.predict(test_chart, "travel")
    assert res_travel.school == kp.school_name
    assert res_travel.confidence >= 0.0

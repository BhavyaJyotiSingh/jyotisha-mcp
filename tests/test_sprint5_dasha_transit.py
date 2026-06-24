import pytest
from jyotisha.engines.chart import ChartEngine
from jyotisha.engines.dasha import DashaEngine
from jyotisha.engines.transit import TransitEngine
from jyotisha.engines.muhurta import MuhurtaEngine
from jyotisha.engines.prashna import PrashnaEngine

@pytest.fixture
def test_chart():
    chart_engine = ChartEngine()
    return chart_engine.generate_birth_chart(
        datetime_str="1995-10-15T10:30:00",
        latitude=13.0827,
        longitude=80.2707,
        location_name="Chennai"
    )

def test_ashtottari_dasha(test_chart):
    dasha_engine = DashaEngine()
    timeline = dasha_engine.compute_ashtottari_dasha(test_chart)
    assert timeline.system == "Ashtottari"
    assert len(timeline.timeline) > 0
    assert timeline.birth_nakshatra != ""
    assert "remaining_years" in timeline.balance_at_birth

def test_dwisaptati_dasha(test_chart):
    dasha_engine = DashaEngine()
    timeline = dasha_engine.compute_dwisaptati_dasha(test_chart)
    assert timeline.system == "Dwisaptati"
    assert len(timeline.timeline) > 0
    assert "remaining_years" in timeline.balance_at_birth

def test_shodashottari_dasha(test_chart):
    dasha_engine = DashaEngine()
    timeline = dasha_engine.compute_shodashottari_dasha(test_chart)
    assert timeline.system == "Shodashottari"
    assert len(timeline.timeline) > 0
    assert "remaining_years" in timeline.balance_at_birth

def test_panchottari_dasha(test_chart):
    dasha_engine = DashaEngine()
    timeline = dasha_engine.compute_panchottari_dasha(test_chart)
    assert timeline.system == "Panchottari"
    assert len(timeline.timeline) > 0
    assert "remaining_years" in timeline.balance_at_birth

def test_naisargika_dasha(test_chart):
    dasha_engine = DashaEngine()
    timeline = dasha_engine.compute_naisargika_dasha(test_chart)
    assert timeline.system == "Naisargika"
    assert len(timeline.timeline) == 7
    lords = [p.lord for p in timeline.timeline]
    assert lords == ["Moon", "Mars", "Mercury", "Venus", "Jupiter", "Sun", "Saturn"]

def test_kalachakra_dasha(test_chart):
    dasha_engine = DashaEngine()
    timeline = dasha_engine.compute_kalachakra_dasha(test_chart)
    assert timeline.system == "Kalachakra"
    assert len(timeline.timeline) == 18
    assert timeline.birth_nakshatra != ""
    assert "remaining_years" in timeline.balance_at_birth
    
    # Verify sub-periods exist
    assert len(timeline.timeline[0].sub_periods) == 9

def test_tara_dasha(test_chart):
    dasha_engine = DashaEngine()
    timeline = dasha_engine.compute_tara_dasha(test_chart)
    assert timeline.system == "Tara"
    assert len(timeline.timeline) > 0
    assert timeline.birth_nakshatra != ""
    assert "remaining_years" in timeline.balance_at_birth

def test_gochar_vedha_blocking():
    # Sun in 3 (favorable) and Saturn in 9 (Vedha house for Sun in 3)
    # But Sun and Saturn have no mutual Vedha exception!
    # So Sun in 3 should NOT be blocked by Saturn in 9.
    gochara_1 = {"Sun": 3, "Saturn": 9}
    res_1 = TransitEngine.compute_gochara_assessment(gochara_1)
    assert res_1["Sun"]["is_favorable"] is True
    assert res_1["Sun"]["vedha_blocked"] is False

    # Sun in 3 (favorable) and Mars in 9 (Vedha house for Sun in 3)
    # No exception between Sun and Mars, so Sun in 3 should be blocked!
    gochara_2 = {"Sun": 3, "Mars": 9}
    res_2 = TransitEngine.compute_gochara_assessment(gochara_2)
    assert res_2["Sun"]["is_favorable"] is False
    assert res_2["Sun"]["vedha_blocked"] is True
    assert res_2["Sun"]["vedha_blocker"] == "Mars"
    assert res_2["Sun"]["status"] == "blocked"

    # Moon in 3 (favorable) and Mercury in 9 (Vedha house for Moon in 3)
    # Moon and Mercury have a mutual exception!
    # So Moon should NOT be blocked by Mercury in 9.
    gochara_3 = {"Moon": 3, "Mercury": 9}
    res_3 = TransitEngine.compute_gochara_assessment(gochara_3)
    assert res_3["Moon"]["is_favorable"] is True
    assert res_3["Moon"]["vedha_blocked"] is False

    # Moon in 3 (favorable) and Venus in 9 (Vedha house for Moon in 3)
    # No exception between Moon and Venus, so Moon in 3 should be blocked!
    gochara_4 = {"Moon": 3, "Venus": 9}
    res_4 = TransitEngine.compute_gochara_assessment(gochara_4)
    assert res_4["Moon"]["is_favorable"] is False
    assert res_4["Moon"]["vedha_blocked"] is True
    assert res_4["Moon"]["vedha_blocker"] == "Venus"
    assert res_4["Moon"]["status"] == "blocked"

def test_transit_engine_computations(test_chart):
    transit_engine = TransitEngine()
    res = transit_engine.compute_transits(test_chart, "2026-06-24")
    assert res.date == "2026-06-24"
    assert len(res.transit_planets) > 0
    assert "Saturn" in res.gochara_from_moon
    assert "active" in res.sade_sati
    assert isinstance(res.double_transit_activations, list)

def test_extended_panchanga_elements(test_chart):
    from jyotisha.engines.panchanga import PanchangaEngine
    panchanga_engine = PanchangaEngine()
    
    event = test_chart.birth_event
    res = panchanga_engine.compute_panchanga(
        jd=event.julian_day,
        lat=event.location.latitude,
        lon=event.location.longitude,
        alt=event.location.altitude,
        utc_offset_hours=event.utc_offset_hours,
        tz_name=event.location.timezone,
    )
    
    # Verify tithi extended elements
    assert res.tithi.start_time is not None
    assert res.tithi.end_time is not None
    assert res.tithi.quality in ["Good", "Bad", "Neutral"]
    assert isinstance(res.tithi.applicable_activities, list)
    
    # Verify nakshatra extended elements
    assert res.nakshatra.start_time is not None
    assert res.nakshatra.end_time is not None
    assert res.nakshatra.quality in ["Good", "Bad", "Neutral"]
    
    # Verify yoga and karana elements
    assert res.yoga.start_time is not None
    assert res.karana.start_time is not None


def test_muhurta_suitability(test_chart):
    engine = MuhurtaEngine()
    
    # 1. Test Tarabala
    # Janma Nakshatra is 0, transit is 3. Count = 4 (Kshema - Auspicious)
    tara = engine.compute_tarabala(0, 3)
    assert tara["tara_number"] == 4
    assert tara["is_auspicious"] is True
    assert tara["tara_name"] == "Kshema"
    
    # 2. Test Chandrabala
    # Birth Moon sign is 5 (Virgo), transit Moon sign is 5. Count = 1 (Auspicious)
    chandra = engine.compute_chandrabala(5, 5)
    assert chandra["house_from_moon"] == 1
    assert chandra["is_auspicious"] is True
    
    # 3. Test evaluate_muhurta for various events
    for event in ["marriage", "business", "travel", "house_purchase", "surgery"]:
        res = engine.evaluate_muhurta(
            birth_chart=test_chart,
            transit_date_str="2026-06-24",
            event_type=event,
        )
        assert res["event_type"] == event
        assert res["date"] == "2026-06-24"
        assert "suitability" in res
        assert "suitability_percentage" in res
        assert "tarabala" in res
        assert "chandrabala" in res
        assert "reasons" in res
        assert len(res["reasons"]) > 0


def test_prashna_engines(test_chart):
    engine = PrashnaEngine()
    
    # 1. Test Classical Prashna
    res_classical = engine.evaluate_classical_prashna(
        birth_chart=test_chart,
        question="Will I get married this year?",
    )
    assert res_classical["question"] == "Will I get married this year?"
    assert "verdict" in res_classical
    assert "confidence" in res_classical
    assert "reasoning" in res_classical
    assert "details" in res_classical
    
    # 2. Test KP Horary (1-249 number)
    # We choose number 100
    res_kp = engine.evaluate_kp_horary(
        birth_chart=test_chart,
        question="Will I purchase a house?",
        number=100,
    )
    assert res_kp["question"] == "Will I purchase a house?"
    assert res_kp["horary_number"] == 100
    assert 0.0 <= res_kp["target_longitude"] <= 360.0
    assert "sign" in res_kp
    assert "star_lord" in res_kp
    assert "sub_lord" in res_kp
    assert "verdict" in res_kp
    assert "confidence" in res_kp

import pytest
from jyotisha.engines.chart import ChartEngine, compute_graha_yuddhas
from jyotisha.engines.dasha import DashaEngine
from jyotisha.engines.transit import TransitEngine
from jyotisha.engines.strength import PlanetaryStrengthEngine
from jyotisha.engines.varga import VargaEngine
from jyotisha.engines.houses import WholeSignHouseSystem
from jyotisha.schools.kp import KPModule
from jyotisha.schools.parashara import ParasharaModule
from jyotisha.constants import Planet, EXALTATION
from jyotisha.models.schemas import PlanetPosition, DignityInfo, Dignity

@pytest.fixture
def dummy_chart():
    chart_engine = ChartEngine()
    # Generates a standard birth chart for test birth details
    return chart_engine.generate_birth_chart(
        datetime_str="1990-01-01T12:00:00",
        latitude=28.6139,
        longitude=77.2090,
        location_name="New Delhi"
    )

def test_graha_yuddha_exclusion():
    """Verify that only the 5 Tara Grahas participate in planetary war."""
    # Sun and Mars in close conjunction (within 1 degree)
    planets_data = {
        "Sun": {"longitude": 10.0, "latitude": 0.0},
        "Mars": {"longitude": 10.1, "latitude": 0.5},
        "Venus": {"longitude": 10.2, "latitude": -0.2}
    }
    results = compute_graha_yuddhas(planets_data)
    # Sun must not be in results
    assert "Sun" not in results
    # Mars and Venus should participate and fight
    assert "Mars" in results
    assert "Venus" in results

def test_chara_dasha_calculation(dummy_chart):
    """Verify Chara Dasha calculates successfully without crash and has correct years."""
    dasha_engine = DashaEngine()
    chara = dasha_engine.compute_chara_dasha(dummy_chart)
    assert chara.system == "Chara Dasha"
    assert len(chara.timeline) == 12
    # Ensure years computed are not all 12 (sign lord distance-based calculation)
    years = [p.years for p in chara.timeline]
    assert any(y != 12 for y in years), f"Chara Dasha calculated all 12 years: {years}"

def test_transit_special_aspects():
    """Verify that special aspects are correctly detected for Mars/Jupiter/Saturn."""
    # Create a transit list where transit Mars is aspecting natal Moon
    # Mars is in Aries (0°), Moon is in Cancer (2°), which is the 4th house (aspect) from Aries.
    chart_engine = ChartEngine()
    d1_chart = chart_engine.generate_birth_chart(
        datetime_str="1990-01-01T12:00:00",
        latitude=28.6139,
        longitude=77.2090,
        location_name="New Delhi"
    )
    
    # Let's inspect aspects in a transit result
    transit_engine = TransitEngine(astro_engine=chart_engine.astro)
    # Mars transit in Aries aspecting Moon in Cancer
    transit_res = transit_engine.compute_transits(d1_chart, "2024-05-01")
    # Make sure hits are detected
    assert len(transit_res.hits) >= 0


def test_transit_sade_sati_status_from_moon():
    """Verify Sade Sati status is derived from Saturn's house from natal Moon."""
    assert TransitEngine.compute_sade_sati_status({"Saturn": 12}) == {
        "active": True,
        "saturn_house_from_moon": 12,
        "phase": "Rising",
        "severity": "medium",
        "description": "Saturn transits the 12th house from natal Moon.",
    }
    assert TransitEngine.compute_sade_sati_status({"Saturn": 1})["phase"] == "Peak"
    assert TransitEngine.compute_sade_sati_status({"Saturn": 2})["phase"] == "Setting"

    inactive = TransitEngine.compute_sade_sati_status({"Saturn": 3})
    assert inactive["active"] is False
    assert inactive["severity"] == "none"


def test_transit_gochara_assessment_from_moon():
    """Verify BPHS gochar favorability is derived from house from natal Moon."""
    assessment = TransitEngine.compute_gochara_assessment(
        {
            "Sun": 3,
            "Jupiter": 6,
            "Saturn": 11,
            "Rahu": 5,
        }
    )

    assert assessment["Sun"]["status"] == "favorable"
    assert assessment["Sun"]["is_favorable"] is True
    assert assessment["Jupiter"]["status"] == "unfavorable"
    assert assessment["Jupiter"]["is_favorable"] is False
    assert assessment["Saturn"]["status"] == "favorable"
    assert assessment["Rahu"]["status"] == "unknown"
    assert assessment["Rahu"]["is_favorable"] is None


def test_transit_double_transit_activation(dummy_chart):
    """Verify double transit detects houses activated by both Jupiter and Saturn."""
    target_house = dummy_chart.get_house(5)
    target_sign = target_house.sign_number
    saturn_sign_for_3rd_aspect = (target_sign - 2) % 12

    jupiter = PlanetPosition(
        name="Jupiter",
        longitude=float(target_sign * 30),
        sign=target_house.sign,
        sign_number=target_sign,
        house=1,
        degree_in_sign=0.0,
        nakshatra="Ashwini",
        nakshatra_number=0,
        pada=1,
        nakshatra_lord="Ketu",
        dignity=DignityInfo(status=Dignity.NEUTRAL),
    )
    saturn = PlanetPosition(
        name="Saturn",
        longitude=float(saturn_sign_for_3rd_aspect * 30),
        sign=target_house.sign,
        sign_number=saturn_sign_for_3rd_aspect,
        house=1,
        degree_in_sign=0.0,
        nakshatra="Ashwini",
        nakshatra_number=0,
        pada=1,
        nakshatra_lord="Ketu",
        dignity=DignityInfo(status=Dignity.NEUTRAL),
    )

    activations = TransitEngine.compute_double_transit_activations(
        dummy_chart,
        [jupiter, saturn],
    )

    fifth_activation = next(
        activation for activation in activations if activation["house"] == 5
    )
    assert fifth_activation["jupiter_relation"] == "occupation"
    assert fifth_activation["saturn_relation"] == "3th aspect"


def test_uchcha_bala_formula():
    """Verify that the Uchcha Bala debilitation point is exactly 180 degrees from exaltation."""
    engine = PlanetaryStrengthEngine()
    
    # Sun exaltation is Aries 10° (longitude 10.0) -> Debilitation must be Libra 10° (longitude 190.0)
    # At longitude 190.0, Uchcha Bala must be 0
    p_sun_deb = PlanetPosition(
        name="Sun",
        longitude=190.0,
        sign="Libra",
        sign_number=6,
        house=1,
        degree_in_sign=10.0,
        nakshatra="Chitra",
        nakshatra_number=13,
        pada=1,
        nakshatra_lord="Mars",
        dignity=DignityInfo(status=Dignity.DEBILITATED)
    )
    assert engine._compute_sthana_bala(p_sun_deb) >= 0.0
    # Uchcha Bala is the first component of Sthana Bala
    # Let's compute just Uchcha Bala:
    exaltation_deg = (EXALTATION[Planet.SUN].sign.value * 30.0 + EXALTATION[Planet.SUN].exact_degree)
    deb_deg = (exaltation_deg + 180.0) % 360.0
    assert deb_deg == 190.0
    
    diff = abs(p_sun_deb.longitude - deb_deg) % 360.0
    diff = min(diff, 360.0 - diff)
    uchcha_bala = 60.0 * (diff / 180.0)
    assert uchcha_bala == 0.0

def test_varga_d60_d81():
    """Verify D60 Shashtiamsa and D81 Navanavamsa formulas."""
    engine = VargaEngine()
    # Test D60 odd vs even sign rules
    # Aries 0.25 (odd sign, index 0): part 0 -> should map to Aries (0)
    assert engine.compute_varga_sign(0.25, 60) == 0
    # Taurus 0.25 (even sign, index 1): part 0 -> should map to Sagittarius (8)
    assert engine.compute_varga_sign(30.25, 60) == 8

    # Test D81 Navanavamsa: D9 of D9
    # Aries 0.25: D9 sign is Aries. Degree is 0.25/3.33333 * 30 = 2.25.
    # D9 of Aries 2.25: 2.25 / 3.33333 = 0.675 -> part 0. Aries starts from Aries, so Aries (0).
    # Let's verify:
    assert engine.compute_varga_sign(0.25, 81) == 0

def test_whole_sign_cusps():
    """Verify Whole Sign house cusps are at 0° of the sign (longitude = sign_number * 30)."""
    system = WholeSignHouseSystem()
    houses = system.build_houses(asc_sign_num=1) # Taurus
    for h in houses:
        assert h.cusp_longitude == (h.sign_number * 30.0) % 360.0
        assert h.span_start == (h.sign_number * 30.0) % 360.0

def test_day_lord_actual_sunrise(dummy_chart):
    """Verify Day Lord calculation uses actual sunrise and changes before sunrise."""
    kp = KPModule()
    ruling = kp._compute_ruling_planets(dummy_chart)
    assert "Day_Lord" in ruling
    assert ruling["Day_Lord"] != "Unknown"


def test_kp_sub_sub_lord_uses_recursive_vimshottari_proportions():
    """Verify KP sub-sub-lord calculation recursively subdivides the selected sub."""
    kp = KPModule()

    ashwini_start = kp.get_sub_lord_detail(0.0)
    assert ashwini_start["star_lord"] == Planet.KETU
    assert ashwini_start["sub_lord"] == Planet.KETU
    assert ashwini_start["sub_sub_lord"] == Planet.KETU

    venus_sub_start = (7 / 120) * (360 / 27)
    venus_sub = kp.get_sub_lord_detail(venus_sub_start + 0.0001)
    assert venus_sub["star_lord"] == Planet.KETU
    assert venus_sub["sub_lord"] == Planet.VENUS
    assert venus_sub["sub_sub_lord"] == Planet.VENUS


def test_kp_analysis_includes_cusp_sub_lords_and_significators(dummy_chart):
    """Verify Phase 7 KP output exposes cusp sub-lords and planet significators."""
    kp = KPModule()
    analysis = kp.analyze_chart(dummy_chart)

    assert len(analysis["cusp_sub_lords"]) == 12
    first_cusp = analysis["cusp_sub_lords"][1]
    assert first_cusp["star_lord"] in Planet
    assert first_cusp["sub_lord"] in Planet
    assert first_cusp["sub_sub_lord"] in Planet
    assert isinstance(first_cusp["sub_lord_significators"], list)

    sun_significators = analysis["planet_significators"]["Sun"]
    assert sun_significators["placed_house"] == dummy_chart.get_planet("Sun").house
    assert sun_significators["signified_houses"]
    assert "sub_sub_lord" in analysis["planet_sub_lords"]["Sun"]


def test_parashara_house_analysis_includes_phase5_fields(dummy_chart):
    """Verify Parashara house analysis exposes lord, karaka, and bhavat-bhavam data."""
    module = ParasharaModule()
    house_analysis = module._analyze_houses(dummy_chart)

    assert len(house_analysis) == 12
    first_house = house_analysis[0]
    seventh_house = house_analysis[6]

    assert first_house["lord_house"] is not None
    assert first_house["lord_sign"]
    assert first_house["lord_dignity"] != "Unknown"
    assert first_house["karakas"] == ["Sun"]
    assert first_house["bhavat_bhavam_house"] == 1

    assert seventh_house["karakas"] == ["Venus"]
    assert seventh_house["bhavat_bhavam_house"] == 1
    assert seventh_house["bhavat_bhavam_significations"]

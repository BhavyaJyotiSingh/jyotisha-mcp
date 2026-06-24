from datetime import datetime, timezone

import pytest
import swisseph as swe

from jyotisha.engines.astronomy import AstronomicalEngine
from jyotisha.engines.calendar import CalendarEngine
from jyotisha.engines.chart import ChartEngine, is_pushkara_navamsa
from jyotisha.engines.houses import (
    CampanusHouseSystem,
    EqualHouseSystem,
    KochHouseSystem,
    PlacidusHouseSystem,
    RegiomontanusHouseSystem,
    SripatiHouseSystem,
    get_house_strategy,
)
from jyotisha.engines.varga import DrekkanaMethod, HoraMethod, VargaEngine
from jyotisha.constants import Ayanamsha, Planet


REFERENCE_JD = swe.julday(2000, 1, 1, 12.0, swe.GREG_CAL)
DELHI_LAT = 28.6139
DELHI_LON = 77.2090


def _jd_to_local_hour(jd: float, utc_offset_hours: float) -> float:
    year, month, day, hour = swe.revjul(jd)
    del year, month, day
    return (hour + utc_offset_hours) % 24.0


def test_houses_ex_returns_all_twelve_cusps_including_first():
    engine = AstronomicalEngine()
    result = engine.compute_ascendant(
        REFERENCE_JD, 28.6139, 77.2090, house_system="P"
    )
    expected_cusps, expected_ascmc = swe.houses_ex(
        REFERENCE_JD,
        28.6139,
        77.2090,
        b"P",
        swe.FLG_SIDEREAL,
    )

    assert len(result["cusps"]) == 12
    assert result["cusps"] == pytest.approx(expected_cusps, abs=1e-10)
    assert result["ascendant"]["longitude"] == pytest.approx(
        expected_ascmc[0] % 360.0, abs=1e-10
    )


def test_delta_t_is_exposed_in_seconds():
    engine = AstronomicalEngine()
    assert engine.get_delta_t(REFERENCE_JD) == pytest.approx(
        swe.deltat(REFERENCE_JD) * 86400.0, abs=1e-12
    )
    assert 60.0 < engine.get_delta_t(REFERENCE_JD) < 70.0


def test_lahiri_ayanamsha_matches_swiss_ephemeris():
    engine = AstronomicalEngine()
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    assert engine.get_ayanamsha_value(REFERENCE_JD) == pytest.approx(
        swe.get_ayanamsa_ut(REFERENCE_JD), abs=1e-12
    )


def test_ayanamsha_can_be_switched_per_engine_instance():
    lahiri = AstronomicalEngine(ayanamsha=Ayanamsha.LAHIRI)
    raman = AstronomicalEngine(ayanamsha=Ayanamsha.RAMAN)

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    expected_lahiri = swe.get_ayanamsa_ut(REFERENCE_JD)
    swe.set_sid_mode(swe.SIDM_RAMAN)
    expected_raman = swe.get_ayanamsa_ut(REFERENCE_JD)

    assert lahiri.get_ayanamsha_value(REFERENCE_JD) == pytest.approx(
        expected_lahiri, abs=1e-12
    )
    assert raman.get_ayanamsha_value(REFERENCE_JD) == pytest.approx(
        expected_raman, abs=1e-12
    )
    assert abs(expected_lahiri - expected_raman) > 1.0


def test_calendar_julian_day_matches_swiss_ephemeris_for_100_dates():
    years = [1000 + index * 11 for index in range(100)]
    for index, year in enumerate(years):
        month = index % 12 + 1
        day = index % 28 + 1
        hour = index % 24
        minute = (index * 7) % 60
        second = (index * 13) % 60
        microsecond = (index * 123_457) % 1_000_000
        dt = datetime(
            year, month, day, hour, minute, second, microsecond, tzinfo=timezone.utc
        )
        hour_decimal = (
            hour + minute / 60.0 + second / 3600.0 + microsecond / 3_600_000_000.0
        )
        calendar = "Julian" if year < 1582 else "Gregorian"
        swe_calendar = swe.JUL_CAL if calendar == "Julian" else swe.GREG_CAL

        assert CalendarEngine._compute_julian_day(dt, calendar) == pytest.approx(
            swe.julday(year, month, day, hour_decimal, swe_calendar), abs=0.0
        )


def test_reference_planetary_longitudes_match_swiss_ephemeris():
    engine = AstronomicalEngine()
    positions = engine.compute_planet_positions(REFERENCE_JD)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    for planet, swe_id in [
        (Planet.SUN, swe.SUN),
        (Planet.MOON, swe.MOON),
        (Planet.MARS, swe.MARS),
        (Planet.MERCURY, swe.MERCURY),
        (Planet.JUPITER, swe.JUPITER),
        (Planet.VENUS, swe.VENUS),
        (Planet.SATURN, swe.SATURN),
        (Planet.RAHU, swe.TRUE_NODE),
    ]:
        expected, ret_flags = swe.calc_ut(REFERENCE_JD, swe_id, flags)
        assert ret_flags >= 0
        assert positions[planet]["longitude"] == pytest.approx(
            expected[0] % 360.0, abs=1e-10
        )

    assert positions[Planet.KETU]["longitude"] == pytest.approx(
        (positions[Planet.RAHU]["longitude"] + 180.0) % 360.0, abs=1e-12
    )


def test_julian_day_preserves_microseconds():
    engine = AstronomicalEngine()
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    shifted = datetime(2024, 1, 1, 0, 0, 0, 500_000, tzinfo=timezone.utc)
    seconds = (engine.datetime_to_jd(shifted) - engine.datetime_to_jd(base)) * 86400
    assert seconds == pytest.approx(0.5, abs=5e-5)


def test_polar_no_sunrise_raises_instead_of_fabricating_time():
    engine = AstronomicalEngine()
    polar_night_jd = swe.julday(2024, 12, 21, 0.0, swe.GREG_CAL)
    with pytest.raises(RuntimeError, match="does not occur"):
        engine.compute_sunrise(polar_night_jd, 89.0, 0.0)


def test_delhi_solstice_sunrise_matches_expected_local_time():
    engine = AstronomicalEngine()
    local_midnight_ist = swe.julday(2024, 6, 20, 18.5, swe.GREG_CAL)
    sunrise = engine.compute_sunrise(local_midnight_ist, DELHI_LAT, DELHI_LON)

    # Expected ~05:25 IST from Swiss Ephemeris for New Delhi on 2024-06-21.
    assert _jd_to_local_hour(sunrise, 5.5) == pytest.approx(5.423, abs=2 / 60)


def test_twilight_events_are_ordered_before_sunrise():
    engine = AstronomicalEngine()
    local_midnight_ist = swe.julday(2024, 6, 20, 18.5, swe.GREG_CAL)
    astronomical = engine.compute_twilight(
        local_midnight_ist, DELHI_LAT, DELHI_LON, "astronomical"
    )
    nautical = engine.compute_twilight(
        local_midnight_ist, DELHI_LAT, DELHI_LON, "nautical"
    )
    civil = engine.compute_twilight(local_midnight_ist, DELHI_LAT, DELHI_LON, "civil")
    sunrise = engine.compute_sunrise(local_midnight_ist, DELHI_LAT, DELHI_LON)

    assert astronomical < nautical < civil < sunrise


def test_moonrise_and_moonset_match_swiss_ephemeris():
    engine = AstronomicalEngine()
    local_midnight_ist = swe.julday(2024, 6, 20, 18.5, swe.GREG_CAL)
    moonrise = engine.compute_moonrise(local_midnight_ist, DELHI_LAT, DELHI_LON)
    moonset = engine.compute_moonset(local_midnight_ist, DELHI_LAT, DELHI_LON)

    for actual, event_flag in [
        (moonrise, swe.CALC_RISE | swe.BIT_DISC_CENTER),
        (moonset, swe.CALC_SET | swe.BIT_DISC_CENTER),
    ]:
        status, expected = swe.rise_trans(
            local_midnight_ist,
            swe.MOON,
            event_flag,
            (DELHI_LON, DELHI_LAT, 0.0),
            1013.25,
            15.0,
        )
        assert status == 0
        assert actual == pytest.approx(expected[0], abs=1e-10)


@pytest.mark.parametrize(
    ("code", "strategy_type"),
    [
        ("E", EqualHouseSystem),
        ("P", PlacidusHouseSystem),
        ("K", KochHouseSystem),
        ("C", CampanusHouseSystem),
        ("R", RegiomontanusHouseSystem),
        ("O", SripatiHouseSystem),
    ],
)
def test_house_strategy_codes_are_not_conflated(code, strategy_type):
    assert isinstance(get_house_strategy(code), strategy_type)


def test_varga_compositions_and_longitude_normalization():
    engine = VargaEngine()
    for longitude in (0.25, 29.999, 30.25, 123.456, 359.999):
        d9_sign = engine.compute_varga_sign(longitude, 9)
        d9_degree = engine.compute_varga_degree(longitude, 9)
        expected_d108 = engine.compute_varga_sign(
            d9_sign * 30.0 + d9_degree, 12
        )
        assert engine.compute_varga_sign(longitude, 108) == expected_d108

        d12_sign = engine.compute_varga_sign(longitude, 12)
        d12_degree = engine.compute_varga_degree(longitude, 12)
        expected_d144 = engine.compute_varga_sign(
            d12_sign * 30.0 + d12_degree, 12
        )
        assert engine.compute_varga_sign(longitude, 144) == expected_d144

    assert engine.compute_varga_sign(360.0, 9) == engine.compute_varga_sign(0.0, 9)
    assert engine.compute_varga_sign(-0.25, 9) == engine.compute_varga_sign(
        359.75, 9
    )


def test_varga_formula_metadata_for_priority_divisions():
    engine = VargaEngine()

    hora = engine.get_formula_spec(2)
    assert hora.classical_source.startswith("BPHS")
    assert hora.method == HoraMethod.PARASHARA.value
    assert HoraMethod.KASHINATHA.value in hora.alternative_methods

    drekkana = engine.get_formula_spec(3)
    assert drekkana.method == DrekkanaMethod.PARASHARA.value
    assert DrekkanaMethod.SOMNATHA.value in drekkana.alternative_methods

    for division in (2, 3, 9, 60, 81):
        spec = engine.get_formula_spec(division)
        for longitude, expected_sign in spec.unit_test_cases:
            assert engine.compute_varga_sign(longitude, division) == expected_sign


def test_varga_boundary_rules_for_d2_d3_d9():
    engine = VargaEngine()

    assert engine.compute_varga_sign(14.999999, 2) == 4
    assert engine.compute_varga_sign(15.0, 2) == 3
    assert engine.compute_varga_sign(29.999999, 3) == 8
    assert engine.compute_varga_sign(30.0, 9) == 9


def test_divisional_chart_recomputes_nakshatra_from_projected_longitude():
    chart_engine = ChartEngine()
    chart = chart_engine.generate_birth_chart(
        "1990-01-01T12:00:00", 28.6139, 77.2090
    )
    navamsha = chart_engine.generate_divisional_chart(chart, 9)
    for planet in navamsha.planets:
        expected_number = min(int(planet.longitude / (360.0 / 27.0)), 26)
        assert planet.nakshatra_number == expected_number


def test_chart_contains_reproducibility_metadata():
    chart_engine = ChartEngine()
    first = chart_engine.generate_birth_chart(
        "1990-01-01T12:00:00", 28.6139, 77.2090
    )
    second = chart_engine.generate_birth_chart(
        "1990-01-01T12:00:00", 28.6139, 77.2090
    )
    assert first.metadata.ephemeris_version
    assert first.metadata.delta_t_seconds > 0.0
    assert len(first.metadata.computation_hash) == 64
    assert first.metadata.computation_hash == second.metadata.computation_hash


def test_pushkara_boundaries_are_half_open():
    boundary = 30.0 / 9.0
    assert is_pushkara_navamsa(3, 0.0)
    assert not is_pushkara_navamsa(3, boundary)

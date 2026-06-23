import json
from jyotisha.engines.chart import ChartEngine
from jyotisha.engines.dasha import DashaEngine
from jyotisha.engines.yoga import YogaEngine
from jyotisha.engines.special import SpecialPointsEngine
from jyotisha.engines.consensus import ConsensusEngine
from jyotisha.engines.strength import PlanetaryStrengthEngine
from jyotisha.engines.ashtakavarga import AshtakavargaEngine
from jyotisha.engines.panchanga import PanchangaEngine
from jyotisha.engines.transit import TransitEngine
from jyotisha.schools.parashara import ParasharaModule
from jyotisha.schools.jaimini import JaiminiModule
from jyotisha.schools.kp import KPModule

def run_validations():
    print("--- Testing Engines ---")
    
    # 1. Chart Engine (which internally tests Calendar & Astronomy)
    print("1. Instantiating Chart Engine...")
    chart_engine = ChartEngine()
    
    print("   Generating Birth Chart...")
    chart = chart_engine.generate_birth_chart(
        datetime_str="1990-01-01T12:00:00",
        latitude=28.6139,
        longitude=77.2090,
        location_name="New Delhi"
    )
    print(f"   Success! Ascendant: {chart.ascendant.sign}")
    
    # Verify planetary war and Pushkara Navamsha fields exist and work
    print("   Checking new chart fields...")
    for p in chart.planets:
        print(f"      - {p.name}: Pushkara Navamsha={p.pushkara_navamsa}, Planetary War={p.planetary_war}")

    # Test new divisional charts (D5, D6, D8, D11, D40, D45)
    new_vargas = [5, 6, 8, 11, 40, 45]
    for v in new_vargas:
        print(f"   Generating divisional chart D{v}...")
        varga_chart = chart_engine.generate_divisional_chart(chart, division=v)
        print(f"      D{v} Success! Ascendant: {varga_chart.ascendant.sign}")
        for p in varga_chart.planets[:3]:
            print(f"         Planet {p.name} in {p.sign} (House {p.house})")

    # 2. Dasha Engine
    print("\n2. Instantiating Dasha Engine...")
    dasha_engine = DashaEngine()
    print("   Computing Vimshottari from Chart...")
    vimshottari = dasha_engine.compute_vimshottari_from_chart(chart)
    print(f"   Success! Active Dashas built. First Mahadasha: {vimshottari.timeline[0].lord}")
    
    print("   Computing Yogini from Chart...")
    yogini = dasha_engine.compute_yogini_dasha(chart)
    print(f"   Success! First Yogini Dasha: {yogini.timeline[0].lord}")

    print("   Computing Chara from Chart...")
    chara = dasha_engine.compute_chara_dasha(chart)
    print(f"   Success! First Chara Dasha: {chara.timeline[0].lord} ({chara.timeline[0].years} years)")
    
    # 3. Yoga Engine
    print("\n3. Instantiating Yoga Engine...")
    yoga_engine = YogaEngine()
    
    print("   Detecting Yogas...")
    yogas = yoga_engine.detect_yogas(chart)
    print(f"   Success! Detected {len(yogas)} Yogas.")
    
    # 4. Strength Engine (Shadbala)
    print("\n4. Instantiating Shadbala Strength Engine...")
    strength_engine = PlanetaryStrengthEngine()
    strengths = strength_engine.compute_shadbala(chart)
    print(f"   Success! Shadbala calculated for {len(strengths)} planets:")
    for name, sb in strengths.items():
        print(f"      - {name}: Total={sb.total_shadbala} Shashtiamsas ({sb.shadbala_rupas} Rupas), Sufficient={sb.is_sufficient}")

    # 4b. Ashtakavarga Engine
    print("\n4b. Instantiating Ashtakavarga Engine...")
    av_engine = AshtakavargaEngine()
    av_result = av_engine.compute_ashtakavarga(chart)
    sav_total = sum(av_result.sav)
    print(f"   Success! SAV computed. Total Bindus = {sav_total} (Expected ~337)")
    print(f"   SAV distribution: {av_result.sav}")

    # 5. Panchanga Engine
    print("\n5. Instantiating Daily Panchanga Engine...")
    panchanga_engine = PanchangaEngine(astro_engine=chart_engine.astro)
    event = chart.birth_event
    panchanga = panchanga_engine.compute_panchanga(
        jd=event.julian_day,
        lat=event.location.latitude,
        lon=event.location.longitude,
        alt=event.location.altitude,
        utc_offset_hours=event.utc_offset_hours,
        tz_name=event.location.timezone
    )
    print(f"   Success! Daily Panchanga elements computed:")
    print(f"      Date: {panchanga.date}")
    print(f"      Tithi: {panchanga.tithi.name} (Paksha: {panchanga.paksha})")
    print(f"      Vara: {panchanga.vara} (Lord: {panchanga.vara_lord})")
    print(f"      Nakshatra: {panchanga.nakshatra.name}")
    print(f"      Yoga: {panchanga.yoga.name}")
    print(f"      Karana: {panchanga.karana.name}")
    print(f"      Sunrise: {panchanga.sunrise}, Sunset: {panchanga.sunset}")

    # 6. Special Points & Upagrahas Engine
    print("\n6. Instantiating Special Points Engine...")
    special_engine = SpecialPointsEngine(astro_engine=chart_engine.astro)
    
    # Get local sunrise/sunset for upagrahas
    midnight_jd = chart_engine.astro.datetime_to_jd(
        event.datetime_utc.replace(hour=0, minute=0, second=0)
    )
    sunrise_jd = chart_engine.astro.compute_sunrise(midnight_jd, event.location.latitude, event.location.longitude)
    sunset_jd = chart_engine.astro.compute_sunset(midnight_jd, event.location.latitude, event.location.longitude)

    print("   Computing Special Lagnas...")
    lagnas = special_engine.compute_special_lagnas(chart, sunrise_jd=sunrise_jd)
    print(f"      Success! Generated {len(lagnas)} Lagnas:")
    for l in lagnas:
        print(f"         - {l.type} Lagna: {l.sign} {l.degree}°")

    print("   Computing Upagrahas...")
    upagrahas = special_engine.compute_upagrahas(chart, sunrise_jd=sunrise_jd, sunset_jd=sunset_jd)
    print(f"      Success! Generated {len(upagrahas)} Upagrahas:")
    for u in upagrahas:
        print(f"         - {u.name}: {u.sign} {u.degree}°")

    # 7. Consensus Engine
    print("\n7. Instantiating Consensus Engine...")
    consensus = ConsensusEngine()
    prediction = consensus.generate_consensus(chart, "marriage")
    print(f"   Success! Consensus Answer: {prediction.consensus_answer} (Confidence: {prediction.consensus_confidence})")
    print("   Explanations:")
    print(prediction.explanation)

    # 8. Transit Engine
    print("\n8. Instantiating Transit Engine...")
    transit_engine = TransitEngine(astro_engine=chart_engine.astro)
    transit_res = transit_engine.compute_transits(chart, "2024-01-01")
    print(f"   Success! Transits computed for 2024-01-01.")
    print(f"      Jupiter Gochar from Moon: {transit_res.gochara_from_moon.get('Jupiter')}")
    print(f"      Saturn Gochar from Moon: {transit_res.gochara_from_moon.get('Saturn')}")
    print(f"      Exact Hits (orb <= 1°): {[h.transit_planet + ' to ' + h.natal_point for h in transit_res.hits if h.is_exact]}")

    print("\n--- ALL TESTS PASSED SUCCESSFULLY ---")

if __name__ == "__main__":
    run_validations()

import json
from jyotisha.engines.chart import ChartEngine
from jyotisha.engines.dasha import DashaEngine
from jyotisha.engines.yoga import YogaEngine
from jyotisha.engines.special import SpecialPointsEngine
from jyotisha.engines.consensus import ConsensusEngine
from jyotisha.schools.parashara import ParasharaModule
from jyotisha.schools.jaimini import JaiminiModule
from jyotisha.schools.kp import KPModule

def run_validations():
    print("--- Testing Engines ---")
    
    # 1. Chart Engine (which internally tests Calendar & Astronomy)
    print("1. Instantiating Chart Engine...")
    chart_engine = ChartEngine()
    
    print("   Generating Birth Chart (mock data)...")
    chart = chart_engine.generate_birth_chart(
        datetime_str="1990-01-01T12:00:00",
        latitude=28.6139,
        longitude=77.2090,
        location_name="New Delhi"
    )
    print(f"   Success! Ascendant: {chart.ascendant.sign}")
    
    # 2. Dasha Engine
    print("\n2. Instantiating Dasha Engine...")
    dasha_engine = DashaEngine()
    
    print("   Computing Vimshottari from Chart...")
    timeline = dasha_engine.compute_vimshottari_from_chart(chart, levels=2)
    print(f"   Success! Active Dashas built. First Mahadasha: {timeline.timeline[0].lord}")
    
    print("   Getting current dasha for 2026-06-23...")
    # JD for 2026-06-23 (approx)
    jd_2026 = dasha_engine._date_to_jd("2026-06-23")
    current_dasha = dasha_engine.get_current_dasha(timeline, jd_2026)
    print(f"   Success! Current Dasha: {current_dasha}")
    
    # 3. Yoga Engine
    print("\n3. Instantiating Yoga Engine...")
    yoga_engine = YogaEngine()
    
    print("   Detecting Yogas...")
    yogas = yoga_engine.detect_yogas(chart)
    print(f"   Success! Detected {len(yogas)} Yogas.")
    for y in yogas:
        print(f"      - {y.name} ({y.category})")
        
    # 4. Special Points Engine
    print("\n4. Instantiating Special Points Engine...")
    special_engine = SpecialPointsEngine()
    
    print("   Computing Special Lagnas...")
    lagnas = special_engine.compute_special_lagnas(chart, sunrise_jd=chart.birth_event.julian_day - 0.25)
    print(f"   Success! Generated {len(lagnas)} Lagnas: {[l.type for l in lagnas]}")
    
    # 5. Schools
    print("\n5. Testing School Modules...")
    
    p_mod = ParasharaModule()
    p_res = p_mod.analyze_chart(chart)
    print(f"   Parashara output has {len(p_res['house_analysis'])} houses analyzed.")
    
    j_mod = JaiminiModule()
    j_res = j_mod.analyze_chart(chart)
    print(f"   Jaimini output has {len(j_res['chara_karakas'])} Karakas and {len(j_res['arudha_padas'])} Arudhas.")
    
    k_mod = KPModule()
    k_res = k_mod.analyze_chart(chart)
    print(f"   KP output has {len(k_res['planet_sub_lords'])} planet sub-lords computed.")
    
    # 6. Consensus Engine
    print("\n6. Instantiating Consensus Engine...")
    consensus = ConsensusEngine()
    print("   Generating Consensus for 'marriage'...")
    cons_res = consensus.generate_consensus(chart, "marriage")
    print(f"   Success! Conclusion: {cons_res.consensus_answer} (Confidence: {cons_res.consensus_confidence})")
    
    print("\n--- ALL TESTS PASSED SUCCESSFULLY ---")

if __name__ == "__main__":
    run_validations()

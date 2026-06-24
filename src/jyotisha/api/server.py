"""
MCP Server Entrypoint

Exposes Jyotisha engines as MCP tools using FastMCP.
"""

from typing import Optional
import json
from datetime import datetime, timedelta, timezone
from mcp.server.fastmcp import FastMCP

from jyotisha.engines.chart import ChartEngine
from jyotisha.engines.dasha import DashaEngine
from jyotisha.engines.transit import TransitEngine
from jyotisha.schools.parashara import ParasharaModule
from jyotisha.schools.jaimini import JaiminiModule
from jyotisha.schools.kp import KPModule
from jyotisha.engines.consensus import ConsensusEngine
from jyotisha.engines.strength import PlanetaryStrengthEngine
from jyotisha.engines.panchanga import PanchangaEngine
from jyotisha.engines.special import SpecialPointsEngine
from jyotisha.engines.muhurta import MuhurtaEngine
from jyotisha.engines.prashna import PrashnaEngine
from jyotisha.rag.retriever import JyotishaRetriever, HAS_CHROMA
from jyotisha.constants import Ayanamsha
from jyotisha.db.database import init_db

# Initialize database schema
init_db()

# Initialize MCP Server
mcp = FastMCP("jyotisha")

# Initialize Engines
chart_engine = ChartEngine(ayanamsha=Ayanamsha.LAHIRI)
dasha_engine = DashaEngine()
transit_engine = TransitEngine()
parashara_module = ParasharaModule()
jaimini_module = JaiminiModule()
kp_module = KPModule()
consensus_engine = ConsensusEngine()
strength_engine = PlanetaryStrengthEngine()
panchanga_engine = PanchangaEngine(astro_engine=chart_engine.astro)
special_engine = SpecialPointsEngine(astro_engine=chart_engine.astro)
muhurta_engine = MuhurtaEngine(chart_engine=chart_engine)
prashna_engine = PrashnaEngine(chart_engine=chart_engine, kp_module=kp_module)

rag_retriever = None
if HAS_CHROMA:
    rag_retriever = JyotishaRetriever()


@mcp.tool()
async def get_birth_chart(
    datetime_str: str,
    latitude: float,
    longitude: float,
    time_str: Optional[str] = None,
    location_name: Optional[str] = None,
) -> str:
    """
    Generate a complete Vedic birth chart (D1/Rashi).

    Args:
        datetime_str: Date in "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SS"
        latitude: Geographic latitude
        longitude: Geographic longitude
        time_str: Optional time in "HH:MM" (if not in datetime_str)
        location_name: Optional place name

    Returns:
        JSON string containing the complete chart data.
    """
    try:
        chart = chart_engine.generate_birth_chart(
            datetime_str=datetime_str,
            latitude=latitude,
            longitude=longitude,
            time_str=time_str,
            location_name=location_name,
        )
        return chart.model_dump_json(indent=2)
    except Exception as e:
        return f"Error generating chart: {e}"


@mcp.tool()
async def get_dasha_timeline(
    datetime_str: str,
    latitude: float,
    longitude: float,
    levels: int = 2,
    system: str = "Vimshottari",
) -> str:
    """
    Generate a Dasha timeline.

    Args:
        datetime_str: ISO Date/Time
        latitude: Latitude
        longitude: Longitude
        levels: Depth of periods
        system: Dasha system name ("Vimshottari", "Yogini", "Chara", "Narayana", "Ashtottari", "Dwisaptati", "Shodashottari", "Panchottari", "Naisargika", "Kalachakra", "Tara")

    Returns:
        JSON string containing the Dasha timeline.
    """
    try:
        chart = chart_engine.generate_birth_chart(
            datetime_str=datetime_str,
            latitude=latitude,
            longitude=longitude,
        )
        sys_lower = system.lower()
        if sys_lower == "yogini":
            timeline = dasha_engine.compute_yogini_dasha(chart)
        elif sys_lower == "chara":
            timeline = dasha_engine.compute_chara_dasha(chart)
        elif sys_lower == "narayana":
            timeline = dasha_engine.compute_narayana_dasha(chart)
        elif sys_lower == "ashtottari":
            timeline = dasha_engine.compute_ashtottari_dasha(chart, levels=levels)
        elif sys_lower == "dwisaptati":
            timeline = dasha_engine.compute_dwisaptati_dasha(chart, levels=levels)
        elif sys_lower == "shodashottari":
            timeline = dasha_engine.compute_shodashottari_dasha(chart, levels=levels)
        elif sys_lower == "panchottari":
            timeline = dasha_engine.compute_panchottari_dasha(chart, levels=levels)
        elif sys_lower == "naisargika":
            timeline = dasha_engine.compute_naisargika_dasha(chart)
        elif sys_lower == "kalachakra":
            timeline = dasha_engine.compute_kalachakra_dasha(chart, levels=levels)
        elif sys_lower == "tara":
            timeline = dasha_engine.compute_tara_dasha(chart, levels=levels)
        else:
            timeline = dasha_engine.compute_vimshottari_from_chart(chart, levels=levels)
        return timeline.model_dump_json(indent=2)
    except Exception as e:
        return f"Error generating dashas: {e}"


@mcp.tool()
async def get_current_dasha(
    birth_datetime: str,
    latitude: float,
    longitude: float,
    query_date: str,
) -> str:
    """
    Find the currently active dasha period for a specific date.

    Args:
        birth_datetime: Birth ISO Date/Time
        latitude: Birth Latitude
        longitude: Birth Longitude
        query_date: Date to check in "YYYY-MM-DD" format
    """
    try:
        chart = chart_engine.generate_birth_chart(
            datetime_str=birth_datetime,
            latitude=latitude,
            longitude=longitude,
        )
        timeline = dasha_engine.compute_vimshottari_from_chart(chart, levels=3)
        
        from jyotisha.engines.dasha import DashaEngine
        query_jd = DashaEngine._date_to_jd(query_date)
        current = dasha_engine.get_current_dasha(timeline, query_jd)
        
        return json.dumps(current, indent=2)
    except Exception as e:
        return f"Error finding current dasha: {e}"


@mcp.tool()
async def run_parashara_analysis(
    datetime_str: str,
    latitude: float,
    longitude: float,
    time_str: Optional[str] = None,
    location_name: Optional[str] = None,
) -> str:
    """
    Run a full Parashara school analysis on a birth chart.
    Returns Yogas, House Analysis, and Current Dasha overview.
    """
    try:
        chart = chart_engine.generate_birth_chart(
            datetime_str=datetime_str,
            latitude=latitude,
            longitude=longitude,
            time_str=time_str,
            location_name=location_name,
        )
        report = parashara_module.analyze_chart(chart)
        return json.dumps(report, indent=2)
    except Exception as e:
        return f"Error running Parashara analysis: {e}"


@mcp.tool()
async def run_jaimini_analysis(
    datetime_str: str,
    latitude: float,
    longitude: float,
    time_str: Optional[str] = None,
    location_name: Optional[str] = None,
    use_8_karakas: Optional[bool] = None,
) -> str:
    """
    Run a full Jaimini school analysis on a birth chart.
    Returns Chara Karakas, Rashi Drishti, Arudha Padas, and Karakamsa/Swamsa.
    """
    try:
        chart = chart_engine.generate_birth_chart(
            datetime_str=datetime_str,
            latitude=latitude,
            longitude=longitude,
            time_str=time_str,
            location_name=location_name,
        )
        report = jaimini_module.analyze_chart(chart, use_8_karakas=use_8_karakas)
        return json.dumps(report, indent=2)
    except Exception as e:
        return f"Error running Jaimini analysis: {e}"


@mcp.tool()
async def run_kp_analysis(
    datetime_str: str,
    latitude: float,
    longitude: float,
    time_str: Optional[str] = None,
    location_name: Optional[str] = None,
) -> str:
    """
    Run Krishnamurti Paddhati (KP) analysis on a birth chart.
    Returns Star Lords, Sub Lords, and Ruling Planets.
    """
    try:
        chart = chart_engine.generate_birth_chart(
            datetime_str=datetime_str,
            latitude=latitude,
            longitude=longitude,
            time_str=time_str,
            location_name=location_name,
        )
        report = kp_module.analyze_chart(chart)
        return json.dumps(report, indent=2)
    except Exception as e:
        return f"Error running KP analysis: {e}"


@mcp.tool()
async def get_consensus_prediction(
    datetime_str: str,
    latitude: float,
    longitude: float,
    question: str,
    time_str: Optional[str] = None,
    location_name: Optional[str] = None,
) -> str:
    """
    Query all astrological schools (Parashara, Jaimini, KP) for a specific question.
    Returns a unified consensus report with confidence scoring.
    Example questions: 'marriage', 'career'
    """
    try:
        chart = chart_engine.generate_birth_chart(
            datetime_str=datetime_str,
            latitude=latitude,
            longitude=longitude,
            time_str=time_str,
            location_name=location_name,
        )
        prediction = consensus_engine.generate_consensus(chart, question)
        return prediction.model_dump_json(indent=2)
    except Exception as e:
        return f"Error generating consensus: {e}"


@mcp.tool()
async def query_classical_texts(
    query_text: str,
    n_results: int = 3,
    source_filter: Optional[str] = None
) -> str:
    """
    Search the local vector database for classical astrological verses matching the query.
    Example query: "Moon in 7th house" or "Gajakesari yoga"
    """
    if not rag_retriever:
        return "RAG module is not available. Please ensure ChromaDB and sentence-transformers are installed."
        
    try:
        filters = {}
        if source_filter:
            filters["source"] = source_filter
            
        results = rag_retriever.query(query_text, n_results=n_results, filter_metadata=filters if filters else None)
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error querying classical texts: {e}"


@mcp.tool()
async def get_panchanga(
    datetime_str: str,
    latitude: float,
    longitude: float,
    time_str: Optional[str] = None,
) -> str:
    """
    Generate Daily Panchanga (Tithi, Vara, Nakshatra, Yoga, Karana, Sunrise, Sunset) for a given date/time and location.
    """
    try:
        event = chart_engine.calendar.normalize_birth_event(
            date_str=datetime_str,
            time_str=time_str,
            latitude=latitude,
            longitude=longitude,
        )
        res = panchanga_engine.compute_panchanga(
            jd=event.julian_day,
            lat=latitude,
            lon=longitude,
            alt=event.location.altitude,
            utc_offset_hours=event.utc_offset_hours,
            tz_name=event.location.timezone,
        )
        return res.model_dump_json(indent=2)
    except Exception as e:
        return f"Error generating Panchanga: {e}"


@mcp.tool()
async def get_divisional_chart(
    datetime_str: str,
    latitude: float,
    longitude: float,
    division: int,
    time_str: Optional[str] = None,
) -> str:
    """
    Generate a divisional chart (D2, D3, D4, D5, D6, D7, D8, D9, D10, D11, D12, D16, D20, D24, D27, D30, D40, D45, D60) from birth details.
    """
    try:
        base_chart = chart_engine.generate_birth_chart(
            datetime_str=datetime_str,
            latitude=latitude,
            longitude=longitude,
            time_str=time_str,
        )
        varga = chart_engine.generate_divisional_chart(base_chart, division=division)
        return varga.model_dump_json(indent=2)
    except Exception as e:
        return f"Error generating divisional chart D{division}: {e}"


@mcp.tool()
async def get_strengths(
    datetime_str: str,
    latitude: float,
    longitude: float,
    time_str: Optional[str] = None,
) -> str:
    """
    Calculate the Shadbala (six-fold strength) values for all 7 traditional planets.
    """
    try:
        chart = chart_engine.generate_birth_chart(
            datetime_str=datetime_str,
            latitude=latitude,
            longitude=longitude,
            time_str=time_str,
        )
        strengths = strength_engine.compute_shadbala(chart)
        return json.dumps({k: v.model_dump() for k, v in strengths.items()}, indent=2)
    except Exception as e:
        return f"Error calculating strengths: {e}"


@mcp.tool()
async def get_upagrahas(
    datetime_str: str,
    latitude: float,
    longitude: float,
    time_str: Optional[str] = None,
) -> str:
    """
    Compute positions of all time-based and Sun-derived Upagrahas (Gulika, Mandi, Yamakantaka, Dhuma, etc.).
    """
    try:
        chart = chart_engine.generate_birth_chart(
            datetime_str=datetime_str,
            latitude=latitude,
            longitude=longitude,
            time_str=time_str,
        )
        event = chart.birth_event
        local_dt = event.datetime_utc + timedelta(hours=event.utc_offset_hours)
        local_midnight = datetime(
            local_dt.year, local_dt.month, local_dt.day, tzinfo=timezone.utc
        )
        utc_midnight = local_midnight - timedelta(hours=event.utc_offset_hours)
        midnight_jd = chart_engine.astro.datetime_to_jd(utc_midnight)
        sunrise_jd = chart_engine.astro.compute_sunrise(midnight_jd, latitude, longitude)
        sunset_jd = chart_engine.astro.compute_sunset(midnight_jd, latitude, longitude)

        upagrahas = special_engine.compute_upagrahas(chart, sunrise_jd, sunset_jd)
        return json.dumps([u.model_dump() for u in upagrahas], indent=2)
    except Exception as e:
        return f"Error computing upagrahas: {e}"


@mcp.tool()
async def get_special_lagnas(
    datetime_str: str,
    latitude: float,
    longitude: float,
    time_str: Optional[str] = None,
) -> str:
    """
    Compute special sensitive points and ascendants (Hora Lagna, Ghati Lagna, Indu Lagna, Pranapada Lagna).
    """
    try:
        chart = chart_engine.generate_birth_chart(
            datetime_str=datetime_str,
            latitude=latitude,
            longitude=longitude,
            time_str=time_str,
        )
        event = chart.birth_event
        local_dt = event.datetime_utc + timedelta(hours=event.utc_offset_hours)
        local_midnight = datetime(
            local_dt.year, local_dt.month, local_dt.day, tzinfo=timezone.utc
        )
        utc_midnight = local_midnight - timedelta(hours=event.utc_offset_hours)
        midnight_jd = chart_engine.astro.datetime_to_jd(utc_midnight)
        sunrise_jd = chart_engine.astro.compute_sunrise(midnight_jd, latitude, longitude)

        lagnas = special_engine.compute_special_lagnas(chart, sunrise_jd)
        return json.dumps([lagna.model_dump() for lagna in lagnas], indent=2)
    except Exception as e:
        return f"Error computing special lagnas: {e}"


@mcp.tool()
async def get_transits(
    birth_datetime: str,
    birth_latitude: float,
    birth_longitude: float,
    transit_date: str,
) -> str:
    """
    Compute transit positions and their effects (Gochara aspects/hits/vedha)
    relative to a birth chart on a target date.

    Args:
        birth_datetime: ISO Date/Time of birth
        birth_latitude: Birth Latitude
        birth_longitude: Birth Longitude
        transit_date: Target date to check transits for (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
    """
    try:
        chart = chart_engine.generate_birth_chart(
            datetime_str=birth_datetime,
            latitude=birth_latitude,
            longitude=birth_longitude,
        )
        res = transit_engine.compute_transits(chart, transit_date)
        return res.model_dump_json(indent=2)
    except Exception as e:
        return f"Error computing transits: {e}"


@mcp.tool()
async def get_sade_sati(
    birth_datetime: str,
    birth_latitude: float,
    birth_longitude: float,
    transit_date: str,
) -> str:
    """
    Check if Sade Sati (Saturn transit over natal Moon) is active on a specific date,
    and returns details of the phase.

    Args:
        birth_datetime: ISO Date/Time of birth
        birth_latitude: Birth Latitude
        birth_longitude: Birth Longitude
        transit_date: Target date to check (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
    """
    try:
        chart = chart_engine.generate_birth_chart(
            datetime_str=birth_datetime,
            latitude=birth_latitude,
            longitude=birth_longitude,
        )
        res = transit_engine.compute_transits(chart, transit_date)
        return json.dumps(res.sade_sati, indent=2)
    except Exception as e:
        return f"Error computing Sade Sati: {e}"


@mcp.tool()
async def get_muhurta(
    birth_datetime: str,
    birth_latitude: float,
    birth_longitude: float,
    transit_date: str,
    event_type: str,
) -> str:
    """
    Evaluate Muhurta suitability for a specific event type on a target transit date.

    Args:
        birth_datetime: ISO Date/Time of birth
        birth_latitude: Birth Latitude
        birth_longitude: Birth Longitude
        transit_date: Target date to evaluate for Muhurta (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        event_type: The type of event ('marriage', 'business', 'travel', 'house_purchase', 'surgery')
    """
    try:
        chart = chart_engine.generate_birth_chart(
            datetime_str=birth_datetime,
            latitude=birth_latitude,
            longitude=birth_longitude,
        )
        res = muhurta_engine.evaluate_muhurta(
            birth_chart=chart,
            transit_date_str=transit_date,
            event_type=event_type,
        )
        return json.dumps(res, indent=2)
    except Exception as e:
        return f"Error evaluating Muhurta: {e}"


@mcp.tool()
async def get_prashna(
    datetime_str: str,
    latitude: float,
    longitude: float,
    question: str,
    number: Optional[int] = None,
) -> str:
    """
    Cast and evaluate a Prashna (Horary) chart.
    If a number (1-249) is provided, runs KP Horary (adjusting the chart to the matching sub-lord).
    Otherwise, runs Classical Prashna (analyzing the query chart directly).

    Args:
        datetime_str: ISO Date/Time of the question
        latitude: Latitude of the query location
        longitude: Longitude of the query location
        question: The question asked
        number: Optional KP Horary number (1-249)
    """
    try:
        chart = chart_engine.generate_birth_chart(
            datetime_str=datetime_str,
            latitude=latitude,
            longitude=longitude,
        )
        if number is not None:
            res = prashna_engine.evaluate_kp_horary(
                birth_chart=chart,
                question=question,
                number=number,
            )
        else:
            res = prashna_engine.evaluate_classical_prashna(
                birth_chart=chart,
                question=question,
            )
        return json.dumps(res, indent=2)
    except Exception as e:
        return f"Error evaluating Prashna: {e}"


if __name__ == "__main__":
    # Start the MCP server using stdin/stdout transport
    mcp.run()

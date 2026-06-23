"""
MCP Server Entrypoint

Exposes Jyotisha engines as MCP tools using FastMCP.
"""

from typing import Optional
from mcp.server.fastmcp import FastMCP

from jyotisha.engines.chart import ChartEngine
from jyotisha.engines.dasha import DashaEngine
from jyotisha.schools.parashara import ParasharaModule
from jyotisha.schools.jaimini import JaiminiModule
from jyotisha.schools.kp import KPModule
from jyotisha.engines.consensus import ConsensusEngine
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
parashara_module = ParasharaModule()
jaimini_module = JaiminiModule()
kp_module = KPModule()
consensus_engine = ConsensusEngine()

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
) -> str:
    """
    Generate Vimshottari Dasha timeline for a birth date.

    Args:
        datetime_str: ISO Date/Time
        latitude: Latitude
        longitude: Longitude
        levels: Depth of periods (1=Mahadasha, 2=Antardasha, 3=Pratyantardasha)

    Returns:
        JSON string containing the Dasha timeline.
    """
    try:
        chart = chart_engine.generate_birth_chart(
            datetime_str=datetime_str,
            latitude=latitude,
            longitude=longitude,
        )
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
        
        import json
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
        
        import json
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
) -> str:
    """
    Run a full Jaimini school analysis on a birth chart.
    Returns Chara Karakas, Rashi Drishti, and Arudha Padas.
    """
    try:
        chart = chart_engine.generate_birth_chart(
            datetime_str=datetime_str,
            latitude=latitude,
            longitude=longitude,
            time_str=time_str,
            location_name=location_name,
        )
        report = jaimini_module.analyze_chart(chart)
        import json
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
        import json
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
        
        import json
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error querying classical texts: {e}"

if __name__ == "__main__":
    # Start the MCP server using stdin/stdout transport
    mcp.run()

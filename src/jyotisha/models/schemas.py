"""
Pydantic Data Models for the Jyotisha MCP system.

All input/output schemas for charts, planets, houses, dashas, yogas, etc.
These models are the canonical data contract between all system layers.
"""

from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

from jyotisha.constants import Dignity


# ─────────────────────────────────────────────────────────────
# Birth Event & Location
# ─────────────────────────────────────────────────────────────

class Location(BaseModel):
    """Geographic location with timezone."""
    name: Optional[str] = None
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude: float = 0.0
    timezone: Optional[str] = None

class BirthEvent(BaseModel):
    """Normalized birth event for chart generation."""
    datetime_utc: datetime
    julian_day: float
    location: Location
    calendar_type: str = "Gregorian"
    dst_active: bool = False
    utc_offset_hours: float = 0.0
    notes: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────
# Planet Position
# ─────────────────────────────────────────────────────────────

class DignityInfo(BaseModel):
    """Planetary dignity classification."""
    status: Dignity
    is_exalted: bool = False
    is_debilitated: bool = False
    is_moolatrikona: bool = False
    is_own_sign: bool = False
    is_friendly: bool = False
    is_neutral: bool = False
    is_enemy: bool = False

class PlanetPosition(BaseModel):
    """Complete position data for a single planet."""
    name: str
    longitude: float = Field(..., ge=0, lt=360, description="Sidereal ecliptic longitude")
    latitude: float = 0.0
    distance: float = 0.0
    speed: float = 0.0
    sign: str
    sign_number: int = Field(..., ge=0, le=11)
    house: int = Field(..., ge=1, le=12)
    degree_in_sign: float = Field(..., ge=0, lt=30)
    retrograde: bool = False
    combust: bool = False
    planetary_war: Optional[str] = None
    nakshatra: str
    nakshatra_number: int = Field(..., ge=0, le=26)
    pada: int = Field(..., ge=1, le=4)
    nakshatra_lord: str
    dignity: DignityInfo
    vargottama: bool = False
    pushkara_navamsa: bool = False


# ─────────────────────────────────────────────────────────────
# House
# ─────────────────────────────────────────────────────────────

class House(BaseModel):
    """Data for a single house (bhava)."""
    number: int = Field(..., ge=1, le=12)
    sign: str
    sign_number: int = Field(..., ge=0, le=11)
    lord: str
    lord_house: Optional[int] = None
    cusp_longitude: float = 0.0
    span_start: float = 0.0
    span_end: float = 0.0
    planets_in_house: list[str] = Field(default_factory=list)
    aspects_received: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────
# Ascendant
# ─────────────────────────────────────────────────────────────

class Ascendant(BaseModel):
    """Lagna (Ascendant) data."""
    longitude: float
    sign: str
    sign_number: int
    degree_in_sign: float
    nakshatra: str
    nakshatra_number: int
    pada: int
    lord: str


# ─────────────────────────────────────────────────────────────
# Chart
# ─────────────────────────────────────────────────────────────

class ChartMetadata(BaseModel):
    """Metadata about a chart computation."""
    chart_type: str = "D1"
    ayanamsha: str = "Lahiri"
    ayanamsha_value: float = 0.0
    house_system: str = "Whole Sign"
    true_nodes: bool = True
    topocentric: bool = False
    engine_version: str = "0.1.0"
    computed_at: datetime = Field(default_factory=datetime.utcnow)

class Chart(BaseModel):
    """Complete Vedic birth chart."""
    ascendant: Ascendant
    planets: list[PlanetPosition]
    houses: list[House]
    metadata: ChartMetadata
    birth_event: Optional[BirthEvent] = None

    def get_planet(self, name: str) -> Optional[PlanetPosition]:
        """Get a planet by name."""
        for p in self.planets:
            if p.name == name:
                return p
        return None

    def get_house(self, number: int) -> Optional[House]:
        """Get a house by number."""
        for h in self.houses:
            if h.number == number:
                return h
        return None

    def get_house_lord(self, house_number: int) -> Optional[str]:
        """Get the lord of a specific house."""
        house = self.get_house(house_number)
        return house.lord if house else None

    def planets_in_sign(self, sign_number: int) -> list[PlanetPosition]:
        """Get all planets in a specific sign."""
        return [p for p in self.planets if p.sign_number == sign_number]

    def planets_in_house(self, house_number: int) -> list[PlanetPosition]:
        """Get all planets in a specific house."""
        return [p for p in self.planets if p.house == house_number]


# ─────────────────────────────────────────────────────────────
# Dasha
# ─────────────────────────────────────────────────────────────

class DashaPeriod(BaseModel):
    """A single dasha period (mahadasha, antardasha, etc.)."""
    lord: str
    start_date: str
    end_date: str
    start_jd: float = 0.0
    end_jd: float = 0.0
    years: float
    is_balance: bool = False
    sub_periods: list[DashaPeriod] = Field(default_factory=list)

class DashaTimeline(BaseModel):
    """Complete dasha timeline for a chart."""
    system: str  # "Vimshottari", "Yogini", etc.
    birth_nakshatra: str
    birth_nakshatra_lord: str
    balance_at_birth: dict = Field(default_factory=dict)
    timeline: list[DashaPeriod]


# ─────────────────────────────────────────────────────────────
# Yoga
# ─────────────────────────────────────────────────────────────

class YogaResult(BaseModel):
    """Result of yoga detection."""
    name: str
    category: str  # "raja", "dhana", "dosha", "pancha_mahapurusha", etc.
    is_active: bool = True
    is_cancelled: bool = False
    cancellation_reason: Optional[str] = None
    conclusion: str = ""
    effects: list[str] = Field(default_factory=list)
    intensity: str = "medium"  # "low", "medium", "high", "very_high"
    sources: list[str] = Field(default_factory=list)
    confidence: float = 0.8
    involved_planets: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────
# Strength
# ─────────────────────────────────────────────────────────────

class ShadBala(BaseModel):
    """Shadbala (six-fold strength) for a planet."""
    planet: str
    sthana_bala: float = 0.0
    dig_bala: float = 0.0
    kala_bala: float = 0.0
    cheshta_bala: float = 0.0
    naisargika_bala: float = 0.0
    drik_bala: float = 0.0
    total_shadbala: float = 0.0
    shadbala_rupas: float = 0.0
    required_rupas: float = 0.0
    is_sufficient: bool = False


# ─────────────────────────────────────────────────────────────
# Panchanga
# ─────────────────────────────────────────────────────────────

class PanchangaElement(BaseModel):
    """A single panchanga element."""
    number: int
    name: str

class Panchanga(BaseModel):
    """Daily Panchanga data."""
    date: str
    location: Location
    tithi: PanchangaElement
    paksha: str  # "Shukla" or "Krishna"
    vara: str
    vara_lord: str
    nakshatra: PanchangaElement
    yoga: PanchangaElement
    karana: PanchangaElement
    sunrise: str
    sunset: str
    moonrise: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# Transit
# ─────────────────────────────────────────────────────────────

class TransitEvent(BaseModel):
    """A significant transit event."""
    type: str  # "Sade Sati", "Jupiter Return", etc.
    planet: str
    phase: Optional[str] = None
    start_date: str
    end_date: str
    natal_reference: Optional[str] = None
    severity: str = "medium"
    description: str = ""
    vedha_blocked: bool = False


# ─────────────────────────────────────────────────────────────
# Arudha Padas
# ─────────────────────────────────────────────────────────────

class ArudhaPada(BaseModel):
    """An Arudha Pada position."""
    type: str  # "AL", "UL", "A2", ..., "A12"
    sign: str
    sign_number: int
    degree: Optional[float] = None


# ─────────────────────────────────────────────────────────────
# Argala
# ─────────────────────────────────────────────────────────────

class ArgalaIntervention(BaseModel):
    """Details of a specific Argala/Virodhargala pair."""
    argala_house_relative: int
    virodhargala_house_relative: int
    argala_planets: list[str] = Field(default_factory=list)
    virodhargala_planets: list[str] = Field(default_factory=list)
    is_active: bool = False

class ArgalaResult(BaseModel):
    """Argala status for a specific house or planet."""
    target: str  # e.g., "House 1" or "Sun"
    primary_argalas: list[ArgalaIntervention] = Field(default_factory=list)
    secondary_argalas: list[ArgalaIntervention] = Field(default_factory=list)
    has_unobstructed_argala: bool = False


# ─────────────────────────────────────────────────────────────
# Transit
# ─────────────────────────────────────────────────────────────

class TransitHit(BaseModel):
    """A transit hit on a natal planet or house."""
    transit_planet: str
    natal_point: str
    aspect_type: str  # "Conjunction", "Opposition", "Square", "Trine", etc., or Vedic Aspects
    orb: float
    is_exact: bool

class TransitResult(BaseModel):
    """Result of transiting planets over a natal chart."""
    date: str
    transit_planets: list[PlanetPosition]
    hits: list[TransitHit] = Field(default_factory=list)
    gochara_from_moon: dict[str, int] = Field(default_factory=dict)  # Planet -> House from Natal Moon

# ─────────────────────────────────────────────────────────────
# Upagraha
# ─────────────────────────────────────────────────────────────

class Upagraha(BaseModel):
    """Position of a subsidiary point."""
    name: str  # "Gulika", "Mandi", etc.
    sign: str
    sign_number: int
    degree: float


# ─────────────────────────────────────────────────────────────
# Special Lagna
# ─────────────────────────────────────────────────────────────

class SpecialLagna(BaseModel):
    """A special lagna position."""
    type: str  # "Hora", "Ghati", "Indu", "Pranapada", "Sree"
    sign: str
    sign_number: int
    degree: float


# ─────────────────────────────────────────────────────────────
# Remedy
# ─────────────────────────────────────────────────────────────

class Remedy(BaseModel):
    """A classical astrological remedy."""
    affliction: str
    category: str  # "gemstone", "mantra", "donation", "fasting", "worship"
    description: str
    mantra: Optional[str] = None
    source: str
    tradition: str = "Parashara"
    precautions: list[str] = Field(default_factory=list)
    confidence: float = 0.7
    disclaimer: str = "Traditional cultural advice; not a medical or scientific guarantee."


# ─────────────────────────────────────────────────────────────
# Consensus / Prediction
# ─────────────────────────────────────────────────────────────

class SchoolResult(BaseModel):
    """Result from a single astrological school."""
    school: str
    answer: Optional[str] = None
    confidence: float = 0.0
    sources: list[str] = Field(default_factory=list)
    reasoning: str = ""
    rules_fired: list[str] = Field(default_factory=list)

class ConsensusPrediction(BaseModel):
    """Multi-school consensus prediction."""
    question: str
    school_results: list[SchoolResult]
    consensus_answer: Optional[str] = None
    consensus_confidence: float = 0.0
    agreement_level: str = "low"  # "low", "medium", "high"
    explanation: str = ""
    all_sources: list[str] = Field(default_factory=list)

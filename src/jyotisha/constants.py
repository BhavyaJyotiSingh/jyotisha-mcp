"""
Vedic Astrology Constants — Signs, Nakshatras, Planets, Dignities

This module contains all the fundamental astronomical and astrological
constants used throughout the Jyotisha MCP system.
"""

from enum import IntEnum, StrEnum
from dataclasses import dataclass

# ─────────────────────────────────────────────────────────────
# Zodiac Signs (Rashis)
# ─────────────────────────────────────────────────────────────

class Sign(IntEnum):
    """12 Zodiac signs, 0-indexed."""
    ARIES = 0
    TAURUS = 1
    GEMINI = 2
    CANCER = 3
    LEO = 4
    VIRGO = 5
    LIBRA = 6
    SCORPIO = 7
    SAGITTARIUS = 8
    CAPRICORN = 9
    AQUARIUS = 10
    PISCES = 11

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

SIGN_SANSKRIT = [
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena",
]

class Element(StrEnum):
    FIRE = "Fire"
    EARTH = "Earth"
    AIR = "Air"
    WATER = "Water"

SIGN_ELEMENTS = [
    Element.FIRE, Element.EARTH, Element.AIR, Element.WATER,
    Element.FIRE, Element.EARTH, Element.AIR, Element.WATER,
    Element.FIRE, Element.EARTH, Element.AIR, Element.WATER,
]

class Modality(StrEnum):
    MOVABLE = "Movable"     # Chara
    FIXED = "Fixed"         # Sthira
    DUAL = "Dual"           # Dvisvabhava

SIGN_MODALITIES = [
    Modality.MOVABLE, Modality.FIXED, Modality.DUAL, Modality.MOVABLE,
    Modality.FIXED, Modality.DUAL, Modality.MOVABLE, Modality.FIXED,
    Modality.DUAL, Modality.MOVABLE, Modality.FIXED, Modality.DUAL,
]


# ─────────────────────────────────────────────────────────────
# Planets (Grahas)
# ─────────────────────────────────────────────────────────────

class Planet(StrEnum):
    SUN = "Sun"
    MOON = "Moon"
    MARS = "Mars"
    MERCURY = "Mercury"
    JUPITER = "Jupiter"
    VENUS = "Venus"
    SATURN = "Saturn"
    RAHU = "Rahu"
    KETU = "Ketu"

PLANET_SANSKRIT = {
    Planet.SUN: "Surya",
    Planet.MOON: "Chandra",
    Planet.MARS: "Mangala",
    Planet.MERCURY: "Budha",
    Planet.JUPITER: "Guru",
    Planet.VENUS: "Shukra",
    Planet.SATURN: "Shani",
    Planet.RAHU: "Rahu",
    Planet.KETU: "Ketu",
}

# Swiss Ephemeris planet IDs
SWIEPH_PLANET_IDS = {
    Planet.SUN: 0,       # SE_SUN
    Planet.MOON: 1,      # SE_MOON
    Planet.MERCURY: 2,   # SE_MERCURY
    Planet.VENUS: 3,     # SE_VENUS
    Planet.MARS: 4,      # SE_MARS
    Planet.JUPITER: 5,   # SE_JUPITER
    Planet.SATURN: 6,    # SE_SATURN
    Planet.RAHU: 11,     # SE_TRUE_NODE (True Rahu)
}

RAHU_MEAN_NODE_ID = 10  # SE_MEAN_NODE


# ─────────────────────────────────────────────────────────────
# Planetary Lordship (Sign rulers)
# ─────────────────────────────────────────────────────────────

SIGN_LORDS = {
    Sign.ARIES: Planet.MARS,
    Sign.TAURUS: Planet.VENUS,
    Sign.GEMINI: Planet.MERCURY,
    Sign.CANCER: Planet.MOON,
    Sign.LEO: Planet.SUN,
    Sign.VIRGO: Planet.MERCURY,
    Sign.LIBRA: Planet.VENUS,
    Sign.SCORPIO: Planet.MARS,
    Sign.SAGITTARIUS: Planet.JUPITER,
    Sign.CAPRICORN: Planet.SATURN,
    Sign.AQUARIUS: Planet.SATURN,
    Sign.PISCES: Planet.JUPITER,
}


# ─────────────────────────────────────────────────────────────
# Planetary Dignities
# ─────────────────────────────────────────────────────────────

class Dignity(StrEnum):
    EXALTED = "Exalted"             # Uchcha
    MOOLATRIKONA = "Moolatrikona"   # Own sign special zone
    OWN_SIGN = "Own Sign"           # Swakshetra
    FRIENDLY = "Friendly"           # Mitra
    NEUTRAL = "Neutral"             # Sama
    ENEMY = "Enemy"                 # Shatru
    DEBILITATED = "Debilitated"     # Neecha

@dataclass
class ExaltationData:
    sign: Sign
    exact_degree: float  # Exact degree of maximum exaltation

EXALTATION = {
    Planet.SUN:     ExaltationData(Sign.ARIES, 10.0),
    Planet.MOON:    ExaltationData(Sign.TAURUS, 3.0),
    Planet.MARS:    ExaltationData(Sign.CAPRICORN, 28.0),
    Planet.MERCURY: ExaltationData(Sign.VIRGO, 15.0),
    Planet.JUPITER: ExaltationData(Sign.CANCER, 5.0),
    Planet.VENUS:   ExaltationData(Sign.PISCES, 27.0),
    Planet.SATURN:  ExaltationData(Sign.LIBRA, 20.0),
    Planet.RAHU:    ExaltationData(Sign.TAURUS, 20.0),   # Per BPHS
    Planet.KETU:    ExaltationData(Sign.SCORPIO, 20.0),
}

DEBILITATION = {
    Planet.SUN:     Sign.LIBRA,
    Planet.MOON:    Sign.SCORPIO,
    Planet.MARS:    Sign.CANCER,
    Planet.MERCURY: Sign.PISCES,
    Planet.JUPITER: Sign.CAPRICORN,
    Planet.VENUS:   Sign.VIRGO,
    Planet.SATURN:  Sign.ARIES,
    Planet.RAHU:    Sign.SCORPIO,
    Planet.KETU:    Sign.TAURUS,
}

# Moolatrikona signs and degree ranges (within the sign, 0-30)
@dataclass
class MoolatrikonaData:
    sign: Sign
    start_degree: float
    end_degree: float

MOOLATRIKONA = {
    Planet.SUN:     MoolatrikonaData(Sign.LEO, 0.0, 20.0),
    Planet.MOON:    MoolatrikonaData(Sign.TAURUS, 3.0, 30.0),
    Planet.MARS:    MoolatrikonaData(Sign.ARIES, 0.0, 12.0),
    Planet.MERCURY: MoolatrikonaData(Sign.VIRGO, 15.0, 20.0),
    Planet.JUPITER: MoolatrikonaData(Sign.SAGITTARIUS, 0.0, 10.0),
    Planet.VENUS:   MoolatrikonaData(Sign.LIBRA, 0.0, 15.0),
    Planet.SATURN:  MoolatrikonaData(Sign.AQUARIUS, 0.0, 20.0),
}

# Own signs (each planet rules 1 or 2 signs)
OWN_SIGNS = {
    Planet.SUN:     [Sign.LEO],
    Planet.MOON:    [Sign.CANCER],
    Planet.MARS:    [Sign.ARIES, Sign.SCORPIO],
    Planet.MERCURY: [Sign.GEMINI, Sign.VIRGO],
    Planet.JUPITER: [Sign.SAGITTARIUS, Sign.PISCES],
    Planet.VENUS:   [Sign.TAURUS, Sign.LIBRA],
    Planet.SATURN:  [Sign.CAPRICORN, Sign.AQUARIUS],
    Planet.RAHU:    [Sign.AQUARIUS],  # Per some traditions
    Planet.KETU:    [Sign.SCORPIO],   # Per some traditions
}


# ─────────────────────────────────────────────────────────────
# Planetary Friendships (Natural — Naisargika)
# ─────────────────────────────────────────────────────────────

# Friends, Neutrals, Enemies — as per BPHS
NATURAL_FRIENDS: dict[Planet, list[Planet]] = {
    Planet.SUN:     [Planet.MOON, Planet.MARS, Planet.JUPITER],
    Planet.MOON:    [Planet.SUN, Planet.MERCURY],
    Planet.MARS:    [Planet.SUN, Planet.MOON, Planet.JUPITER],
    Planet.MERCURY: [Planet.SUN, Planet.VENUS],
    Planet.JUPITER: [Planet.SUN, Planet.MOON, Planet.MARS],
    Planet.VENUS:   [Planet.MERCURY, Planet.SATURN],
    Planet.SATURN:  [Planet.MERCURY, Planet.VENUS],
}

NATURAL_ENEMIES: dict[Planet, list[Planet]] = {
    Planet.SUN:     [Planet.VENUS, Planet.SATURN],
    Planet.MOON:    [],  # Moon has no natural enemies
    Planet.MARS:    [Planet.MERCURY],
    Planet.MERCURY: [Planet.MOON],
    Planet.JUPITER: [Planet.MERCURY, Planet.VENUS],
    Planet.VENUS:   [Planet.SUN, Planet.MOON],
    Planet.SATURN:  [Planet.SUN, Planet.MOON, Planet.MARS],
}

# Neutrals are all others not in friends or enemies


# ─────────────────────────────────────────────────────────────
# Combustion Distances (from Sun, in degrees)
# ─────────────────────────────────────────────────────────────

COMBUSTION_DISTANCE = {
    Planet.MOON:    12.0,
    Planet.MARS:    17.0,
    Planet.MERCURY: 14.0,   # 12° if retrograde
    Planet.JUPITER: 11.0,
    Planet.VENUS:   10.0,   # 8° if retrograde
    Planet.SATURN:  15.0,
}

COMBUSTION_DISTANCE_RETRO = {
    Planet.MERCURY: 12.0,
    Planet.VENUS:   8.0,
}


# ─────────────────────────────────────────────────────────────
# Nakshatras (27 Lunar Mansions)
# ─────────────────────────────────────────────────────────────

NAKSHATRA_SPAN = 360.0 / 27.0  # 13°20' = 13.3333...°

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
    "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

# Nakshatra lords for Vimshottari Dasha (cyclic: Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury)
NAKSHATRA_LORDS = [
    Planet.KETU, Planet.VENUS, Planet.SUN, Planet.MOON, Planet.MARS,
    Planet.RAHU, Planet.JUPITER, Planet.SATURN, Planet.MERCURY,
    Planet.KETU, Planet.VENUS, Planet.SUN, Planet.MOON, Planet.MARS,
    Planet.RAHU, Planet.JUPITER, Planet.SATURN, Planet.MERCURY,
    Planet.KETU, Planet.VENUS, Planet.SUN, Planet.MOON, Planet.MARS,
    Planet.RAHU, Planet.JUPITER, Planet.SATURN, Planet.MERCURY,
]

# Nakshatra deities
NAKSHATRA_DEITIES = [
    "Ashwini Kumaras", "Yama", "Agni", "Brahma", "Soma",
    "Rudra", "Aditi", "Brihaspati", "Sarpa", "Pitris",
    "Bhaga", "Aryaman", "Savitar", "Tvashtar", "Vayu",
    "Indragni", "Mitra", "Indra", "Nirriti", "Apas",
    "Vishvedevas", "Vishnu", "Vasu", "Varuna",
    "Ajaikapada", "Ahir Budhnya", "Pushan",
]


# ─────────────────────────────────────────────────────────────
# Vimshottari Dasha Periods (years)
# ─────────────────────────────────────────────────────────────

VIMSHOTTARI_YEARS = {
    Planet.KETU:    7,
    Planet.VENUS:   20,
    Planet.SUN:     6,
    Planet.MOON:    10,
    Planet.MARS:    7,
    Planet.RAHU:    18,
    Planet.JUPITER: 16,
    Planet.SATURN:  19,
    Planet.MERCURY: 17,
}

VIMSHOTTARI_ORDER = [
    Planet.KETU, Planet.VENUS, Planet.SUN, Planet.MOON, Planet.MARS,
    Planet.RAHU, Planet.JUPITER, Planet.SATURN, Planet.MERCURY,
]

VIMSHOTTARI_TOTAL_YEARS = 120


# ─────────────────────────────────────────────────────────────
# Ayanamsha Identifiers (Swiss Ephemeris IDs)
# ─────────────────────────────────────────────────────────────

class Ayanamsha(IntEnum):
    """Swiss Ephemeris sidereal mode constants."""
    FAGAN_BRADLEY = 0
    LAHIRI = 1
    DELUCE = 2
    RAMAN = 3
    USHASHASHI = 4
    KRISHNAMURTI = 5    # KP
    DJWHAL_KHUL = 6
    YUKTESWAR = 7
    JN_BHASIN = 8
    BABYLONIAN_HUBER = 9
    BABYLONIAN_ETPSC = 10
    ALDEBARAN_15TAU = 11
    HIPPARCHOS = 12
    SASSANIAN = 13
    GALACT_CTR_0SAG = 14
    J2000 = 15
    J1900 = 16
    B1950 = 17
    SURYASIDDHANTA = 18
    SURYASIDDHANTA_MSUN = 19
    ARYABHATA = 20
    ARYABHATA_MSUN = 21
    SS_REVATI = 22
    SS_CITRA = 23
    TRUE_CITRA = 24
    TRUE_REVATI = 25
    TRUE_PUSHYA = 26
    GALACT_CTR_BRAND = 27
    GALACT_EQ_IAU1958 = 28
    GALACT_EQ = 29
    GALACT_EQ_MIDMULA = 30
    SKYDRAM = 31
    TRUE_MULA = 32
    DHRUVA = 33
    ARYABHATA_522 = 34
    BRITTON = 35
    GALACT_CTR_0CAP = 36


# ─────────────────────────────────────────────────────────────
# Vedic Aspects (Drishti)
# ─────────────────────────────────────────────────────────────

# All planets aspect the 7th house from themselves (180°)
# Special aspects:
SPECIAL_ASPECTS = {
    Planet.MARS:    [4, 8],       # Mars also aspects 4th and 8th
    Planet.JUPITER: [5, 9],       # Jupiter also aspects 5th and 9th
    Planet.SATURN:  [3, 10],      # Saturn also aspects 3rd and 10th
    Planet.RAHU:    [5, 9],       # Rahu (per some traditions) = Jupiter aspects
    Planet.KETU:    [5, 9],       # Ketu (per some traditions) = Jupiter aspects
}


# ─────────────────────────────────────────────────────────────
# Natural Benefics and Malefics
# ─────────────────────────────────────────────────────────────

NATURAL_BENEFICS = [Planet.JUPITER, Planet.VENUS, Planet.MERCURY, Planet.MOON]
NATURAL_MALEFICS = [Planet.SUN, Planet.MARS, Planet.SATURN, Planet.RAHU, Planet.KETU]

# Note: Mercury is benefic when alone or with benefics, malefic when with malefics
# Moon is benefic when waxing (Shukla Paksha), malefic when waning (Krishna Paksha)


# ─────────────────────────────────────────────────────────────
# Karakas (Natural Significators)
# ─────────────────────────────────────────────────────────────

NAISARGIKA_KARAKAS = {
    Planet.SUN:     ["Soul", "Father", "Authority", "Government", "Health"],
    Planet.MOON:    ["Mind", "Mother", "Emotions", "Public", "Liquids"],
    Planet.MARS:    ["Energy", "Brothers", "Land", "Courage", "Surgery"],
    Planet.MERCURY: ["Intelligence", "Speech", "Commerce", "Education", "Writing"],
    Planet.JUPITER: ["Wisdom", "Children", "Dharma", "Wealth", "Guru"],
    Planet.VENUS:   ["Love", "Marriage", "Art", "Vehicles", "Luxury"],
    Planet.SATURN:  ["Longevity", "Discipline", "Servants", "Sorrow", "Hard Work"],
    Planet.RAHU:    ["Foreign", "Obsession", "Technology", "Unconventional", "Illusion"],
    Planet.KETU:    ["Spirituality", "Liberation", "Ancestors", "Mysticism", "Loss"],
}


# ─────────────────────────────────────────────────────────────
# House Significations
# ─────────────────────────────────────────────────────────────

HOUSE_SIGNIFICATIONS = {
    1:  ["Self", "Body", "Appearance", "Health", "Personality"],
    2:  ["Wealth", "Family", "Speech", "Food", "Right Eye"],
    3:  ["Siblings", "Courage", "Short Travel", "Communication", "Hands"],
    4:  ["Mother", "Home", "Property", "Vehicles", "Education", "Happiness"],
    5:  ["Children", "Intelligence", "Romance", "Creativity", "Purva Punya"],
    6:  ["Enemies", "Disease", "Debts", "Service", "Litigation"],
    7:  ["Marriage", "Partner", "Business", "Foreign Travel", "Death (Maraka)"],
    8:  ["Longevity", "Occult", "Inheritance", "Transformation", "Chronic Disease"],
    9:  ["Father", "Dharma", "Fortune", "Higher Learning", "Long Travel", "Guru"],
    10: ["Career", "Karma", "Authority", "Status", "Government"],
    11: ["Gains", "Income", "Friends", "Aspirations", "Elder Siblings"],
    12: ["Loss", "Expenses", "Foreign Lands", "Liberation", "Sleep", "Left Eye"],
}

BHAVA_KARAKAS = {
    1: [Planet.SUN],
    2: [Planet.JUPITER],
    3: [Planet.MARS],
    4: [Planet.MOON, Planet.MERCURY],
    5: [Planet.JUPITER],
    6: [Planet.MARS, Planet.SATURN],
    7: [Planet.VENUS],
    8: [Planet.SATURN],
    9: [Planet.SUN, Planet.JUPITER],
    10: [Planet.SUN, Planet.MERCURY, Planet.JUPITER, Planet.SATURN],
    11: [Planet.JUPITER],
    12: [Planet.SATURN],
}


# ─────────────────────────────────────────────────────────────
# Tithi Names (Lunar Days)
# ─────────────────────────────────────────────────────────────

TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya",
]

WEEKDAY_NAMES = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]

WEEKDAY_LORDS = {
    "Sunday": Planet.SUN,
    "Monday": Planet.MOON,
    "Tuesday": Planet.MARS,
    "Wednesday": Planet.MERCURY,
    "Thursday": Planet.JUPITER,
    "Friday": Planet.VENUS,
    "Saturday": Planet.SATURN,
}

YOGA_NAMES = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarma", "Dhriti", "Shoola", "Ganda",
    "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
    "Siddhi", "Vyatipata", "Variyan", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma",
    "Indra", "Vaidhriti",
]

KARANA_NAMES = [
    "Bava", "Balava", "Kaulava", "Taitila", "Gara",
    "Vanija", "Vishti", "Shakuni", "Chatushpada", "Naga", "Kimstughna",
]

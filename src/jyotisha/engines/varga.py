"""
Varga Engine — Layer V

Mathematical computation of all Divisional Charts (Vargas).
Includes D1 through D144 based on classical principles.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from jyotisha.constants import Sign


class HoraMethod(StrEnum):
    """Supported D2 Hora computation traditions."""

    PARASHARA = "Parashara"
    KASHINATHA = "Kashinatha"


class DrekkanaMethod(StrEnum):
    """Supported D3 Drekkana computation traditions."""

    PARASHARA = "Parashara"
    SOMNATHA = "Somnatha"
    JAGANNATHA = "Jagannatha"


@dataclass(frozen=True)
class VargaFormulaSpec:
    """Traceable metadata for a divisional-chart formula."""

    division: int
    classical_source: str
    method: str
    alternative_methods: tuple[str, ...] = ()
    unit_test_cases: tuple[tuple[float, int], ...] = field(default_factory=tuple)


VARGA_FORMULA_SPECS: dict[int, VargaFormulaSpec] = {
    2: VargaFormulaSpec(
        division=2,
        classical_source="BPHS Ch.6, Sl.5-6",
        method=HoraMethod.PARASHARA.value,
        alternative_methods=(HoraMethod.KASHINATHA.value,),
        unit_test_cases=((7.5, Sign.LEO.value), (22.5, Sign.CANCER.value)),
    ),
    3: VargaFormulaSpec(
        division=3,
        classical_source="BPHS Ch.6, Sl.7",
        method=DrekkanaMethod.PARASHARA.value,
        alternative_methods=(
            DrekkanaMethod.SOMNATHA.value,
            DrekkanaMethod.JAGANNATHA.value,
        ),
        unit_test_cases=((5.0, Sign.ARIES.value), (15.0, Sign.LEO.value)),
    ),
    9: VargaFormulaSpec(
        division=9,
        classical_source="BPHS Ch.6, Sl.9-10",
        method="Parashara",
        unit_test_cases=((15.0, Sign.LEO.value), (33.0, Sign.CAPRICORN.value)),
    ),
    60: VargaFormulaSpec(
        division=60,
        classical_source="BPHS Ch.6, Sl.28-31",
        method="Odd signs forward, even signs offset per implemented BPHS mapping",
        unit_test_cases=((0.25, Sign.ARIES.value), (30.25, Sign.SAGITTARIUS.value)),
    ),
    81: VargaFormulaSpec(
        division=81,
        classical_source="BPHS variant tradition",
        method="D9(D9)",
        unit_test_cases=((0.25, Sign.ARIES.value),),
    ),
    108: VargaFormulaSpec(
        division=108,
        classical_source="Classical compositional varga tradition",
        method="D12(D9)",
    ),
    144: VargaFormulaSpec(
        division=144,
        classical_source="Classical compositional varga tradition",
        method="D12(D12)",
    ),
}


class VargaEngine:
    """Dedicated mathematical engine for calculating Varga boundaries and mapping."""

    @staticmethod
    def get_supported_vargas() -> list[int]:
        return [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 16, 20, 24, 27, 30, 40, 45, 60, 81, 108, 144]

    @staticmethod
    def get_formula_spec(division: int) -> VargaFormulaSpec:
        """Return traceable formula metadata for a supported varga."""
        try:
            return VARGA_FORMULA_SPECS[division]
        except KeyError as exc:
            raise ValueError(f"No formula metadata registered for D{division}.") from exc

    def compute_varga_sign(self, longitude: float, division: int) -> int:
        """Compute the mapped sign (0-11) for a given longitude in a specific varga division."""
        longitude = self._normalize_longitude(longitude)
        methods = {
            2: self._compute_hora_sign,
            3: self._compute_drekkana_sign,
            4: self._compute_chaturthamsa_sign,
            5: self._compute_panchamsa_sign,
            6: self._compute_shasthamsa_sign,
            7: self._compute_saptamsa_sign,
            8: self._compute_ashtamsa_sign,
            9: self._compute_navamsa_sign,
            10: self._compute_dasamsa_sign,
            11: self._compute_rudramsa_sign,
            12: self._compute_dwadasamsa_sign,
            16: self._compute_shodasamsa_sign,
            20: self._compute_vimsamsa_sign,
            24: self._compute_siddhamsa_sign,
            27: self._compute_bhamsa_sign,
            30: self._compute_trimsamsa_sign,
            40: self._compute_khavedamsa_sign,
            45: self._compute_akshavedamsa_sign,
            60: self._compute_shashtiamsa_sign,
            81: self._compute_navanavamsa_sign,
            108: self._compute_ashtottaramsa_sign,
            144: self._compute_dwadashadwadasamsa_sign,
        }
        
        if division not in methods:
            raise ValueError(f"Division D{division} not supported.")
            
        return methods[division](longitude)

    def compute_varga_degree(self, longitude: float, division: int) -> float:
        """Calculate the exact fractional degree of a planet mathematically mapped into the Varga sign."""
        longitude = self._normalize_longitude(longitude)
        if division == 30:
            deg = longitude % 30.0
            sign = int(longitude // 30.0)
            if sign % 2 == 0:
                segments = [(0.0, 5.0), (5.0, 10.0), (10.0, 18.0), (18.0, 25.0), (25.0, 30.0)]
            else:
                segments = [(0.0, 5.0), (5.0, 12.0), (12.0, 20.0), (20.0, 25.0), (25.0, 30.0)]
                
            fraction = 0.5
            for start_deg, end_deg in segments:
                if deg <= end_deg or end_deg == 30.0:
                    slice_size = end_deg - start_deg
                    fraction = (deg - start_deg) / slice_size
                    break
        else:
            slice_size = 30.0 / division
            fraction = (longitude % slice_size) / slice_size
            
        return fraction * 30.0

    @staticmethod
    def _normalize_longitude(longitude: float) -> float:
        if not isinstance(longitude, (int, float)):
            raise TypeError("Longitude must be numeric")
        return float(longitude) % 360.0

    # ─────────────────────────────────────────────────────────
    # Individual Varga Methods
    # ─────────────────────────────────────────────────────────

    def _compute_hora_sign(self, longitude: float) -> int:
        """D2 Hora: 2 parts of 15° each (Parashara basic)."""
        sign = int(longitude // 30)
        deg = longitude % 30
        if deg < 15:
            return Sign.LEO.value if sign % 2 == 0 else Sign.CANCER.value
        else:
            return Sign.CANCER.value if sign % 2 == 0 else Sign.LEO.value

    def _compute_drekkana_sign(self, longitude: float) -> int:
        """D3 Drekkana: 3 parts of 10° each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 10)
        offsets = [0, 4, 8]
        return (sign + offsets[part]) % 12

    def _compute_chaturthamsa_sign(self, longitude: float) -> int:
        """D4 Chaturthamsha: 4 parts of 7°30' each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 7.5)
        return (sign + part * 3) % 12

    def _compute_panchamsa_sign(self, longitude: float) -> int:
        """D5 Panchamsha: 5 parts of 6° each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 6.0)
        odd_map = [Sign.ARIES.value, Sign.AQUARIUS.value, Sign.SAGITTARIUS.value, Sign.GEMINI.value, Sign.LIBRA.value]
        even_map = [Sign.TAURUS.value, Sign.VIRGO.value, Sign.PISCES.value, Sign.CAPRICORN.value, Sign.SCORPIO.value]
        return odd_map[part] if sign % 2 == 0 else even_map[part]

    def _compute_shasthamsa_sign(self, longitude: float) -> int:
        """D6 Shasthamsa: 6 parts of 5° each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 5.0)
        start = Sign.ARIES.value if sign % 2 == 0 else Sign.LIBRA.value
        return (start + part) % 12

    def _compute_saptamsa_sign(self, longitude: float) -> int:
        """D7 Saptamsha: 7 parts of 4°17'8.57\" each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / (30.0 / 7))
        return (sign + part) % 12 if sign % 2 == 0 else (sign + 6 + part) % 12

    def _compute_ashtamsa_sign(self, longitude: float) -> int:
        """D8 Ashtamsha: 8 parts of 3°45' each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 3.75)
        modality = sign % 3
        starts = {0: sign, 1: (sign + 8) % 12, 2: (sign + 4) % 12}
        return (starts[modality] + part) % 12

    def _compute_navamsa_sign(self, longitude: float) -> int:
        """D9 Navamsa: 9 parts of 3°20' each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / (30.0 / 9))
        element = sign % 4
        starts = [0, 9, 6, 3]  # Fire→Aries, Earth→Cap, Air→Libra, Water→Cancer
        return (starts[element] + part) % 12

    def _compute_dasamsa_sign(self, longitude: float) -> int:
        """D10 Dasamsha: 10 parts of 3° each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 3.0)
        return (sign + part) % 12 if sign % 2 == 0 else (sign + 8 + part) % 12

    def _compute_rudramsa_sign(self, longitude: float) -> int:
        """D11 Rudramsa: 11 parts of 2°43'38\" each."""
        deg = longitude % 30
        part = int(deg / (30.0 / 11.0))
        return part % 12

    def _compute_dwadasamsa_sign(self, longitude: float) -> int:
        """D12 Dwadashamsha: 12 parts of 2°30' each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 2.5)
        return (sign + part) % 12

    def _compute_shodasamsa_sign(self, longitude: float) -> int:
        """D16 Shodashamsha: 16 parts of 1°52'30\" each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / (30.0 / 16))
        starts = [0, 4, 8]
        return (starts[sign % 3] + part) % 12

    def _compute_vimsamsa_sign(self, longitude: float) -> int:
        """D20 Vimshamsha: 20 parts of 1°30' each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / (30.0 / 20))
        starts = [0, 8, 4]
        return (starts[sign % 3] + part) % 12

    def _compute_siddhamsa_sign(self, longitude: float) -> int:
        """D24 Siddhamsha: 24 parts of 1°15' each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / (30.0 / 24))
        return (Sign.LEO.value + part) % 12 if sign % 2 == 0 else (Sign.CANCER.value + part) % 12

    def _compute_bhamsa_sign(self, longitude: float) -> int:
        """D27 Bhamsha: 27 parts per sign."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / (30.0 / 27))
        starts = [0, 3, 6, 9]
        return (starts[sign % 4] + part) % 12

    def _compute_trimsamsa_sign(self, longitude: float) -> int:
        """D30 Trimshamsha: irregular division."""
        sign = int(longitude // 30)
        deg = longitude % 30
        if sign % 2 == 0:
            segments = [(5, Sign.ARIES.value), (10, Sign.AQUARIUS.value), (18, Sign.SAGITTARIUS.value), (25, Sign.GEMINI.value), (30, Sign.LIBRA.value)]
        else:
            segments = [(5, Sign.LIBRA.value), (12, Sign.GEMINI.value), (20, Sign.SAGITTARIUS.value), (25, Sign.AQUARIUS.value), (30, Sign.ARIES.value)]
        for boundary, result_sign in segments:
            if deg < boundary:
                return result_sign
        return segments[-1][1]

    def _compute_khavedamsa_sign(self, longitude: float) -> int:
        """D40 Khavedamsha: 40 parts of 0°45' each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 0.75)
        start = Sign.ARIES.value if sign % 2 == 0 else Sign.LIBRA.value
        return (start + part) % 12

    def _compute_akshavedamsa_sign(self, longitude: float) -> int:
        """D45 Akshavedamsha: 45 parts of 0°40' each."""
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / (30.0 / 45.0))
        starts = [Sign.ARIES.value, Sign.LEO.value, Sign.SAGITTARIUS.value]
        return (starts[sign % 3] + part) % 12

    def _compute_shashtiamsa_sign(self, longitude: float) -> int:
        """
        D60 Shashtiamsha: 60 parts of 0°30' each.
        Odd signs start from Aries (0), Even signs start from Sagittarius (8).
        """
        sign = int(longitude // 30)
        deg = longitude % 30
        part = int(deg / 0.5)
        # Note: sign % 2 == 0 corresponds to physically ODD signs (Aries=0, Gemini=2, etc.)
        if sign % 2 == 0:
            return part % 12
        else:
            return (part + 8) % 12

    def _compute_navanavamsa_sign(self, longitude: float) -> int:
        """D81 Navanavamsa: D9 of D9 (Navamsa of Navamsa)."""
        d9_sign = self._compute_navamsa_sign(longitude)
        d9_deg = self.compute_varga_degree(longitude, 9)
        d9_lon = d9_sign * 30.0 + d9_deg
        return self._compute_navamsa_sign(d9_lon)

    def _compute_ashtottaramsa_sign(self, longitude: float) -> int:
        """D108 Ashtottaramsa: D12 applied to the D9 position."""
        d9_sign = self._compute_navamsa_sign(longitude)
        d9_degree = self.compute_varga_degree(longitude, 9)
        return self._compute_dwadasamsa_sign(d9_sign * 30.0 + d9_degree)

    def _compute_dwadashadwadasamsa_sign(self, longitude: float) -> int:
        """D144 Dwadashadwadasamsa: D12 applied twice."""
        d12_sign = self._compute_dwadasamsa_sign(longitude)
        d12_degree = self.compute_varga_degree(longitude, 12)
        return self._compute_dwadasamsa_sign(d12_sign * 30.0 + d12_degree)

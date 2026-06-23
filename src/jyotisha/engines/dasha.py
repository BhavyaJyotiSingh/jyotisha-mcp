"""
Dasha Engine — Layer F

Computes Mahadasha and sub-period timelines for various dasha systems.
Currently implements Vimshottari Dasha (primary system).
"""

from __future__ import annotations

from jyotisha.constants import (
    NAKSHATRA_SPAN, VIMSHOTTARI_YEARS, VIMSHOTTARI_ORDER, VIMSHOTTARI_TOTAL_YEARS,
    Planet,
)
from jyotisha.models.schemas import DashaPeriod, DashaTimeline, Chart


class DashaEngine:
    """
    Computes dasha (planetary period) timelines.

    Supports:
    - Vimshottari Dasha (120-year cycle based on Moon's nakshatra)
    - Sub-periods: Antardasha, Pratyantardasha
    """

    DAYS_PER_YEAR = 365.25

    def compute_vimshottari(
        self,
        moon_longitude: float,
        birth_jd: float,
        levels: int = 2,
    ) -> DashaTimeline:
        """
        Compute Vimshottari Dasha timeline.

        Args:
            moon_longitude: Moon's sidereal longitude (0-360)
            birth_jd: Julian Day of birth
            levels: Depth of sub-periods (1=Maha only, 2=+Antar, 3=+Pratyantara)

        Returns:
            Complete DashaTimeline with periods and sub-periods.
        """
        # Determine Moon's nakshatra
        nakshatra_num = int(moon_longitude / NAKSHATRA_SPAN)
        if nakshatra_num >= 27:
            nakshatra_num = 26
        degree_in_nakshatra = moon_longitude % NAKSHATRA_SPAN

        # Starting lord (from nakshatra lord cycle)
        lord_index = nakshatra_num % 9
        starting_lord = VIMSHOTTARI_ORDER[lord_index]

        # Balance at birth: proportion of the first dasha remaining
        proportion_elapsed = degree_in_nakshatra / NAKSHATRA_SPAN
        first_lord_years = VIMSHOTTARI_YEARS[starting_lord]
        balance_years = first_lord_years * (1.0 - proportion_elapsed)

        # Build timeline
        timeline = []
        current_jd = birth_jd

        # Generate enough dashas to cover ~120+ years
        for cycle_offset in range(18):  # 18 dashas covers 2 full cycles
            idx = (lord_index + cycle_offset) % 9
            lord = VIMSHOTTARI_ORDER[idx]
            total_years = VIMSHOTTARI_YEARS[lord]

            if cycle_offset == 0:
                years = balance_years
                is_balance = True
            else:
                years = float(total_years)
                is_balance = False

            days = years * self.DAYS_PER_YEAR
            end_jd = current_jd + days

            # Compute sub-periods if requested
            sub_periods = []
            if levels >= 2:
                sub_periods = self._compute_sub_periods(
                    lord, years, current_jd, level=2, max_level=levels
                )

            period = DashaPeriod(
                lord=lord,
                start_date=self._jd_to_date(current_jd),
                end_date=self._jd_to_date(end_jd),
                start_jd=round(current_jd, 6),
                end_jd=round(end_jd, 6),
                years=round(years, 4),
                is_balance=is_balance,
                sub_periods=sub_periods,
            )
            timeline.append(period)
            current_jd = end_jd

        from jyotisha.constants import NAKSHATRA_NAMES
        return DashaTimeline(
            system="Vimshottari",
            birth_nakshatra=NAKSHATRA_NAMES[nakshatra_num],
            birth_nakshatra_lord=starting_lord,
            balance_at_birth={
                "lord": starting_lord,
                "remaining_years": round(balance_years, 4),
                "total_years": first_lord_years,
                "elapsed_fraction": round(proportion_elapsed, 4),
            },
            timeline=timeline,
        )

    def compute_vimshottari_from_chart(
        self,
        chart: Chart,
        levels: int = 2,
    ) -> DashaTimeline:
        """Convenience method to compute Vimshottari from a Chart object."""
        moon = chart.get_planet("Moon")
        if moon is None:
            raise ValueError("Moon position not found in chart")

        if chart.birth_event is None:
            raise ValueError("Chart has no birth event data")

        return self.compute_vimshottari(
            moon_longitude=moon.longitude,
            birth_jd=chart.birth_event.julian_day,
            levels=levels,
        )

    def compute_chara_dasha(self, chart: Chart) -> DashaTimeline:
        """
        Compute Jaimini Chara Dasha.
        Sign-based dasha.
        Direct sequence for odd signs: Asc, 2nd, 3rd...
        Reverse sequence for even signs: Asc, 12th, 11th...
        Duration = Count from sign to its lord (direct/reverse) - 1. 
        If lord in own sign, 12 years.
        """
        if chart.birth_event is None:
            raise ValueError("Chart has no birth event data")
            
        asc_sign_num = chart.ascendant.sign_number
        is_odd = asc_sign_num % 2 == 0  # 0 is Aries (1st sign -> odd)
        
        sequence = []
        for i in range(12):
            if is_odd:
                sequence.append((asc_sign_num + i) % 12)
            else:
                sequence.append((asc_sign_num - i) % 12)
                
        timeline = []
        current_jd = chart.birth_event.julian_day
        
        from jyotisha.constants import SIGN_NAMES
        
        for sign_num in sequence:
            sign_name = SIGN_NAMES[sign_num]
            
            # Find lord
            from jyotisha.constants import SIGN_LORDS
            lord_planet_name = SIGN_LORDS.get(sign_num)
            
            lord_pos = chart.get_planet(lord_planet_name)
            
            if lord_pos is None or lord_pos.sign_number == sign_num:
                years = 12
            else:
                lord_sign_num = lord_pos.sign_number
                sign_is_odd = sign_num % 2 == 0
                
                if sign_is_odd:
                    # Direct count
                    count = ((lord_sign_num - sign_num) % 12) + 1
                else:
                    # Reverse count
                    count = ((sign_num - lord_sign_num) % 12) + 1
                    
                years = count - 1
                if years == 0:
                    years = 12
                    
            days = years * self.DAYS_PER_YEAR
            end_jd = current_jd + days
            
            period = DashaPeriod(
                lord=sign_name,
                start_date=self._jd_to_date(current_jd),
                end_date=self._jd_to_date(end_jd),
                start_jd=round(current_jd, 6),
                end_jd=round(end_jd, 6),
                years=float(years),
                is_balance=False,
                sub_periods=[],
            )
            timeline.append(period)
            current_jd = end_jd
            
        return DashaTimeline(
            system="Chara Dasha",
            birth_nakshatra=chart.ascendant.sign,  # Not really nakshatra but ascendant sign
            birth_nakshatra_lord=SIGN_NAMES[asc_sign_num],
            balance_at_birth={},
            timeline=timeline
        )

    def compute_yogini_dasha(self, chart: Chart) -> DashaTimeline:
        """
        Compute Yogini Dasha.
        36-year cycle based on Moon's nakshatra.
        (Nakshatra + 3) % 8 -> determines starting dasha.
        """
        moon = chart.get_planet("Moon")
        if moon is None or chart.birth_event is None:
            raise ValueError("Moon or birth event missing")
            
        nakshatra_num = moon.nakshatra_number + 1  # 1-indexed (Ashwini=1)
        
        yogini_order = [
            ("Mangala", 1, "Moon"),
            ("Pingala", 2, "Sun"),
            ("Dhanya", 3, "Jupiter"),
            ("Bhramari", 4, "Mars"),
            ("Bhadrika", 5, "Mercury"),
            ("Ulka", 6, "Saturn"),
            ("Siddha", 7, "Venus"),
            ("Sankata", 8, "Rahu"),
        ]
        
        remainder = (nakshatra_num + 3) % 8
        if remainder == 0:
            remainder = 8
            
        start_idx = remainder - 1
        
        # Balance
        degree_in_nakshatra = moon.longitude % 13.333333
        proportion_elapsed = degree_in_nakshatra / 13.333333
        first_lord_years = yogini_order[start_idx][1]
        balance_years = first_lord_years * (1.0 - proportion_elapsed)
        
        timeline = []
        current_jd = chart.birth_event.julian_day
        
        for cycle_offset in range(16): # roughly 16*4.5 = 72 periods, covers over 100 years
            idx = (start_idx + cycle_offset) % 8
            y_name, total_years, lord = yogini_order[idx]
            
            if cycle_offset == 0:
                years = balance_years
                is_balance = True
            else:
                years = float(total_years)
                is_balance = False
                
            days = years * self.DAYS_PER_YEAR
            end_jd = current_jd + days
            
            period = DashaPeriod(
                lord=f"{y_name} ({lord})",
                start_date=self._jd_to_date(current_jd),
                end_date=self._jd_to_date(end_jd),
                start_jd=round(current_jd, 6),
                end_jd=round(end_jd, 6),
                years=round(years, 4),
                is_balance=is_balance,
                sub_periods=[],
            )
            timeline.append(period)
            current_jd = end_jd
            
        return DashaTimeline(
            system="Yogini",
            birth_nakshatra=moon.nakshatra,
            birth_nakshatra_lord=yogini_order[start_idx][2],
            balance_at_birth={
                "lord": yogini_order[start_idx][0],
                "remaining_years": round(balance_years, 4),
            },
            timeline=timeline
        )

    def compute_narayana_dasha(self, chart: Chart) -> DashaTimeline:
        """
        Compute Narayana Dasha.
        Advanced Jaimini sign-based dasha.
        Currently a simplified placeholder (uses Chara Dasha logic as a base).
        Full implementation requires Chara Bala (sign strength) to determine
        starting sign (Ascendant vs 7th) and direction.
        """
        # For now, fallback to Chara Dasha logic, but label it Narayana
        # as a placeholder for the advanced implementation.
        base_chara = self.compute_chara_dasha(chart)
        base_chara.system = "Narayana (Simplified)"
        return base_chara

    def get_current_dasha(
        self,
        dasha_timeline: DashaTimeline,
        query_jd: float,
    ) -> dict:
        """
        Find the active dasha at a given Julian Day.

        Returns dict with current Mahadasha, Antardasha, etc.
        """
        result = {}

        for period in dasha_timeline.timeline:
            start_jd = period.start_jd
            end_jd = period.end_jd

            if start_jd <= query_jd < end_jd:
                result["mahadasha"] = {
                    "lord": period.lord,
                    "start": period.start_date,
                    "end": period.end_date,
                    "years": period.years,
                }

                # Check sub-periods
                for sub in period.sub_periods:
                    sub_start = sub.start_jd
                    sub_end = sub.end_jd

                    if sub_start <= query_jd < sub_end:
                        result["antardasha"] = {
                            "lord": sub.lord,
                            "start": sub.start_date,
                            "end": sub.end_date,
                            "years": sub.years,
                        }

                        for subsub in sub.sub_periods:
                            ss_start = subsub.start_jd
                            ss_end = subsub.end_jd
                            if ss_start <= query_jd < ss_end:
                                result["pratyantardasha"] = {
                                    "lord": subsub.lord,
                                    "start": subsub.start_date,
                                    "end": subsub.end_date,
                                    "years": subsub.years,
                                }
                                break
                        break
                break

        return result

    # ─────────────────────────────────────────────────────────
    # Sub-period computation
    # ─────────────────────────────────────────────────────────

    def _compute_sub_periods(
        self,
        parent_lord: Planet,
        parent_years: float,
        start_jd: float,
        level: int = 2,
        max_level: int = 2,
    ) -> list[DashaPeriod]:
        """
        Compute sub-periods within a dasha period.

        Sub-periods cycle through the Vimshottari order starting from
        the parent period's lord.
        """
        parent_idx = VIMSHOTTARI_ORDER.index(parent_lord)
        sub_periods = []
        current_jd = start_jd

        for i in range(9):
            sub_lord = VIMSHOTTARI_ORDER[(parent_idx + i) % 9]
            sub_lord_years = VIMSHOTTARI_YEARS[sub_lord]

            # Sub-period proportion = (sub_lord_years * parent_years) / total_years
            sub_years = (sub_lord_years * parent_years) / VIMSHOTTARI_TOTAL_YEARS
            sub_days = sub_years * self.DAYS_PER_YEAR
            end_jd = current_jd + sub_days

            # Recurse for deeper levels
            deeper_subs = []
            if level < max_level:
                deeper_subs = self._compute_sub_periods(
                    sub_lord, sub_years, current_jd,
                    level=level + 1, max_level=max_level,
                )

            sub_periods.append(DashaPeriod(
                lord=sub_lord,
                start_date=self._jd_to_date(current_jd),
                end_date=self._jd_to_date(end_jd),
                start_jd=round(current_jd, 6),
                end_jd=round(end_jd, 6),
                years=round(sub_years, 4),
                sub_periods=deeper_subs,
            ))
            current_jd = end_jd

        return sub_periods

    # ─────────────────────────────────────────────────────────
    # Date helpers
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def _jd_to_date(jd: float) -> str:
        """Convert Julian Day to ISO date string."""
        try:
            import swisseph as swe
            year, month, day, hour = swe.revjul(jd)
            return f"{year:04d}-{month:02d}-{day:02d}"
        except ImportError:
            # Fallback: manual conversion
            z = int(jd + 0.5)
            if z < 2299161:
                a = z
            else:
                alpha = int((z - 1867216.25) / 36524.25)
                a = z + 1 + alpha - int(alpha / 4)
            b = a + 1524
            c = int((b - 122.1) / 365.25)
            d = int(365.25 * c)
            e = int((b - d) / 30.6001)

            day = b - d - int(30.6001 * e)
            month = e - 1 if e < 14 else e - 13
            year = c - 4716 if month > 2 else c - 4715

            return f"{year:04d}-{month:02d}-{day:02d}"

    @staticmethod
    def _date_to_jd(date_str: str) -> float:
        """Convert ISO date string to Julian Day."""
        try:
            import swisseph as swe
            parts = date_str.split("-")
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            return swe.julday(year, month, day, 0.0)
        except (ImportError, Exception):
            # Fallback
            parts = date_str.split("-")
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            if m <= 2:
                y -= 1
                m += 12
            A = int(y / 100)
            B = 2 - A + int(A / 4)
            return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + B - 1524.5

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
        # Note: VIMSHOTTARI_ORDER starts with Ketu at index 0 (Ashwini).
        # E.g., Revati is index 26. 26 % 9 = 8 (Mercury), which is correct.
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
        # Note: 0 is Aries, so 0 % 2 == 0 evaluates to True.
        # This correctly designates Aries as an Odd sign in Jyotish.
        # 1 is Taurus (False -> Even).
        is_odd = asc_sign_num % 2 == 0
        
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
            from jyotisha.constants import SIGN_LORDS, Sign
            lord_planet_name = SIGN_LORDS.get(Sign(sign_num)).value
            
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
        degree_in_nakshatra = moon.longitude % NAKSHATRA_SPAN
        proportion_elapsed = degree_in_nakshatra / NAKSHATRA_SPAN
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

    def _compare_jaimini_sign_strength(self, chart: Chart, sign_a: int, sign_b: int) -> int:
        """
        Compares the Jaimini strength of two signs (0-11).
        Returns:
            1 if sign_a is stronger,
            -1 if sign_b is stronger,
            0 if they are tied.
        """
        # 1. Number of planets in each sign
        planets_in_a = [p for p in chart.planets if p.sign_number == sign_a]
        planets_in_b = [p for p in chart.planets if p.sign_number == sign_b]
        
        if len(planets_in_a) != len(planets_in_b):
            return 1 if len(planets_in_a) > len(planets_in_b) else -1
            
        # 2. Presence of Jupiter, Mercury, or sign lord in the sign
        from jyotisha.constants import SIGN_LORDS, Sign, Planet
        lord_a_name = SIGN_LORDS[Sign(sign_a)].value
        lord_b_name = SIGN_LORDS[Sign(sign_b)].value
        
        score_a = 0
        score_b = 0
        for p in planets_in_a:
            if p.name in [Planet.JUPITER, Planet.MERCURY, lord_a_name]:
                score_a += 1
        for p in planets_in_b:
            if p.name in [Planet.JUPITER, Planet.MERCURY, lord_b_name]:
                score_b += 1
                
        if score_a != score_b:
            return 1 if score_a > score_b else -1
            
        # 3. Check Jaimini aspects (Rashi Drishti) from Jupiter, Mercury, or sign lord
        def sign_aspects_sign(s1: int, s2: int) -> bool:
            if s1 == s2:
                return True
            from jyotisha.constants import SIGN_MODALITIES, Modality
            m1 = SIGN_MODALITIES[s1]
            m2 = SIGN_MODALITIES[s2]
            if m1 == Modality.MOVABLE and m2 == Modality.FIXED:
                return s2 != (s1 + 1) % 12
            if m1 == Modality.FIXED and m2 == Modality.MOVABLE:
                return s2 != (s1 - 1) % 12
            if m1 == Modality.DUAL and m2 == Modality.DUAL:
                return s1 != s2
            return False
            
        aspect_score_a = 0
        aspect_score_b = 0
        for p in chart.planets:
            if p.sign_number != sign_a and sign_aspects_sign(p.sign_number, sign_a):
                if p.name in [Planet.JUPITER, Planet.MERCURY, lord_a_name]:
                    aspect_score_a += 1
            if p.sign_number != sign_b and sign_aspects_sign(p.sign_number, sign_b):
                if p.name in [Planet.JUPITER, Planet.MERCURY, lord_b_name]:
                    aspect_score_b += 1
                    
        if aspect_score_a != aspect_score_b:
            return 1 if aspect_score_a > aspect_score_b else -1
            
        # 4. Compare degrees of sign lords in their signs
        lord_a_obj = chart.get_planet(lord_a_name)
        lord_b_obj = chart.get_planet(lord_b_name)
        
        deg_a = lord_a_obj.degree_in_sign if lord_a_obj else 0.0
        deg_b = lord_b_obj.degree_in_sign if lord_b_obj else 0.0
        
        if deg_a != deg_b:
            return 1 if deg_a > deg_b else -1
            
        return 0

    def _get_jaimini_sign_lord(self, chart: Chart, sign_num: int) -> str:
        from jyotisha.constants import SIGN_LORDS, Sign, Planet
        default_lord = SIGN_LORDS[Sign(sign_num)].value
        
        if sign_num == 7: # Scorpio
            p1 = chart.get_planet("Mars")
            p2 = chart.get_planet("Ketu")
            if p1 and p2:
                if p1.sign_number == 7 and p2.sign_number != 7:
                    return "Ketu"
                elif p2.sign_number == 7 and p1.sign_number != 7:
                    return "Mars"
                else:
                    planets_with_mars = len([p for p in chart.planets if p.sign_number == p1.sign_number])
                    planets_with_ketu = len([p for p in chart.planets if p.sign_number == p2.sign_number])
                    if planets_with_mars != planets_with_ketu:
                        return "Mars" if planets_with_mars > planets_with_ketu else "Ketu"
                    return "Mars" if p1.degree_in_sign >= p2.degree_in_sign else "Ketu"
        elif sign_num == 10: # Aquarius
            p1 = chart.get_planet("Saturn")
            p2 = chart.get_planet("Rahu")
            if p1 and p2:
                if p1.sign_number == 10 and p2.sign_number != 10:
                    return "Rahu"
                elif p2.sign_number == 10 and p1.sign_number != 10:
                    return "Saturn"
                else:
                    planets_with_saturn = len([p for p in chart.planets if p.sign_number == p1.sign_number])
                    planets_with_rahu = len([p for p in chart.planets if p.sign_number == p2.sign_number])
                    if planets_with_saturn != planets_with_rahu:
                        return "Saturn" if planets_with_saturn > planets_with_rahu else "Rahu"
                    return "Saturn" if p1.degree_in_sign >= p2.degree_in_sign else "Rahu"
        elif sign_num == 11: # Pisces
            p1 = chart.get_planet("Jupiter")
            p2 = chart.get_planet("Ketu")
            if p1 and p2:
                if p1.sign_number == 11 and p2.sign_number != 11:
                    return "Ketu"
                elif p2.sign_number == 11 and p1.sign_number != 11:
                    return "Jupiter"
                else:
                    planets_with_jup = len([p for p in chart.planets if p.sign_number == p1.sign_number])
                    planets_with_ketu = len([p for p in chart.planets if p.sign_number == p2.sign_number])
                    if planets_with_jup != planets_with_ketu:
                        return "Jupiter" if planets_with_jup > planets_with_ketu else "Ketu"
                    return "Jupiter" if p1.degree_in_sign >= p2.degree_in_sign else "Ketu"
                    
        return default_lord

    def _get_exalt_deb_adjustment(self, lord_name: str, lord_sign: int) -> int:
        exalt_signs = {
            "Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5, "Jupiter": 3, "Venus": 11, "Saturn": 6, "Rahu": 1, "Ketu": 7
        }
        deb_signs = {
            "Sun": 6, "Moon": 7, "Mars": 3, "Mercury": 11, "Jupiter": 9, "Venus": 5, "Saturn": 0, "Rahu": 7, "Ketu": 1
        }
        if exalt_signs.get(lord_name) == lord_sign:
            return 1
        if deb_signs.get(lord_name) == lord_sign:
            return -1
        return 0

    def compute_narayana_dasha(self, chart: Chart) -> DashaTimeline:
        """
        Compute Narayana Dasha.
        Advanced Jaimini sign-based dasha.
        Determines the stronger sign between Lagna and 7th house,
        direction based on 9th from starting sign (with Saturn/Ketu overrides),
        and applies progression rules by modality (Chara, Sthira, Dvisvabhava).
        """
        if chart.birth_event is None:
            raise ValueError("Chart has no birth event data")
            
        asc_sign_num = chart.ascendant.sign_number
        desc_sign_num = (asc_sign_num + 6) % 12
        
        # Determine starting sign (stronger of 1st and 7th)
        comp = self._compare_jaimini_sign_strength(chart, asc_sign_num, desc_sign_num)
        start_sign = asc_sign_num if comp >= 0 else desc_sign_num
        
        # Footedness lists
        odd_footed = [0, 1, 2, 6, 7, 8]
        even_footed = [3, 4, 5, 9, 10, 11]
        
        # Find 9th house from start_sign
        if start_sign in odd_footed:
            ninth_house = (start_sign + 8) % 12
        else:
            ninth_house = (start_sign - 8) % 12
            
        # Direction determined by 9th house footedness
        dir_val = 1 if ninth_house in odd_footed else -1
        
        # Planet-based overrides
        saturn_in_start = any(p.name == Planet.SATURN and p.sign_number == start_sign for p in chart.planets)
        ketu_in_start = any(p.name == Planet.KETU and p.sign_number == start_sign for p in chart.planets)
        
        if saturn_in_start:
            dir_val = 1
        elif ketu_in_start:
            dir_val = -dir_val
            
        # Modality sequence
        modality = start_sign % 3
        sequence = []
        if modality == 0:  # Chara (Movable)
            sequence = [(start_sign + k * dir_val) % 12 for k in range(12)]
        elif modality == 1:  # Sthira (Fixed)
            sequence = [(start_sign + 5 * k * dir_val) % 12 for k in range(12)]
        else:  # Dvisvabhava (Dual)
            offsets = [0, 4, 8, 1, 5, 9, 2, 6, 10, 3, 7, 11]
            sequence = [(start_sign + offsets[k] * dir_val) % 12 for k in range(12)]
            
        timeline = []
        current_jd = chart.birth_event.julian_day
        from jyotisha.constants import SIGN_NAMES
        
        for sign_num in sequence:
            sign_name = SIGN_NAMES[sign_num]
            lord_name = self._get_jaimini_sign_lord(chart, sign_num)
            lord_planet = chart.get_planet(lord_name)
            
            if lord_planet is None or lord_planet.sign_number == sign_num:
                years = 12
            else:
                lord_sign_num = lord_planet.sign_number
                sign_is_odd_footed = sign_num in odd_footed
                
                if sign_is_odd_footed:
                    count = ((lord_sign_num - sign_num) % 12) + 1
                else:
                    count = ((sign_num - lord_sign_num) % 12) + 1
                    
                years = count - 1
                if years == 0:
                    years = 12
                else:
                    # Apply exaltation/debilitation adjustment
                    adj = self._get_exalt_deb_adjustment(lord_name, lord_sign_num)
                    years = max(1, min(12, years + adj))
                    
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
            system="Narayana Dasha",
            birth_nakshatra=chart.ascendant.sign,
            birth_nakshatra_lord=SIGN_NAMES[asc_sign_num],
            balance_at_birth={},
            timeline=timeline
        )

    def get_28_nakshatra_info(self, longitude: float) -> tuple[int, float]:
        """
        Returns the 28-nakshatra index (0 to 27) and the fraction elapsed (0.0 to 1.0)
        for a given sidereal longitude.
        Includes Abhijit at index 21 (between Uttara Ashadha 20 and Shravana 22).
        """
        lon = float(longitude) % 360.0
        if lon < 266.666667:
            span = 360.0 / 27.0
            idx = int(lon / span)
            elapsed = lon % span
            return idx, elapsed / span
        elif lon < 276.666667:
            # Uttara Ashadha (reduced span)
            span = 10.0
            elapsed = lon - 266.666667
            return 20, elapsed / span
        elif lon < 280.888889:
            # Abhijit
            span = 4.222222
            elapsed = lon - 276.666667
            return 21, elapsed / span
        elif lon < 293.333333:
            # Shravana (reduced span)
            span = 12.444444
            elapsed = lon - 280.888889
            return 22, elapsed / span
        else:
            offset_lon = lon - 293.333333
            span = 360.0 / 27.0
            sub_idx = int(offset_lon / span)
            idx = 23 + sub_idx
            elapsed = offset_lon % span
            return idx, elapsed / span

    def compute_ashtottari_dasha(self, chart: Chart, levels: int = 2) -> DashaTimeline:
        """
        Compute Ashtottari Dasha (108 years).
        Uses 28 nakshatras (including Abhijit).
        Ketu is excluded.
        Starts from Ardra if any planet is in Lagna, else Krittika.
        """
        moon = chart.get_planet("Moon")
        if moon is None or chart.birth_event is None:
            raise ValueError("Moon or birth event missing")
            
        planet_in_lagna = any(p.house == 1 for p in chart.planets)
        start_nak_idx = 5 if planet_in_lagna else 2 # 0-indexed (Ardra=5, Krittika=2)
        
        moon_nak_idx, fraction = self.get_28_nakshatra_info(moon.longitude)
        count = (moon_nak_idx - start_nak_idx) % 28
        
        sizes = [4, 3, 4, 3, 4, 3, 4, 3]
        planets_order = ["Sun", "Moon", "Mars", "Mercury", "Saturn", "Jupiter", "Rahu", "Venus"]
        durations = {"Sun": 6, "Moon": 15, "Mars": 8, "Mercury": 17, "Saturn": 10, "Jupiter": 19, "Rahu": 12, "Venus": 21}
        
        accum = 0
        starting_planet_idx = 0
        for p_idx, size in enumerate(sizes):
            if accum <= count < accum + size:
                starting_planet_idx = p_idx
                break
            accum += size
            
        timeline = []
        current_jd = chart.birth_event.julian_day
        
        for cycle_offset in range(16):
            idx = (starting_planet_idx + cycle_offset) % 8
            lord = planets_order[idx]
            total_years = durations[lord]
            
            if cycle_offset == 0:
                years = total_years * (1.0 - fraction)
                is_balance = True
            else:
                years = float(total_years)
                is_balance = False
                
            days = years * self.DAYS_PER_YEAR
            end_jd = current_jd + days
            
            sub_periods = []
            if levels >= 2:
                sub_periods = self._compute_ashtottari_sub_periods(
                    lord, years, current_jd, levels
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
        birth_nak_name = "Abhijit" if moon_nak_idx == 21 else NAKSHATRA_NAMES[moon_nak_idx if moon_nak_idx < 21 else moon_nak_idx - 1]
        
        return DashaTimeline(
            system="Ashtottari",
            birth_nakshatra=birth_nak_name,
            birth_nakshatra_lord=planets_order[starting_planet_idx],
            balance_at_birth={
                "lord": planets_order[starting_planet_idx],
                "remaining_years": round(durations[planets_order[starting_planet_idx]] * (1.0 - fraction), 4),
            },
            timeline=timeline
        )

    def _compute_ashtottari_sub_periods(
        self,
        parent_lord: str,
        parent_years: float,
        start_jd: float,
        max_level: int = 2,
    ) -> list[DashaPeriod]:
        planets_order = ["Sun", "Moon", "Mars", "Mercury", "Saturn", "Jupiter", "Rahu", "Venus"]
        durations = {"Sun": 6, "Moon": 15, "Mars": 8, "Mercury": 17, "Saturn": 10, "Jupiter": 19, "Rahu": 12, "Venus": 21}
        
        parent_idx = planets_order.index(parent_lord)
        sub_periods = []
        current_jd = start_jd
        
        for i in range(8):
            sub_lord = planets_order[(parent_idx + i) % 8]
            sub_lord_years = durations[sub_lord]
            
            sub_years = (sub_lord_years * parent_years) / 108.0
            sub_days = sub_years * self.DAYS_PER_YEAR
            end_jd = current_jd + sub_days
            
            sub_periods.append(DashaPeriod(
                lord=sub_lord,
                start_date=self._jd_to_date(current_jd),
                end_date=self._jd_to_date(end_jd),
                start_jd=round(current_jd, 6),
                end_jd=round(end_jd, 6),
                years=round(sub_years, 4),
                sub_periods=[],
            ))
            current_jd = end_jd
            
        return sub_periods

    def compute_dwisaptati_dasha(self, chart: Chart, levels: int = 2) -> DashaTimeline:
        """
        Compute Dwisaptati Dasha (72 years).
        8 planets (excluding Ketu), each 9 years.
        Starts from Mula.
        """
        moon = chart.get_planet("Moon")
        if moon is None or chart.birth_event is None:
            raise ValueError("Moon or birth event missing")
            
        moon_nak_idx = moon.nakshatra_number
        degree_in_nakshatra = moon.longitude % NAKSHATRA_SPAN
        fraction = degree_in_nakshatra / NAKSHATRA_SPAN
        
        # Mula is the 19th nakshatra (index 18)
        count = (moon_nak_idx - 18) % 27 + 1
        starting_planet_idx = (count - 1) % 8
        
        planets_order = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"]
        
        timeline = []
        current_jd = chart.birth_event.julian_day
        
        for cycle_offset in range(16):
            idx = (starting_planet_idx + cycle_offset) % 8
            lord = planets_order[idx]
            total_years = 9.0
            
            if cycle_offset == 0:
                years = total_years * (1.0 - fraction)
                is_balance = True
            else:
                years = float(total_years)
                is_balance = False
                
            days = years * self.DAYS_PER_YEAR
            end_jd = current_jd + days
            
            sub_periods = []
            if levels >= 2:
                sub_periods = self._compute_dwisaptati_sub_periods(
                    lord, years, current_jd
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
            
        return DashaTimeline(
            system="Dwisaptati",
            birth_nakshatra=moon.nakshatra,
            birth_nakshatra_lord=planets_order[starting_planet_idx],
            balance_at_birth={
                "lord": planets_order[starting_planet_idx],
                "remaining_years": round(9.0 * (1.0 - fraction), 4),
            },
            timeline=timeline
        )

    def _compute_dwisaptati_sub_periods(
        self,
        parent_lord: str,
        parent_years: float,
        start_jd: float,
    ) -> list[DashaPeriod]:
        planets_order = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"]
        parent_idx = planets_order.index(parent_lord)
        sub_periods = []
        current_jd = start_jd
        
        for i in range(8):
            sub_lord = planets_order[(parent_idx + i) % 8]
            sub_years = parent_years / 8.0
            sub_days = sub_years * self.DAYS_PER_YEAR
            end_jd = current_jd + sub_days
            
            sub_periods.append(DashaPeriod(
                lord=sub_lord,
                start_date=self._jd_to_date(current_jd),
                end_date=self._jd_to_date(end_jd),
                start_jd=round(current_jd, 6),
                end_jd=round(end_jd, 6),
                years=round(sub_years, 4),
                sub_periods=[],
            ))
            current_jd = end_jd
            
        return sub_periods

    def compute_shodashottari_dasha(self, chart: Chart, levels: int = 2) -> DashaTimeline:
        """
        Compute Shodashottari Dasha (116 years).
        9 planets (including Ketu), starting from Pushya.
        """
        moon = chart.get_planet("Moon")
        if moon is None or chart.birth_event is None:
            raise ValueError("Moon or birth event missing")
            
        moon_nak_idx = moon.nakshatra_number
        degree_in_nakshatra = moon.longitude % NAKSHATRA_SPAN
        fraction = degree_in_nakshatra / NAKSHATRA_SPAN
        
        # Pushya is the 8th nakshatra (index 7)
        count = (moon_nak_idx - 7) % 27 + 1
        starting_planet_idx = (count - 1) // 3
        
        planets_order = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        durations = {"Sun": 11, "Moon": 9, "Mars": 8, "Mercury": 9, "Jupiter": 10, "Venus": 21, "Saturn": 12, "Rahu": 18, "Ketu": 18}
        
        timeline = []
        current_jd = chart.birth_event.julian_day
        
        for cycle_offset in range(18): # 18 periods covers 2 full cycles
            idx = (starting_planet_idx + cycle_offset) % 9
            lord = planets_order[idx]
            total_years = durations[lord]
            
            if cycle_offset == 0:
                years = total_years * (1.0 - fraction)
                is_balance = True
            else:
                years = float(total_years)
                is_balance = False
                
            days = years * self.DAYS_PER_YEAR
            end_jd = current_jd + days
            
            sub_periods = []
            if levels >= 2:
                sub_periods = self._compute_shodashottari_sub_periods(
                    lord, years, current_jd
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
            
        return DashaTimeline(
            system="Shodashottari",
            birth_nakshatra=moon.nakshatra,
            birth_nakshatra_lord=planets_order[starting_planet_idx],
            balance_at_birth={
                "lord": planets_order[starting_planet_idx],
                "remaining_years": round(durations[planets_order[starting_planet_idx]] * (1.0 - fraction), 4),
            },
            timeline=timeline
        )

    def _compute_shodashottari_sub_periods(
        self,
        parent_lord: str,
        parent_years: float,
        start_jd: float,
    ) -> list[DashaPeriod]:
        planets_order = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        durations = {"Sun": 11, "Moon": 9, "Mars": 8, "Mercury": 9, "Jupiter": 10, "Venus": 21, "Saturn": 12, "Rahu": 18, "Ketu": 18}
        parent_idx = planets_order.index(parent_lord)
        sub_periods = []
        current_jd = start_jd
        
        for i in range(9):
            sub_lord = planets_order[(parent_idx + i) % 9]
            sub_lord_years = durations[sub_lord]
            
            sub_years = (sub_lord_years * parent_years) / 116.0
            sub_days = sub_years * self.DAYS_PER_YEAR
            end_jd = current_jd + sub_days
            
            sub_periods.append(DashaPeriod(
                lord=sub_lord,
                start_date=self._jd_to_date(current_jd),
                end_date=self._jd_to_date(end_jd),
                start_jd=round(current_jd, 6),
                end_jd=round(end_jd, 6),
                years=round(sub_years, 4),
                sub_periods=[],
            ))
            current_jd = end_jd
            
        return sub_periods

    def compute_panchottari_dasha(self, chart: Chart, levels: int = 2) -> DashaTimeline:
        """
        Compute Panchottari Dasha (105 years).
        7 planets (excluding Rahu & Ketu), starting from Anuradha.
        """
        moon = chart.get_planet("Moon")
        if moon is None or chart.birth_event is None:
            raise ValueError("Moon or birth event missing")
            
        moon_nak_idx = moon.nakshatra_number
        degree_in_nakshatra = moon.longitude % NAKSHATRA_SPAN
        fraction = degree_in_nakshatra / NAKSHATRA_SPAN
        
        # Anuradha is the 17th nakshatra (index 16)
        count = (moon_nak_idx - 16) % 27 + 1
        starting_planet_idx = (count - 1) % 7
        
        planets_order = ["Sun", "Mercury", "Saturn", "Mars", "Venus", "Moon", "Jupiter"]
        durations = {"Sun": 12, "Mercury": 13, "Saturn": 14, "Mars": 15, "Venus": 16, "Moon": 17, "Jupiter": 18}
        
        timeline = []
        current_jd = chart.birth_event.julian_day
        
        for cycle_offset in range(14): # covers 2 cycles
            idx = (starting_planet_idx + cycle_offset) % 7
            lord = planets_order[idx]
            total_years = durations[lord]
            
            if cycle_offset == 0:
                years = total_years * (1.0 - fraction)
                is_balance = True
            else:
                years = float(total_years)
                is_balance = False
                
            days = years * self.DAYS_PER_YEAR
            end_jd = current_jd + days
            
            sub_periods = []
            if levels >= 2:
                sub_periods = self._compute_panchottari_sub_periods(
                    lord, years, current_jd
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
            
        return DashaTimeline(
            system="Panchottari",
            birth_nakshatra=moon.nakshatra,
            birth_nakshatra_lord=planets_order[starting_planet_idx],
            balance_at_birth={
                "lord": planets_order[starting_planet_idx],
                "remaining_years": round(durations[planets_order[starting_planet_idx]] * (1.0 - fraction), 4),
            },
            timeline=timeline
        )

    def _compute_panchottari_sub_periods(
        self,
        parent_lord: str,
        parent_years: float,
        start_jd: float,
    ) -> list[DashaPeriod]:
        planets_order = ["Sun", "Mercury", "Saturn", "Mars", "Venus", "Moon", "Jupiter"]
        durations = {"Sun": 12, "Mercury": 13, "Saturn": 14, "Mars": 15, "Venus": 16, "Moon": 17, "Jupiter": 18}
        parent_idx = planets_order.index(parent_lord)
        sub_periods = []
        current_jd = start_jd
        
        for i in range(7):
            sub_lord = planets_order[(parent_idx + i) % 7]
            sub_lord_years = durations[sub_lord]
            
            sub_years = (sub_lord_years * parent_years) / 105.0
            sub_days = sub_years * self.DAYS_PER_YEAR
            end_jd = current_jd + sub_days
            
            sub_periods.append(DashaPeriod(
                lord=sub_lord,
                start_date=self._jd_to_date(current_jd),
                end_date=self._jd_to_date(end_jd),
                start_jd=round(current_jd, 6),
                end_jd=round(end_jd, 6),
                years=round(sub_years, 4),
                sub_periods=[],
            ))
            current_jd = end_jd
            
        return sub_periods

    def compute_naisargika_dasha(self, chart: Chart) -> DashaTimeline:
        """
        Compute Naisargika Dasha (Natural life stages, 120 years).
        Universal fixed timeline:
        - Moon: 1 year (Age 0-1)
        - Mars: 2 years (Age 1-3)
        - Mercury: 9 years (Age 3-12)
        - Venus: 20 years (Age 12-32)
        - Jupiter: 18 years (Age 32-50)
        - Sun: 20 years (Age 50-70)
        - Saturn: 50 years (Age 70-120)
        """
        if chart.birth_event is None:
            raise ValueError("Birth event missing")
            
        planets_order = ["Moon", "Mars", "Mercury", "Venus", "Jupiter", "Sun", "Saturn"]
        durations = [1.0, 2.0, 9.0, 20.0, 18.0, 20.0, 50.0]
        
        timeline = []
        current_jd = chart.birth_event.julian_day
        
        for idx, lord in enumerate(planets_order):
            years = durations[idx]
            days = years * self.DAYS_PER_YEAR
            end_jd = current_jd + days
            
            period = DashaPeriod(
                lord=lord,
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
            system="Naisargika",
            birth_nakshatra=chart.ascendant.sign,
            birth_nakshatra_lord="Ascendant",
            balance_at_birth={},
            timeline=timeline
        )

    def compute_kalachakra_dasha(self, chart: Chart, levels: int = 2) -> DashaTimeline:
        """
        Compute Kalachakra Dasha.
        Determines the Savya/Apasavya cycle from Moon's nakshatra,
        sets the sequence of 9 signs based on nakshatra pada,
        and computes durations and sub-periods (bhuktis).
        """
        moon = chart.get_planet("Moon")
        if moon is None or chart.birth_event is None:
            raise ValueError("Moon or birth event missing")

        from jyotisha.constants import NAKSHATRA_SPAN, NAKSHATRA_NAMES
        
        moon_longitude = moon.longitude
        nak_idx = int(moon_longitude / NAKSHATRA_SPAN)
        if nak_idx >= 27:
            nak_idx = 26
            
        deg_in_nak = moon_longitude % NAKSHATRA_SPAN
        pada_span = NAKSHATRA_SPAN / 4.0
        pada_idx = int(deg_in_nak / pada_span)
        if pada_idx >= 4:
            pada_idx = 3
        pada_num = pada_idx + 1
        fraction = (deg_in_nak % pada_span) / pada_span

        is_savya = (nak_idx // 3) % 2 == 0

        SAVYA_SEQUENCES = {
            1: ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius"],
            2: ["Capricorn", "Aquarius", "Pisces", "Scorpio", "Libra", "Virgo", "Cancer", "Leo", "Gemini"],
            3: ["Taurus", "Aries", "Pisces", "Aquarius", "Capricorn", "Sagittarius", "Aries", "Taurus", "Gemini"],
            4: ["Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"],
        }

        APASAVYA_SEQUENCES = {
            1: ["Pisces", "Aquarius", "Capricorn", "Sagittarius", "Scorpio", "Libra", "Virgo", "Leo", "Cancer"],
            2: ["Gemini", "Taurus", "Aries", "Sagittarius", "Capricorn", "Aquarius", "Pisces", "Aries", "Taurus"],
            3: ["Gemini", "Leo", "Cancer", "Virgo", "Libra", "Scorpio", "Pisces", "Aquarius", "Capricorn"],
            4: ["Sagittarius", "Scorpio", "Libra", "Virgo", "Leo", "Cancer", "Gemini", "Taurus", "Aries"],
        }

        KALACHAKRA_YEARS = {
            "Aries": 7.0,
            "Taurus": 16.0,
            "Gemini": 9.0,
            "Cancer": 21.0,
            "Leo": 5.0,
            "Virgo": 9.0,
            "Libra": 16.0,
            "Scorpio": 7.0,
            "Sagittarius": 10.0,
            "Capricorn": 4.0,
            "Aquarius": 4.0,
            "Pisces": 10.0,
        }

        sequence = SAVYA_SEQUENCES[pada_num] if is_savya else APASAVYA_SEQUENCES[pada_num]
        paramayush = sum(KALACHAKRA_YEARS[s] for s in sequence)

        timeline = []
        current_jd = chart.birth_event.julian_day

        for cycle_offset in range(18):
            idx = cycle_offset % 9
            lord = sequence[idx]
            total_years = KALACHAKRA_YEARS[lord]

            if cycle_offset == 0:
                years = total_years * (1.0 - fraction)
                is_balance = True
            else:
                years = float(total_years)
                is_balance = False

            days = years * self.DAYS_PER_YEAR
            end_jd = current_jd + days

            sub_periods = []
            if levels >= 2:
                sub_periods = self._compute_kalachakra_sub_periods(
                    sequence=sequence,
                    parent_idx=idx,
                    parent_years=years,
                    paramayush=paramayush,
                    start_jd=current_jd,
                    kalachakra_years=KALACHAKRA_YEARS
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

        starting_rashi = sequence[0]
        return DashaTimeline(
            system="Kalachakra",
            birth_nakshatra=NAKSHATRA_NAMES[nak_idx],
            birth_nakshatra_lord=starting_rashi,
            balance_at_birth={
                "lord": starting_rashi,
                "remaining_years": round(KALACHAKRA_YEARS[starting_rashi] * (1.0 - fraction), 4),
                "total_years": KALACHAKRA_YEARS[starting_rashi],
                "elapsed_fraction": round(fraction, 4),
            },
            timeline=timeline,
        )

    def _compute_kalachakra_sub_periods(
        self,
        sequence: list[str],
        parent_idx: int,
        parent_years: float,
        paramayush: float,
        start_jd: float,
        kalachakra_years: dict[str, float],
    ) -> list[DashaPeriod]:
        sub_periods = []
        current_jd = start_jd

        for i in range(9):
            sub_lord = sequence[(parent_idx + i) % 9]
            sub_lord_years = kalachakra_years[sub_lord]

            sub_years = (sub_lord_years * parent_years) / paramayush
            sub_days = sub_years * self.DAYS_PER_YEAR
            end_jd = current_jd + sub_days

            sub_periods.append(DashaPeriod(
                lord=sub_lord,
                start_date=self._jd_to_date(current_jd),
                end_date=self._jd_to_date(end_jd),
                start_jd=round(current_jd, 6),
                end_jd=round(end_jd, 6),
                years=round(sub_years, 4),
                sub_periods=[],
            ))
            current_jd = end_jd

        return sub_periods

    def compute_tara_dasha(self, chart: Chart, levels: int = 2) -> DashaTimeline:
        """
        Compute Tara Dasha (120 years).
        Calculated from Lagna's nakshatra (Ascendant's longitude)
        using the Vimshottari sequence.
        """
        if chart.birth_event is None:
            raise ValueError("Chart has no birth event data")

        timeline = self.compute_vimshottari(
            moon_longitude=chart.ascendant.longitude,
            birth_jd=chart.birth_event.julian_day,
            levels=levels,
        )
        timeline.system = "Tara"
        return timeline


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

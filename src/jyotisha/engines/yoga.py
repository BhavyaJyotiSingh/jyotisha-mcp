"""
Yoga Detection Engine — Layer H

Parses YAML-based yoga definitions and evaluates them against a Chart object.
Implements a custom domain-specific language (DSL) for astrological conditions.
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from jyotisha.models.schemas import Chart, YogaResult
from jyotisha.constants import NATURAL_BENEFICS


class YogaEngine:
    """
    Evaluates astrological rules (Yogas) against a birth chart.
    """

    def __init__(self, rules_path: Optional[str] = None):
        if not HAS_YAML:
            raise ImportError("PyYAML is required to parse yoga rules. Install with: pip install pyyaml")

        if rules_path is None:
            # Default to bundled rules
            base_dir = Path(__file__).parent.parent
            rules_path = str(base_dir / "rules" / "yogas.yaml")

        self.rules = self._load_rules(rules_path)

    def _load_rules(self, path: str) -> list[dict]:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("yogas", [])

    def detect_yogas(
        self,
        chart: Chart,
        categories: Optional[list[str]] = None,
        include_cancelled: bool = False,
    ) -> list[YogaResult]:
        """
        Scan the chart for all known yogas.
        """
        results = []

        for rule in self.rules:
            # Filter by category if requested
            if categories and rule.get("category") not in categories:
                continue

            # Evaluate main conditions
            is_active, involved_planets = self._evaluate_conditions(rule["conditions"], chart)

            if is_active:
                # Check cancellation conditions
                is_cancelled = False
                cancellation_reason = None
                cancel_conds = rule.get("cancellation_conditions", [])
                
                if cancel_conds:
                    is_cancelled, _ = self._evaluate_conditions(cancel_conds, chart, match_all=False)
                    if is_cancelled:
                        cancellation_reason = "Cancellation condition met."

                if is_active and (not is_cancelled or include_cancelled):
                    result = YogaResult(
                        name=rule["name"],
                        category=rule.get("category", "general"),
                        is_active=True,
                        is_cancelled=is_cancelled,
                        cancellation_reason=cancellation_reason,
                        conclusion=rule.get("conclusion", ""),
                        effects=rule.get("effects", []),
                        intensity=rule.get("intensity", "medium"),
                        sources=rule.get("sources", []),
                        involved_planets=list(involved_planets)
                    )
                    results.append(result)

        return results

    # ─────────────────────────────────────────────────────────
    # DSL Evaluator
    # ─────────────────────────────────────────────────────────

    def _evaluate_conditions(
        self,
        conditions: list[Any],
        chart: Chart,
        match_all: bool = True
    ) -> tuple[bool, set[str]]:
        """
        Evaluate a list of conditions (strings or composite dicts).
        Returns (is_met, involved_planets).
        """
        involved = set()
        
        for cond in conditions:
            if isinstance(cond, str):
                met, inv = self._eval_expression(cond, chart)
                involved.update(inv)
                if match_all and not met:
                    return False, set()
                if not match_all and met:
                    return True, involved
            elif isinstance(cond, dict) and cond.get("type") == "composite":
                met, inv = self._eval_composite(cond, chart)
                involved.update(inv)
                if match_all and not met:
                    return False, set()
                if not match_all and met:
                    return True, involved
        
        # If match_all is True and we made it here, all matched
        # If match_all is False and we made it here, none matched
        return match_all, involved

    def _eval_composite(self, cond: dict, chart: Chart) -> tuple[bool, set[str]]:
        """Handle AND/OR composite logic blocks."""
        involved = set()
        
        if "any_of" in cond:
            # OR logic
            for sub_cond in cond["any_of"]:
                met, inv = self._eval_expression(sub_cond, chart)
                if met:
                    involved.update(inv)
                    return True, involved
            return False, set()
            
        elif "all_of" in cond:
            # AND logic
            for sub_cond in cond["all_of"]:
                met, inv = self._eval_expression(sub_cond, chart)
                if not met:
                    return False, set()
                involved.update(inv)
            return True, involved
            
        return False, set()

    def _eval_expression(self, expr: str, chart: Chart) -> tuple[bool, set[str]]:
        """
        Evaluate a single string expression.
        Examples:
        - "Mars.inOwnSign() OR Mars.inExaltation()"
        - "Jupiter.inKendraFrom(Moon)"
        - "Moon.house(2).emptyExcluding(Sun, Rahu, Ketu)"
        """
        involved = set()
        
        # Handle simple logical OR at the top level string
        if " OR " in expr:
            parts = expr.split(" OR ")
            for part in parts:
                met, inv = self._eval_single_statement(part.strip(), chart)
                if met:
                    involved.update(inv)
                    return True, involved
            return False, set()
            
        # Handle simple AND
        if " AND " in expr:
            parts = expr.split(" AND ")
            for part in parts:
                met, inv = self._eval_single_statement(part.strip(), chart)
                if not met:
                    return False, set()
                involved.update(inv)
            return True, involved

        return self._eval_single_statement(expr, chart)

    def _eval_single_statement(self, stmt: str, chart: Chart) -> tuple[bool, set[str]]:
        """Evaluate a single atomic statement without AND/OR."""
        
        # Planet.inOwnSign()
        match = re.match(r"^([a-zA-Z]+)\.inOwnSign\(\)$", stmt)
        if match:
            planet = match.group(1)
            p_data = chart.get_planet(planet)
            if p_data and p_data.dignity.is_own_sign:
                return True, {planet}
            return False, set()

        # Planet.inExaltation()
        match = re.match(r"^([a-zA-Z]+)\.inExaltation\(\)$", stmt)
        if match:
            planet = match.group(1)
            p_data = chart.get_planet(planet)
            if p_data and p_data.dignity.is_exalted:
                return True, {planet}
            return False, set()

        # Planet.inDebilitation()
        match = re.match(r"^([a-zA-Z]+)\.inDebilitation\(\)$", stmt)
        if match:
            planet = match.group(1)
            p_data = chart.get_planet(planet)
            if p_data and p_data.dignity.is_debilitated:
                return True, {planet}
            return False, set()

        # Planet.combust
        match = re.match(r"^([a-zA-Z]+)\.combust$", stmt)
        if match:
            planet = match.group(1)
            p_data = chart.get_planet(planet)
            if p_data and p_data.combust:
                return True, {planet}
            return False, set()

        # Planet.inKendra()  (houses 1, 4, 7, 10 from Lagna)
        match = re.match(r"^([a-zA-Z]+)\.inKendra\(\)$", stmt)
        if match:
            planet = match.group(1)
            p_data = chart.get_planet(planet)
            if p_data and p_data.house in [1, 4, 7, 10]:
                return True, {planet}
            return False, set()

        # Planet.inKendraFrom(OtherPlanet)
        match = re.match(r"^([a-zA-Z]+)\.inKendraFrom\(([a-zA-Z]+)\)$", stmt)
        if match:
            planet1 = match.group(1)
            planet2 = match.group(2)
            p1_data = chart.get_planet(planet1)
            p2_data = chart.get_planet(planet2)
            if p1_data and p2_data:
                # Relative house position
                relative_house = ((p1_data.house - p2_data.house) % 12) + 1
                if relative_house in [1, 4, 7, 10]:
                    return True, {planet1, planet2}
            return False, set()

        # Planet.conjunct(OtherPlanet, orb=X) or Planet.conjunct(OtherPlanet)
        match = re.match(r"^([a-zA-Z]+)\.conjunct\(([a-zA-Z]+)(?:,\s*orb=([0-9.]+))?\)$", stmt)
        if match:
            planet1 = match.group(1)
            target = match.group(2)
            orb_str = match.group(3)
            p1_data = chart.get_planet(planet1)
            if not p1_data:
                return False, set()

            if target == "Benefic":
                # Check if conjunct any natural benefic
                for b_name in NATURAL_BENEFICS:
                    b_data = chart.get_planet(b_name.value)
                    if b_data and b_data.house == p1_data.house and b_data.name != planet1:
                        if orb_str:
                            orb_limit = float(orb_str)
                            actual_orb = abs(p1_data.degree_in_sign - b_data.degree_in_sign)
                            if actual_orb <= orb_limit:
                                return True, {planet1, b_data.name}
                        else:
                            return True, {planet1, b_data.name}
            else:
                p2_data = chart.get_planet(target)
                if p2_data and p1_data.house == p2_data.house:
                    if orb_str:
                        orb_limit = float(orb_str)
                        actual_orb = abs(p1_data.degree_in_sign - p2_data.degree_in_sign)
                        if actual_orb <= orb_limit:
                            return True, {planet1, target}
                    else:
                        return True, {planet1, target}
            return False, set()
            
        # Planet.aspects(OtherPlanet)
        match = re.match(r"^([a-zA-Z]+)\.aspects\(([a-zA-Z]+)\)$", stmt)
        if match:
            planet1 = match.group(1)
            planet2 = match.group(2)
            p2_data = chart.get_planet(planet2)
            if p2_data:
                target_house = chart.get_house(p2_data.house)
                if target_house and planet1 in target_house.aspects_received:
                    return True, {planet1, planet2}
            return False, set()

        # Planet.house(N).hasPlanetExcluding(A, B, C)
        match = re.match(r"^([a-zA-Z]+)\.house\(([0-9]+)\)\.hasPlanetExcluding\(([^)]+)\)$", stmt)
        if match:
            ref_planet = match.group(1)
            relative_house_offset = int(match.group(2))
            excluded = [p.strip() for p in match.group(3).split(",")]
            
            p_data = chart.get_planet(ref_planet)
            if not p_data:
                return False, set()
                
            target_house_num = ((p_data.house + relative_house_offset - 2) % 12) + 1
            target_house = chart.get_house(target_house_num)
            
            if target_house:
                occupants = set(target_house.planets_in_house)
                # Remove excluded planets
                for ex in excluded:
                    occupants.discard(ex)
                if occupants:
                    # Condition met: there is at least one planet here not in excluded list
                    return True, {ref_planet}.union(occupants)
            return False, set()

        # Planet.house(N).emptyExcluding(A, B, C)
        match = re.match(r"^([a-zA-Z]+)\.house\(([0-9]+)\)\.emptyExcluding\(([^)]+)\)$", stmt)
        if match:
            ref_planet = match.group(1)
            relative_house_offset = int(match.group(2))
            excluded = [p.strip() for p in match.group(3).split(",")]
            
            p_data = chart.get_planet(ref_planet)
            if not p_data:
                return False, set()
                
            target_house_num = ((p_data.house + relative_house_offset - 2) % 12) + 1
            target_house = chart.get_house(target_house_num)
            
            if target_house:
                occupants = set(target_house.planets_in_house)
                for ex in excluded:
                    occupants.discard(ex)
                if not occupants:
                    # Condition met: house is empty (ignoring excluded planets)
                    return True, {ref_planet}
            return False, set()

        # House(N).lord.inHouse(M)
        match = re.match(r"^House\(([0-9]+)\)\.lord\.inHouse\(([0-9]+)\)$", stmt)
        if match:
            source_house_num = int(match.group(1))
            target_house_num = int(match.group(2))
            
            source_house = chart.get_house(source_house_num)
            if source_house:
                lord = source_house.lord
                lord_data = chart.get_planet(lord)
                if lord_data and lord_data.house == target_house_num:
                    return True, {lord}
            return False, set()

        # Complex cases (Neechabhanga)
        
        # DebilitatedPlanet.dispositor.inKendra()
        if stmt == "DebilitatedPlanet.dispositor.inKendra()":
            # Find any debilitated planet
            for p in chart.planets:
                if p.dignity.is_debilitated:
                    # Find its dispositor (lord of its current sign)
                    house = chart.get_house(p.house)
                    if house:
                        dispositor_name = house.lord
                        dispositor = chart.get_planet(dispositor_name)
                        if dispositor and dispositor.house in [1, 4, 7, 10]:
                            return True, {p.name, dispositor_name}
            return False, set()

        # DebilitatedPlanet.dispositor.exalted()
        if stmt == "DebilitatedPlanet.dispositor.exalted()":
            for p in chart.planets:
                if p.dignity.is_debilitated:
                    house = chart.get_house(p.house)
                    if house:
                        dispositor_name = house.lord
                        dispositor = chart.get_planet(dispositor_name)
                        if dispositor and dispositor.dignity.is_exalted:
                            return True, {p.name, dispositor_name}
            return False, set()

        # Fallback for unrecognized syntax
        raise ValueError(f"Unrecognized Yoga DSL statement: '{stmt}'")

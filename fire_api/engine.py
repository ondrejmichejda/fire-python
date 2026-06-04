from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any


CRITICAL_HEAT_FLUX_KW_M2 = 18.5
STEFAN_BOLTZMANN_KW_M2_K4 = 5.67e-11

STRUCTURAL_SYSTEM_ADJUSTMENTS = {
    "noncombustible": 0.0,
    "nehorlavy": 0.0,
    "nehořlavý": 0.0,
    "mixed": 5.0,
    "smiseny": 5.0,
    "smíšený": 5.0,
    "combustible_d2": 10.0,
    "horlavy_d2": 10.0,
    "hořlavý_d2": 10.0,
    "c1": 10.0,
    "combustible_d3": 15.0,
    "horlavy_d3": 15.0,
    "hořlavý_d3": 15.0,
    "c2": 15.0,
}

ROOF_DISTANCE_TABLE_15 = {
    2.0: {3.0: 2.65, 6.0: 3.45, 9.0: 3.90, 12.0: 4.15, 15.0: 4.30, 25.0: 4.50, 35.0: 4.60},
    3.0: {3.0: 3.25, 6.0: 4.45, 9.0: 5.30, 12.0: 5.70, 15.0: 6.10, 25.0: 6.50, 35.0: 6.75},
    4.0: {3.0: 3.75, 6.0: 5.25, 9.0: 6.25, 12.0: 6.95, 15.0: 7.45, 25.0: 8.45, 35.0: 8.85},
    5.0: {3.0: 4.15, 6.0: 5.95, 9.0: 7.15, 12.0: 8.00, 15.0: 8.70, 25.0: 10.10, 35.0: 10.75},
}


class CalculationError(ValueError):
    """Raised for invalid payloads or impossible calculations."""


@dataclass(frozen=True)
class OpeningInput:
    width_m: float
    height_m: float
    pv_kg_m2: float
    structural_system: str = "noncombustible"
    radiation_percentage: float = 100.0
    emissivity: float = 1.0
    falling_parts_risk: bool = False
    fall_height_m: float | None = None
    opening_id: str | None = None


@dataclass(frozen=True)
class GroupGeometryInput:
    openings: list[dict[str, Any]]
    layout: str
    gaps_m: list[float]


def _require_number(name: str, value: Any, *, min_value: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalculationError(f"'{name}' must be a number.")
    result = float(value)
    if min_value is not None and result < min_value:
        raise CalculationError(f"'{name}' must be >= {min_value}.")
    return result


def _normalize_structural_system(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CalculationError("'structural_system' must be a non-empty string.")
    key = value.strip().lower()
    if key not in STRUCTURAL_SYSTEM_ADJUSTMENTS:
        allowed = ", ".join(sorted(set(STRUCTURAL_SYSTEM_ADJUSTMENTS)))
        raise CalculationError(f"Unknown structural_system '{value}'. Allowed values: {allowed}.")
    return key


def _normalize_layout(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CalculationError("'layout' must be a non-empty string.")
    key = value.strip().lower()
    if key not in {"horizontal", "vertical"}:
        raise CalculationError("'layout' must be either 'horizontal' or 'vertical'.")
    return key


def _normalize_opening_id(opening: dict[str, Any], index: int) -> str:
    opening_id = opening.get("opening_id", opening.get("id"))
    if opening_id is None:
        return f"opening_{index}"
    if not isinstance(opening_id, str) or not opening_id.strip():
        raise CalculationError(f"'openings[{index}].opening_id' must be a non-empty string when provided.")
    return opening_id.strip()


def _normalize_openings(openings: Any) -> tuple[list[dict[str, Any]], float]:
    if not isinstance(openings, list) or not openings:
        raise CalculationError("'openings' must contain at least one opening.")

    normalized: list[dict[str, Any]] = []
    opening_area_total = 0.0
    for index, opening in enumerate(openings, start=1):
        if not isinstance(opening, dict):
            raise CalculationError(f"'openings[{index}]' must be an object.")
        width = _require_number(f"openings[{index}].width_m", opening.get("width_m"), min_value=0.000001)
        height = _require_number(f"openings[{index}].height_m", opening.get("height_m"), min_value=0.000001)
        area = width * height
        opening_area_total += area
        normalized.append(
            {
                "opening_id": _normalize_opening_id(opening, index),
                "width_m": width,
                "height_m": height,
                "area_m2": round(area, 4),
            }
        )
    return normalized, opening_area_total


def _normalize_gaps(gaps_m: Any, *, expected_count: int) -> list[float]:
    if expected_count == 0:
        if gaps_m in (None, []):
            return []
        raise CalculationError("'gaps_m' must be empty when only one opening is provided.")
    if not isinstance(gaps_m, list):
        raise CalculationError("'gaps_m' must be a list.")
    if len(gaps_m) != expected_count:
        raise CalculationError(f"'gaps_m' must contain exactly {expected_count} values.")
    return [
        _require_number(f"gaps_m[{index}]", gap, min_value=0.0)
        for index, gap in enumerate(gaps_m, start=1)
    ]


def adjusted_fire_load(pv_kg_m2: float, structural_system: str) -> dict[str, float | str]:
    pv = _require_number("pv_kg_m2", pv_kg_m2, min_value=0.0)
    system_key = _normalize_structural_system(structural_system)
    adjustment = STRUCTURAL_SYSTEM_ADJUSTMENTS[system_key]
    return {
        "structural_system": system_key,
        "adjustment_kg_m2": adjustment,
        "pv_original_kg_m2": pv,
        "pv_adjusted_kg_m2": pv + adjustment,
    }


def gas_temperature_celsius(pv_adjusted_kg_m2: float) -> float:
    pv = _require_number("pv_adjusted_kg_m2", pv_adjusted_kg_m2, min_value=0.0)
    return 20.0 + 345.0 * math.log10(8.0 * pv + 1.0)


def source_heat_flux_kw_m2(temperature_celsius: float, emissivity: float = 1.0) -> float:
    tn = _require_number("temperature_celsius", temperature_celsius)
    epsilon = _require_number("emissivity", emissivity, min_value=0.0)
    return epsilon * ((tn + 273.0) ** 4) * STEFAN_BOLTZMANN_KW_M2_K4


def effective_heat_flux_kw_m2(source_flux_kw_m2: float, radiation_percentage: float = 100.0) -> float:
    source_flux = _require_number("source_flux_kw_m2", source_flux_kw_m2, min_value=0.0)
    p0 = _require_number("radiation_percentage", radiation_percentage, min_value=0.0)
    return source_flux * (p0 / 100.0)


def required_position_factor(effective_flux_kw_m2: float) -> float:
    flux = _require_number("effective_flux_kw_m2", effective_flux_kw_m2, min_value=0.000001)
    return CRITICAL_HEAT_FLUX_KW_M2 / flux


def rectangle_position_factor(width_m: float, height_m: float, distance_m: float) -> float:
    width = _require_number("width_m", width_m, min_value=0.000001)
    height = _require_number("height_m", height_m, min_value=0.000001)
    distance = _require_number("distance_m", distance_m, min_value=0.000001)
    b = width / (2.0 * distance)
    h = height / (2.0 * distance)
    first = b / math.sqrt(1.0 + b**2) * math.atan(h / math.sqrt(1.0 + b**2))
    second = h / math.sqrt(1.0 + h**2) * math.atan(b / math.sqrt(1.0 + h**2))
    return (2.0 / math.pi) * (first + second)


def solve_separation_distance(width_m: float, height_m: float, required_phi: float) -> float:
    width = _require_number("width_m", width_m, min_value=0.000001)
    height = _require_number("height_m", height_m, min_value=0.000001)
    phi_target = _require_number("required_phi", required_phi, min_value=0.000001)
    low = 0.001
    high = max(width, height, 1.0)
    while rectangle_position_factor(width, height, high) > phi_target:
        high *= 2.0
        if high > 1_000.0:
            raise CalculationError("Could not bracket the separation distance.")
    for _ in range(80):
        mid = (low + high) / 2.0
        phi_mid = rectangle_position_factor(width, height, mid)
        if phi_mid > phi_target:
            low = mid
        else:
            high = mid
    return high


def falling_parts_distance(fall_height_m: float) -> float:
    height = _require_number("fall_height_m", fall_height_m, min_value=0.0)
    return 0.36 * height


def calculate_opening_distance(payload: dict[str, Any]) -> dict[str, Any]:
    opening = OpeningInput(
        width_m=_require_number("width_m", payload.get("width_m"), min_value=0.000001),
        height_m=_require_number("height_m", payload.get("height_m"), min_value=0.000001),
        pv_kg_m2=_require_number("pv_kg_m2", payload.get("pv_kg_m2"), min_value=0.0),
        structural_system=str(payload.get("structural_system", "noncombustible")),
        radiation_percentage=_require_number(
            "radiation_percentage",
            payload.get("radiation_percentage", 100.0),
            min_value=0.0,
        ),
        emissivity=_require_number("emissivity", payload.get("emissivity", 1.0), min_value=0.0),
        falling_parts_risk=bool(payload.get("falling_parts_risk", False)),
        fall_height_m=payload.get("fall_height_m"),
        opening_id=payload.get("opening_id", payload.get("id")),
    )
    pv_data = adjusted_fire_load(opening.pv_kg_m2, opening.structural_system)
    temperature = gas_temperature_celsius(float(pv_data["pv_adjusted_kg_m2"]))
    source_flux = source_heat_flux_kw_m2(temperature, opening.emissivity)
    effective_flux = effective_heat_flux_kw_m2(source_flux, opening.radiation_percentage)
    phi = required_position_factor(effective_flux)
    base_distance = solve_separation_distance(opening.width_m, opening.height_m, phi)

    fall_distance = None
    final_distance = base_distance
    if opening.falling_parts_risk:
        if opening.fall_height_m is None:
            raise CalculationError("'fall_height_m' is required when 'falling_parts_risk' is true.")
        fall_distance = falling_parts_distance(opening.fall_height_m)
        final_distance = max(base_distance, fall_distance)

    return {
        "opening_id": opening.opening_id,
        "inputs": {
            "width_m": opening.width_m,
            "height_m": opening.height_m,
            "pv_kg_m2": opening.pv_kg_m2,
            "structural_system": pv_data["structural_system"],
            "radiation_percentage": opening.radiation_percentage,
            "emissivity": opening.emissivity,
            "falling_parts_risk": opening.falling_parts_risk,
            "fall_height_m": opening.fall_height_m,
        },
        "intermediate": {
            "pv_adjustment_kg_m2": pv_data["adjustment_kg_m2"],
            "pv_adjusted_kg_m2": pv_data["pv_adjusted_kg_m2"],
            "temperature_celsius": round(temperature, 3),
            "source_heat_flux_kw_m2": round(source_flux, 6),
            "effective_heat_flux_kw_m2": round(effective_flux, 6),
            "required_position_factor": round(phi, 8),
        },
        "result": {
            "base_distance_m": round(base_distance, 3),
            "falling_parts_distance_m": None if fall_distance is None else round(fall_distance, 3),
            "final_distance_m": round(final_distance, 3),
            "critical_heat_flux_kw_m2": CRITICAL_HEAT_FLUX_KW_M2,
        },
        "source_reference": {
            "workflow": "rules/05_workflow.md",
            "formulas": "rules/03_vzorce.yaml",
        },
    }


def calculate_opening_group(payload: dict[str, Any]) -> dict[str, Any]:
    normalized_openings, opening_area_total = _normalize_openings(payload.get("openings"))
    geometry = GroupGeometryInput(
        openings=normalized_openings,
        layout=_normalize_layout(payload.get("layout")),
        gaps_m=_normalize_gaps(payload.get("gaps_m"), expected_count=len(normalized_openings) - 1),
    )

    widths = [opening["width_m"] for opening in geometry.openings]
    heights = [opening["height_m"] for opening in geometry.openings]
    if geometry.layout == "horizontal":
        bounding_width = sum(widths) + sum(geometry.gaps_m)
        bounding_height = max(heights)
    else:
        bounding_width = max(widths)
        bounding_height = sum(heights) + sum(geometry.gaps_m)

    bounding_area = bounding_width * bounding_height
    p0 = (opening_area_total / bounding_area) * 100.0
    return {
        "openings": geometry.openings,
        "layout": geometry.layout,
        "gaps_m": geometry.gaps_m,
        "opening_area_m2": round(opening_area_total, 4),
        "opening_area_total_m2": round(opening_area_total, 4),
        "bounding_width_m": round(bounding_width, 4),
        "bounding_height_m": round(bounding_height, 4),
        "bounding_area_m2": round(bounding_area, 4),
        "p0_percent": round(p0, 4),
        "radiation_percentage": round(p0, 4),
        "can_be_assessed_as_group": p0 >= 40.0,
        "requires_10481_confirmation": p0 < 40.0,
        "individual_assessment_prompt_required": p0 < 40.0,
        "source_reference": {
            "formula": "FORMULA_OPENING_GROUP_PERCENTAGE",
            "file": "rules/03_vzorce.yaml",
        },
    }


def calculate_opening_percentage(
    openings_or_payload: list[dict[str, Any]] | dict[str, Any],
    bounding_width_m: float | None = None,
    bounding_height_m: float | None = None,
) -> dict[str, Any]:
    if isinstance(openings_or_payload, dict):
        payload = openings_or_payload
        openings = payload.get("openings")
        if payload.get("layout") is not None or payload.get("gaps_m") is not None:
            return calculate_opening_group(payload)
        bounding_width = _require_number("bounding_width_m", payload.get("bounding_width_m"), min_value=0.000001)
        bounding_height = _require_number("bounding_height_m", payload.get("bounding_height_m"), min_value=0.000001)
    else:
        openings = openings_or_payload
        bounding_width = _require_number("bounding_width_m", bounding_width_m, min_value=0.000001)
        bounding_height = _require_number("bounding_height_m", bounding_height_m, min_value=0.000001)

    normalized_openings, opening_area_total = _normalize_openings(openings)
    bounding_area = bounding_width * bounding_height
    p0 = (opening_area_total / bounding_area) * 100.0
    return {
        "openings": normalized_openings,
        "opening_area_m2": round(opening_area_total, 4),
        "opening_area_total_m2": round(opening_area_total, 4),
        "bounding_area_m2": round(bounding_area, 4),
        "bounding_width_m": round(bounding_width, 4),
        "bounding_height_m": round(bounding_height, 4),
        "p0_percent": round(p0, 4),
        "radiation_percentage": round(p0, 4),
        "can_be_assessed_as_group": p0 >= 40.0,
        "requires_10481_confirmation": p0 < 40.0,
        "individual_assessment_prompt_required": p0 < 40.0,
        "source_reference": {
            "formula": "FORMULA_OPENING_PERCENTAGE",
            "file": "rules/03_vzorce.yaml",
        },
    }


def check_individual_opening_spacing(
    gap_or_payload: float | dict[str, Any],
    distance_1_m: float | None = None,
    distance_2_m: float | None = None,
) -> dict[str, Any]:
    p0_percent = None
    if isinstance(gap_or_payload, dict):
        payload = gap_or_payload
        if payload.get("p0_percent") is not None:
            p0_percent = _require_number("p0_percent", payload.get("p0_percent"), min_value=0.0)
        gap = _require_number(
            "openings_edge_distance_m",
            payload.get("openings_edge_distance_m", payload.get("gap_m")),
            min_value=0.0,
        )
        d1 = _require_number(
            "distance_opening_1_m",
            payload.get("distance_opening_1_m", payload.get("distance_1_m")),
            min_value=0.0,
        )
        d2 = _require_number(
            "distance_opening_2_m",
            payload.get("distance_opening_2_m", payload.get("distance_2_m")),
            min_value=0.0,
        )
    else:
        gap = _require_number("gap_m", gap_or_payload, min_value=0.0)
        d1 = _require_number("distance_1_m", distance_1_m, min_value=0.0)
        d2 = _require_number("distance_2_m", distance_2_m, min_value=0.0)
    threshold = 0.6 * (d1 + d2)
    return {
        "openings_edge_distance_m": gap,
        "gap_m": gap,
        "distance_opening_1_m": d1,
        "distance_opening_2_m": d2,
        "required_minimum_gap_m": round(threshold, 3),
        "assessment_10481_possible": gap > threshold,
        "passes": gap > threshold,
        "p0_percent": None if p0_percent is None else round(p0_percent, 4),
        "source_reference": {
            "formula": "FORMULA_CSN730802_10_4_8_1_SPACING",
            "file": "rules/03_vzorce.yaml",
        },
    }


def assess_roof(payload: dict[str, Any]) -> dict[str, Any]:
    pv_kg_m2 = float(payload.get("pv_kg_m2", 30.0))
    fire_safety_level = payload.get("fire_safety_level")
    roof_requirement_status = payload.get("roof_requirement_status")
    roof_classification = payload.get("roof_classification")
    roof_structure_above_fire_ceiling = payload.get("roof_structure_above_fire_ceiling")
    fire_resistance_required = payload.get("fire_resistance_required")
    fire_resistance_met = payload.get("fire_resistance_met")
    coefficient_c = payload.get("coefficient_c")
    supporting_construction_type = payload.get("supporting_construction_type")
    required_fire_resistance_met = payload.get("required_fire_resistance_met")
    released_heat_mj_m2 = payload.get("released_heat_mj_m2")
    heat_release_rate_mw_m2 = payload.get("heat_release_rate_mw_m2")
    average_distance_to_dp1_m = payload.get("average_distance_to_dp1_m")
    roof_edge_heat_flux_kw_m2 = payload.get("roof_edge_heat_flux_kw_m2")

    matched_rule = {
        "id": "CSN730802_8_15_4_A",
        "article": "8.15.4 a)",
        "title": "Střešní plášť jako požárně otevřená plocha",
        "roof_is_fire_open": True,
        "distance_required": True,
        "reason": "Nebyla splněna žádná známá výjimka z čl. 8.15.4 b).",
    }

    if (
        pv_kg_m2 <= 50
        and fire_safety_level in {"I", "II"}
        and roof_requirement_status in {"splňuje 8.15.1 a)", "požadavky 8.15.1 c) jsou nulové"}
    ):
        matched_rule = {
            "id": "CSN730802_8_15_4_B1",
            "article": "8.15.4 b) 1)",
            "title": "Střešní plášť není požárně otevřenou plochou – I. a II. SPB",
            "roof_is_fire_open": False,
            "distance_required": False,
            "reason": "pv <= 50 kg/m2, objekt je v I. nebo II. SPB a je splněn stav střechy dle 8.15.1.",
        }
    elif (
        roof_classification == "Broof(t3)"
        and roof_structure_above_fire_ceiling is True
        and fire_resistance_required is False
    ):
        matched_rule = {
            "id": "CSN730802_8_15_4_B2",
            "article": "8.15.4 b) 2)",
            "title": "Střešní plášť Broof(t3) nad požárním stropem",
            "roof_is_fire_open": False,
            "distance_required": False,
            "reason": "Klasifikace Broof(t3), krov nad požárním stropem a bez požadované požární odolnosti.",
        }
    elif (
        fire_resistance_required is True
        and fire_resistance_met is True
        and fire_safety_level in {"III", "IV", "V", "VI", "VII"}
    ):
        matched_rule = {
            "id": "CSN730802_8_15_4_B3",
            "article": "8.15.4 b) 3)",
            "title": "Střešní plášť s požadovanou požární odolností",
            "roof_is_fire_open": False,
            "distance_required": False,
            "reason": "Požární odolnost střechy je požadována a splněna.",
        }
    elif fire_resistance_required is True and fire_resistance_met is False and coefficient_c is not None and float(coefficient_c) <= 0.4:
        matched_rule = {
            "id": "CSN730802_8_15_4_B4",
            "article": "8.15.4 b) 4)",
            "title": "Střešní plášť bez požadované požární odolnosti při c <= 0,4",
            "roof_is_fire_open": False,
            "distance_required": False,
            "reason": "Požadovaná požární odolnost není splněna, ale součinitel c <= 0,4.",
        }
    elif (
        supporting_construction_type == "DP1"
        and required_fire_resistance_met is True
        and average_distance_to_dp1_m is not None
        and float(average_distance_to_dp1_m) <= 0.5
        and (
            (released_heat_mj_m2 is not None and float(released_heat_mj_m2) <= 150.0)
            or (heat_release_rate_mw_m2 is not None and float(heat_release_rate_mw_m2) < 0.4)
        )
    ):
        matched_rule = {
            "id": "CSN730802_8_15_4_B5",
            "article": "8.15.4 b) 5)",
            "title": "Střešní plášť na konstrukci DP1 s omezeným uvolněným teplem",
            "roof_is_fire_open": False,
            "distance_required": False,
            "reason": "Střecha leží na DP1 s vyhovující odolností a omezeným uvolněným teplem nebo výkonem.",
        }
    elif roof_edge_heat_flux_kw_m2 is not None and float(roof_edge_heat_flux_kw_m2) < 18.5:
        matched_rule = {
            "id": "CSN730802_8_15_4_B6",
            "article": "8.15.4 b) 6)",
            "title": "Hustota tepelného toku z hořící střechy je nižší než 18,5 kW/m2",
            "roof_is_fire_open": False,
            "distance_required": False,
            "reason": "Tepelný tok v okraji římsy je menší než 18,5 kW/m2.",
        }

    result = {
        "matched_rule": matched_rule,
        "source_reference": {
            "rules": "rules/02_rules.yaml",
            "system_rules": "rules/01_system_rules.md",
        },
    }

    if matched_rule["roof_is_fire_open"] and payload.get("hu_m") is not None and payload.get("width_m") is not None:
        result["distance_table_15"] = roof_distance_table_15(float(payload["hu_m"]), float(payload["width_m"]))
    return result


def assess_etics(payload: dict[str, Any]) -> dict[str, Any]:
    thickness = _require_number("insulation_thickness_mm", payload.get("insulation_thickness_mm"), min_value=0.0)
    reaction_class = payload.get("insulation_reaction_class")
    if not isinstance(reaction_class, str) or not reaction_class.strip():
        raise CalculationError("'insulation_reaction_class' must be a non-empty string.")
    normalized_class = reaction_class.strip().upper()

    if normalized_class in {"A1", "A2"}:
        return {
            "matched_rule": {
                "id": "CSN730810_3_1_3_ETICS_A1_A2",
                "released_heat_assessment_required": False,
                "affects_fire_open_area": False,
                "reason": "ETICS je z materiálů třídy reakce na oheň A1 nebo A2.",
            },
            "source_reference": {"rules": "rules/02_rules.yaml"},
        }
    if thickness <= 200.0:
        return {
            "matched_rule": {
                "id": "CSN730810_3_1_3_ETICS_THICKNESS",
                "released_heat_assessment_required": False,
                "affects_fire_open_area": False,
                "reason": "Tloušťka tepelné izolace nepřesahuje 200 mm.",
            },
            "source_reference": {"rules": "rules/02_rules.yaml"},
        }
    return {
        "matched_rule": {
            "id": "CSN730810_3_1_3_ETICS_OVER_200",
            "released_heat_assessment_required": True,
            "affects_fire_open_area": True,
            "reason": "Tloušťka ETICS je > 200 mm a nejde o A1/A2.",
        },
        "source_reference": {"rules": "rules/02_rules.yaml"},
    }


def roof_distance_table_15(hu_m: float, width_m: float) -> dict[str, Any]:
    hu = _require_number("hu_m", hu_m, min_value=0.000001)
    width = _require_number("width_m", width_m, min_value=0.000001)
    hu_values = sorted(ROOF_DISTANCE_TABLE_15)
    width_values = sorted(next(iter(ROOF_DISTANCE_TABLE_15.values())))

    if hu < hu_values[0] or hu > hu_values[-1] or width < width_values[0] or width > width_values[-1]:
        raise CalculationError(
            "Values are outside Table 15 range. Known range: hu 2-5 m, width 3-35 m."
        )

    hu_low, hu_high = _bracket(hu_values, hu)
    width_low, width_high = _bracket(width_values, width)

    q11 = ROOF_DISTANCE_TABLE_15[hu_low][width_low]
    q12 = ROOF_DISTANCE_TABLE_15[hu_low][width_high]
    q21 = ROOF_DISTANCE_TABLE_15[hu_high][width_low]
    q22 = ROOF_DISTANCE_TABLE_15[hu_high][width_high]

    if hu_low == hu_high and width_low == width_high:
        distance = q11
    elif hu_low == hu_high:
        distance = _linear_interpolate(width_low, width_high, q11, q12, width)
    elif width_low == width_high:
        distance = _linear_interpolate(hu_low, hu_high, q11, q21, hu)
    else:
        r1 = _linear_interpolate(width_low, width_high, q11, q12, width)
        r2 = _linear_interpolate(width_low, width_high, q21, q22, width)
        distance = _linear_interpolate(hu_low, hu_high, r1, r2, hu)

    return {
        "hu_m": hu,
        "width_m": width,
        "distance_m": round(distance, 3),
        "interpolation": {
            "hu_low": hu_low,
            "hu_high": hu_high,
            "width_low": width_low,
            "width_high": width_high,
        },
        "source_reference": {
            "table": "TABLE_CSN730802_15",
            "file": "rules/04_tabulky.yaml",
        },
    }


def _linear_interpolate(x1: float, x2: float, y1: float, y2: float, x: float) -> float:
    if x1 == x2:
        return y1
    return y1 + (x - x1) * (y2 - y1) / (x2 - x1)


def _bracket(values: list[float], target: float) -> tuple[float, float]:
    if target in values:
        return target, target
    for low, high in zip(values, values[1:]):
        if low <= target <= high:
            return low, high
    raise CalculationError(f"Target value {target} is outside known range.")


def calculate_full_assessment(payload: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "openings": [],
        "roof": None,
        "etics": None,
        "group": None,
        "individual_spacing_checks": [],
    }

    roof_payload = payload.get("roof")
    if isinstance(roof_payload, dict):
        result["roof"] = assess_roof(roof_payload)

    etics_payload = payload.get("etics")
    if isinstance(etics_payload, dict):
        result["etics"] = assess_etics(etics_payload)

    openings = payload.get("openings", [])
    if openings:
        if not isinstance(openings, list):
            raise CalculationError("'openings' must be a list.")
        pv_kg_m2 = payload.get("pv_kg_m2")
        structural_system = payload.get("structural_system", "noncombustible")
        if pv_kg_m2 is None:
            raise CalculationError("'pv_kg_m2' is required when 'openings' are provided.")

        for index, opening in enumerate(openings, start=1):
            opening_payload = {
                "opening_id": _normalize_opening_id(opening, index),
                "width_m": opening.get("width_m"),
                "height_m": opening.get("height_m"),
                "pv_kg_m2": pv_kg_m2,
                "structural_system": structural_system,
                "radiation_percentage": opening.get("radiation_percentage", 100.0),
                "emissivity": opening.get("emissivity", 1.0),
                "falling_parts_risk": opening.get("falling_parts_risk", False),
                "fall_height_m": opening.get("fall_height_m"),
            }
            result["openings"].append(calculate_opening_distance(opening_payload))

    group_payload = payload.get("group")
    if isinstance(group_payload, dict):
        if not openings:
            raise CalculationError("'group' requires 'openings'.")
        percentage = calculate_opening_percentage(
            openings,
            group_payload.get("bounding_width_m"),
            group_payload.get("bounding_height_m"),
        )
        result["group"] = {
            "geometry": percentage,
            "requires_10481_confirmation": percentage["requires_10481_confirmation"],
        }
        if percentage["requires_10481_confirmation"]:
            result["requires_10481_confirmation"] = True
        else:
            opening_distance = calculate_opening_distance(
                {
                    "opening_id": group_payload.get("group_id", "opening_group"),
                    "width_m": group_payload.get("bounding_width_m"),
                    "height_m": group_payload.get("bounding_height_m"),
                    "pv_kg_m2": payload.get("pv_kg_m2"),
                    "structural_system": payload.get("structural_system", "noncombustible"),
                    "radiation_percentage": percentage["p0_percent"],
                    "emissivity": group_payload.get("emissivity", 1.0),
                    "falling_parts_risk": group_payload.get("falling_parts_risk", False),
                    "fall_height_m": group_payload.get("fall_height_m"),
                }
            )
            result["group"]["distance"] = opening_distance

    if openings and (payload.get("layout") is not None or payload.get("gaps_m") is not None):
        geometry = calculate_opening_group(
            {
                "openings": openings,
                "layout": payload.get("layout"),
                "gaps_m": payload.get("gaps_m"),
            }
        )
        result["group"] = {
            "geometry": geometry,
            "requires_10481_confirmation": geometry["requires_10481_confirmation"],
        }
        if geometry["requires_10481_confirmation"]:
            result["requires_10481_confirmation"] = True
        else:
            group_distance = calculate_opening_distance(
                {
                    "opening_id": payload.get("group_id", "opening_group"),
                    "width_m": geometry["bounding_width_m"],
                    "height_m": geometry["bounding_height_m"],
                    "pv_kg_m2": payload.get("pv_kg_m2"),
                    "structural_system": payload.get("structural_system", "noncombustible"),
                    "radiation_percentage": geometry["p0_percent"],
                    "emissivity": payload.get("emissivity", 1.0),
                    "falling_parts_risk": payload.get("falling_parts_risk", False),
                    "fall_height_m": payload.get("fall_height_m"),
                }
            )
            result["group"]["distance"] = group_distance

    spacing_checks = payload.get("spacing_checks", [])
    if spacing_checks:
        if not isinstance(spacing_checks, list):
            raise CalculationError("'spacing_checks' must be a list.")
        for item in spacing_checks:
            result["individual_spacing_checks"].append(check_individual_opening_spacing(item))

    return result

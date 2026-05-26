from __future__ import annotations

import unittest

from fire_api.engine import (
    assess_etics,
    assess_roof,
    calculate_opening_distance,
    calculate_opening_percentage,
    check_individual_opening_spacing,
    roof_distance_table_15,
)


class EngineTests(unittest.TestCase):
    def test_opening_distance_basic(self) -> None:
        result = calculate_opening_distance(
            {
                "width_m": 1.2,
                "height_m": 1.5,
                "pv_kg_m2": 45,
                "structural_system": "mixed",
            }
        )
        self.assertGreater(result["result"]["final_distance_m"], 1.0)
        self.assertLess(result["result"]["final_distance_m"], 20.0)

    def test_opening_percentage_marks_low_ratio(self) -> None:
        result = calculate_opening_percentage(
            [
                {"width_m": 1.0, "height_m": 1.0},
                {"width_m": 1.0, "height_m": 1.0},
            ],
            4.0,
            4.0,
        )
        self.assertAlmostEqual(result["radiation_percentage"], 12.5)
        self.assertTrue(result["individual_assessment_prompt_required"])

    def test_spacing_check(self) -> None:
        result = check_individual_opening_spacing(3.0, 1.5, 1.0)
        self.assertTrue(result["passes"])

    def test_roof_exception_b1(self) -> None:
        result = assess_roof(
            {
                "pv_kg_m2": 30,
                "fire_safety_level": "II",
                "roof_requirement_status": "splňuje 8.15.1 a)",
            }
        )
        self.assertEqual(result["matched_rule"]["id"], "CSN730802_8_15_4_B1")

    def test_etics_a1(self) -> None:
        result = assess_etics(
            {
                "insulation_thickness_mm": 240,
                "insulation_reaction_class": "A1",
            }
        )
        self.assertFalse(result["matched_rule"]["released_heat_assessment_required"])

    def test_table_15_interpolation(self) -> None:
        result = roof_distance_table_15(3.5, 10.0)
        self.assertGreater(result["distance_m"], 5.0)
        self.assertLess(result["distance_m"], 6.5)


if __name__ == "__main__":
    unittest.main()


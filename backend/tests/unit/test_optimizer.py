import json
import os
import unittest
from app.services.optimizer import (
    optimize_schedule,
    validate_schedule,
    build_scenario_context,
    solve_with_fallback,
)
from app.schemas.enums import BatteryAction


def get_sample_cases():
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "../../../BUP_CSE_FEST_2026_Participant_Docs/BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json"),
        os.path.join(os.getcwd(), "BUP_CSE_FEST_2026_Participant_Docs/BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json"),
        os.path.join(os.getcwd(), "../BUP_CSE_FEST_2026_Participant_Docs/BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("cases", [])
    return []


class TestOptimizer(unittest.TestCase):

    def test_all_10_public_sample_cases(self):
        cases = get_sample_cases()
        self.assertEqual(len(cases), 10, f"Expected 10 sample cases, found {len(cases)}")

        for case in cases:
            case_id = case["id"]
            scenario_input = case["input"]
            expected_directives = case["expected_output"]["directive_interpretation"]
            expected_cost = case["expected_output"]["total_cost_bdt"]
            expected_grid = case["expected_output"]["total_grid_kwh"]

            # Run optimizer
            result = optimize_schedule(scenario_input, expected_directives)

            self.assertEqual(result["scenario_id"], scenario_input["scenario_id"])
            self.assertEqual(len(result["hourly_plan"]), 24)

            # Validate with independent validator
            val_res = validate_schedule(scenario_input, expected_directives, result)
            self.assertTrue(val_res.is_valid, f"Case {case_id} failed validation: {val_res.errors}")

            # Check optimal cost within tolerance (should be equal to or better than reference cost)
            cost_diff = result["total_cost_bdt"] - expected_cost
            self.assertLessEqual(cost_diff, 0.05, f"Case {case_id} cost {result['total_cost_bdt']} exceeded expected {expected_cost} by {cost_diff}")

    def test_validator_detects_energy_imbalance(self):
        cases = get_sample_cases()
        if not cases:
            return
        case = cases[0]
        result = optimize_schedule(case["input"], case["expected_output"]["directive_interpretation"])

        # Tamper with hour 0 grid_kwh to create energy imbalance
        result["hourly_plan"][0]["grid_kwh"] += 50.0

        val_res = validate_schedule(case["input"], case["expected_output"]["directive_interpretation"], result)
        self.assertFalse(val_res.is_valid)
        self.assertTrue(any("Energy balance violation" in err or "mismatch" in err for err in val_res.errors))

    def test_validator_detects_neutrality_violation(self):
        cases = get_sample_cases()
        if not cases:
            return
        case = cases[0]
        result = optimize_schedule(case["input"], case["expected_output"]["directive_interpretation"])

        # Tamper with hour 23 battery energy
        result["hourly_plan"][23]["battery_energy_after_kwh"] += 20.0

        val_res = validate_schedule(case["input"], case["expected_output"]["directive_interpretation"], result)
        self.assertFalse(val_res.is_valid)
        self.assertTrue(any("neutrality" in err.lower() or "mismatch" in err.lower() for err in val_res.errors))

    def test_fallback_solver_produces_valid_plan(self):
        cases = get_sample_cases()
        if not cases:
            return
        case = cases[0]
        ctx = build_scenario_context(case["input"], case["expected_output"]["directive_interpretation"])
        raw_sol = solve_with_fallback(ctx)

        self.assertIn("grid_kwh", raw_sol)
        self.assertEqual(len(raw_sol["grid_kwh"]), 24)
        self.assertEqual(len(raw_sol["battery_energy_after_kwh"]), 24)


if __name__ == "__main__":
    unittest.main()

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from app.services.optimizer.matrix_builder import ScenarioContext, build_scenario_context


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)


def validate_schedule(
    scenario: Union[Dict[str, Any], Any],
    directives: Optional[List[Union[Dict[str, Any], Any]]],
    schedule: Union[Dict[str, Any], Any],
    tolerance: float = 0.01,
) -> ValidationResult:
    """
    Independent schedule validator.
    Replays the schedule hour-by-hour and verifies against all GridWise and directive rules.
    """
    errors: List[str] = []
    warnings: List[str] = []

    try:
        ctx = build_scenario_context(scenario, directives)
    except Exception as e:
        return ValidationResult(is_valid=False, errors=[f"Scenario context parsing error: {str(e)}"])

    # Extract hourly_plan
    if hasattr(schedule, "hourly_plan"):
        raw_plan = schedule.hourly_plan
        claimed_total_grid = getattr(schedule, "total_grid_kwh", None)
        claimed_total_cost = getattr(schedule, "total_cost_bdt", None)
        claimed_peak_grid = getattr(schedule, "peak_grid_kwh", None)
    elif isinstance(schedule, dict):
        raw_plan = schedule.get("hourly_plan", [])
        claimed_total_grid = schedule.get("total_grid_kwh")
        claimed_total_cost = schedule.get("total_cost_bdt")
        claimed_peak_grid = schedule.get("peak_grid_kwh")
    else:
        return ValidationResult(is_valid=False, errors=["Schedule must be a dict or response object."])

    # 1. Horizon checks
    if len(raw_plan) != 24:
        errors.append(f"hourly_plan must contain exactly 24 entries, got {len(raw_plan)}.")
        return ValidationResult(is_valid=False, errors=errors)

    plan_by_hour: Dict[int, Dict[str, Any]] = {}
    for idx, item in enumerate(raw_plan):
        if hasattr(item, "hour"):
            h = item.hour
            g = float(item.grid_kwh)
            s_u = float(item.solar_used_kwh)
            raw_action = item.battery_action
            b_kwh = float(item.battery_kwh)
            soc = float(item.battery_energy_after_kwh)
        elif isinstance(item, dict):
            h = item.get("hour", idx)
            g = float(item.get("grid_kwh", 0.0))
            s_u = float(item.get("solar_used_kwh", 0.0))
            raw_action = item.get("battery_action", "idle")
            b_kwh = float(item.get("battery_kwh", 0.0))
            soc = float(item.get("battery_energy_after_kwh", 0.0))
        else:
            errors.append(f"Invalid hourly plan item at index {idx}.")
            continue

        if hasattr(raw_action, "value"):
            action = str(raw_action.value).lower()
        elif isinstance(raw_action, str) and "." in raw_action:
            action = raw_action.split(".")[-1].lower()
        else:
            action = str(raw_action).lower()

        plan_by_hour[h] = {
            "grid_kwh": g,
            "solar_used_kwh": s_u,
            "battery_action": action.lower(),
            "battery_kwh": b_kwh,
            "battery_energy_after_kwh": soc,
        }

    # Verify all hours 0..23 present
    for h in range(24):
        if h not in plan_by_hour:
            errors.append(f"Missing hour {h} in hourly_plan.")

    if errors:
        return ValidationResult(is_valid=False, errors=errors)

    # 2. Replay hour by hour
    recalculated_grid: List[float] = []
    recalculated_cost: List[float] = []
    prev_soc = ctx.battery_initial_energy

    for h in range(24):
        entry = plan_by_hour[h]
        g = entry["grid_kwh"]
        s_u = entry["solar_used_kwh"]
        action = entry["battery_action"]
        b_kwh = entry["battery_kwh"]
        soc = entry["battery_energy_after_kwh"]

        # Non-negative checks
        if g < -tolerance:
            errors.append(f"Hour {h}: Negative grid_kwh ({g}).")
        if s_u < -tolerance:
            errors.append(f"Hour {h}: Negative solar_used_kwh ({s_u}).")
        if b_kwh < -tolerance:
            errors.append(f"Hour {h}: Negative battery_kwh ({b_kwh}).")
        if soc < -tolerance:
            errors.append(f"Hour {h}: Negative battery_energy_after_kwh ({soc}).")

        # Action consistency
        if action not in ["charge", "discharge", "idle"]:
            errors.append(f"Hour {h}: Invalid battery_action '{action}'.")
        elif action == "idle" and b_kwh > tolerance:
            errors.append(f"Hour {h}: Idle battery action must have battery_kwh = 0, got {b_kwh}.")

        # Hourly rate limits
        if action == "charge" and b_kwh > ctx.max_charge_rate + tolerance:
            errors.append(
                f"Hour {h}: Charge {b_kwh} exceeds max charge rate {ctx.max_charge_rate}."
            )
        if action == "discharge" and b_kwh > ctx.max_discharge_rate + tolerance:
            errors.append(
                f"Hour {h}: Discharge {b_kwh} exceeds max discharge rate {ctx.max_discharge_rate}."
            )

        # Directive: No-charge window
        if not ctx.can_charge[h] and action == "charge" and b_kwh > tolerance:
            errors.append(f"Hour {h}: Battery charge forbidden by no_charge_window directive.")

        # Directive: No-discharge window
        if not ctx.can_discharge[h] and action == "discharge" and b_kwh > tolerance:
            errors.append(f"Hour {h}: Battery discharge forbidden by no_discharge_window directive.")

        # Solar usage limit
        if s_u > ctx.effective_solar[h] + tolerance:
            errors.append(
                f"Hour {h}: solar_used_kwh ({s_u}) exceeds effective solar ({ctx.effective_solar[h]})."
            )

        # Energy balance: grid + solar_used + discharge = demand + charge
        ch = b_kwh if action == "charge" else 0.0
        dis = b_kwh if action == "discharge" else 0.0
        lhs = g + s_u + dis
        rhs = ctx.demand[h] + ch
        if abs(lhs - rhs) > tolerance:
            errors.append(
                f"Hour {h}: Energy balance violation: grid({g}) + solar({s_u}) + dis({dis}) = {lhs:.3f} != demand({ctx.demand[h]}) + ch({ch}) = {rhs:.3f}."
            )

        # Directive: Max grid window
        if g > ctx.max_grid[h] + tolerance:
            errors.append(
                f"Hour {h}: grid_kwh ({g}) exceeds max_grid_window limit ({ctx.max_grid[h]})."
            )

        # Battery transition
        expected_soc = prev_soc + ch - dis
        if abs(soc - expected_soc) > tolerance:
            errors.append(
                f"Hour {h}: Battery state transition mismatch: expected {expected_soc:.3f}, got {soc:.3f}."
            )

        # Battery capacity & minimum reserve
        if soc > ctx.battery_capacity + tolerance:
            errors.append(
                f"Hour {h}: battery_energy_after_kwh ({soc}) exceeds battery capacity ({ctx.battery_capacity})."
            )
        if soc < ctx.min_battery_reserve[h] - tolerance:
            errors.append(
                f"Hour {h}: battery_energy_after_kwh ({soc}) below required minimum reserve ({ctx.min_battery_reserve[h]})."
            )

        prev_soc = soc
        recalculated_grid.append(g)
        recalculated_cost.append(g * ctx.tariff[h])

    # 3. End-of-day battery neutrality
    if abs(prev_soc - ctx.battery_initial_energy) > tolerance:
        errors.append(
            f"End-of-day neutrality violation: final energy {prev_soc:.3f} != initial energy {ctx.battery_initial_energy:.3f}."
        )

    # 4. Check recalculated totals against claimed totals
    calc_total_grid = sum(recalculated_grid)
    calc_total_cost = sum(recalculated_cost)
    calc_peak_grid = max(recalculated_grid) if recalculated_grid else 0.0

    if claimed_total_grid is not None and abs(float(claimed_total_grid) - calc_total_grid) > tolerance:
        errors.append(
            f"Total grid kWh mismatch: claimed {claimed_total_grid}, recalculated {calc_total_grid:.3f}."
        )
    if claimed_total_cost is not None and abs(float(claimed_total_cost) - calc_total_cost) > tolerance:
        errors.append(
            f"Total cost BDT mismatch: claimed {claimed_total_cost}, recalculated {calc_total_cost:.3f}."
        )
    if claimed_peak_grid is not None and abs(float(claimed_peak_grid) - calc_peak_grid) > tolerance:
        errors.append(
            f"Peak grid kWh mismatch: claimed {claimed_peak_grid}, recalculated {calc_peak_grid:.3f}."
        )

    metrics = {
        "total_grid_kwh": calc_total_grid,
        "total_cost_bdt": calc_total_cost,
        "peak_grid_kwh": calc_peak_grid,
    }

    return ValidationResult(
        is_valid=(len(errors) == 0),
        errors=errors,
        warnings=warnings,
        metrics=metrics,
    )

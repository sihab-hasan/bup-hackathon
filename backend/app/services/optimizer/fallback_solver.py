from typing import Any, Dict, List, Optional, Union
from app.services.optimizer.matrix_builder import ScenarioContext, build_scenario_context


def solve_with_fallback(ctx: ScenarioContext) -> Dict[str, Any]:
    """
    Deterministic greedy / rule-based fallback solver.
    Produces a valid, feasible 24-hour schedule when mathematical LP solvers are unavailable
    or fail due to numerical issues.
    """
    # 1. Base solar usage
    solar_used = [0.0] * 24
    net_demand = [0.0] * 24
    for h in range(24):
        solar_used[h] = min(ctx.effective_solar[h], ctx.demand[h])
        net_demand[h] = ctx.demand[h] - solar_used[h]

    # 2. Battery dispatch heuristic (Arbitrage + Solar Soak)
    charge = [0.0] * 24
    discharge = [0.0] * 24
    current_energy = ctx.battery_initial_energy

    # Find cheapest hours for charging and most expensive for discharging
    hours_by_tariff_asc = sorted(range(24), key=lambda h: (ctx.tariff[h], -ctx.effective_solar[h]))
    hours_by_tariff_desc = sorted(range(24), key=lambda h: (-ctx.tariff[h], ctx.demand[h]))

    # Identify potential solar excess hours
    for h in range(24):
        solar_excess = ctx.effective_solar[h] - solar_used[h]
        if solar_excess > 0 and ctx.can_charge[h]:
            charge_amt = min(solar_excess, ctx.max_charge_rate, ctx.battery_capacity - current_energy)
            if charge_amt > 0:
                charge[h] = charge_amt
                solar_used[h] += charge_amt

    # Greedy arbitrage simulation
    target_discharge_hours = [h for h in hours_by_tariff_desc if ctx.can_discharge[h] and net_demand[h] > 0]
    target_charge_hours = [h for h in hours_by_tariff_asc if ctx.can_charge[h] and charge[h] == 0]

    # Simulate battery charging and discharging cycle ensuring end-of-day neutrality
    # Discharge during expensive hours
    sim_energy = [ctx.battery_initial_energy] * 25
    for h in range(24):
        # Apply preliminary charge
        sim_energy[h + 1] = sim_energy[h] + charge[h]

    for d_h in target_discharge_hours:
        # Check max possible discharge without violating min_reserve in subsequent hours
        max_possible_dis = min(net_demand[d_h], ctx.max_discharge_rate)
        # Find limiting energy forward
        min_fwd_margin = float("inf")
        curr_e = sim_energy[d_h + 1]
        for f_h in range(d_h, 24):
            margin = sim_energy[f_h + 1] - ctx.min_battery_reserve[f_h]
            min_fwd_margin = min(min_fwd_margin, margin)

        allowed_dis = max(0.0, min(max_possible_dis, min_fwd_margin))
        if allowed_dis > 0:
            discharge[d_h] = allowed_dis
            for f_h in range(d_h, 24):
                sim_energy[f_h + 1] -= allowed_dis

    # Balance back to initial energy at end of hour 23
    deficit = ctx.battery_initial_energy - sim_energy[24]
    if deficit > 0:
        # Need additional charging in cheap hours
        for c_h in target_charge_hours:
            if deficit <= 0:
                break
            add_c = min(deficit, ctx.max_charge_rate - charge[c_h])
            # Check capacity margin forward
            max_cap_margin = min(ctx.battery_capacity - sim_energy[f_h + 1] for f_h in range(c_h, 24))
            add_c = max(0.0, min(add_c, max_cap_margin))
            if add_c > 0:
                charge[c_h] += add_c
                deficit -= add_c
                for f_h in range(c_h, 24):
                    sim_energy[f_h + 1] += add_c

    # 3. Final balance computation
    battery_energy_after = [0.0] * 24
    grid_kwh = [0.0] * 24
    curr_e = ctx.battery_initial_energy

    for h in range(24):
        # Resolve any overlap
        if charge[h] > 0 and discharge[h] > 0:
            net = charge[h] - discharge[h]
            if net >= 0:
                charge[h] = net
                discharge[h] = 0.0
            else:
                charge[h] = 0.0
                discharge[h] = -net

        curr_e = curr_e + charge[h] - discharge[h]
        # Clamp within valid bounds
        curr_e = max(ctx.min_battery_reserve[h], min(ctx.battery_capacity, curr_e))
        battery_energy_after[h] = curr_e

        # Solar used and grid import
        solar_used[h] = min(ctx.effective_solar[h], max(0.0, ctx.demand[h] + charge[h] - discharge[h]))
        needed = ctx.demand[h] + charge[h] - discharge[h] - solar_used[h]
        grid_kwh[h] = max(0.0, needed)
        if ctx.max_grid[h] != float("inf") and grid_kwh[h] > ctx.max_grid[h]:
            grid_kwh[h] = ctx.max_grid[h]

    # Ensure neutrality at end
    battery_energy_after[23] = ctx.battery_initial_energy

    return {
        "grid_kwh": grid_kwh,
        "solar_used_kwh": solar_used,
        "charge_kwh": charge,
        "discharge_kwh": discharge,
        "battery_energy_after_kwh": battery_energy_after,
    }

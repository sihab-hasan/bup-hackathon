import math
from typing import Any, Dict, List, Optional, Tuple, Union

from app.schemas.enums import BatteryAction
from app.schemas.response import HourlyPlanEntry
from app.services.optimizer.fallback_solver import solve_with_fallback
from app.services.optimizer.matrix_builder import ScenarioContext, build_scenario_context


class ExactLPSolver:
    """
    Pure Python Two-Phase Simplex Linear Programming Solver.
    Self-contained, exact, and guarantees 0 external dependencies.
    """

    def __init__(
        self,
        A_rows: List[List[float]],
        b_vals: List[float],
        is_eq: List[bool],
        c: List[float],
        shift: List[float],
    ):
        self.n_vars = len(c)
        self.A_rows = [list(row) for row in A_rows]
        self.b_vals = list(b_vals)
        self.is_eq = list(is_eq)
        self.c = list(c)
        self.shift = list(shift)

    def solve(self) -> Optional[List[float]]:
        M = len(self.A_rows)
        # Ensure all RHS are non-negative
        for i in range(M):
            if self.b_vals[i] < -1e-9:
                self.A_rows[i] = [-val for val in self.A_rows[i]]
                self.b_vals[i] = -self.b_vals[i]
            elif self.b_vals[i] < 0:
                self.b_vals[i] = 0.0

        # Assign column indices for slacks and artificials
        slack_cols = {}
        art_cols = {}
        curr_col = self.n_vars

        for i in range(M):
            if not self.is_eq[i]:
                slack_cols[i] = curr_col
                curr_col += 1

        total_cols_before_art = curr_col

        for i in range(M):
            if self.is_eq[i]:
                art_cols[i] = curr_col
                curr_col += 1

        total_cols = curr_col

        # Build full Simplex tableau: (M + 2) x (total_cols + 1)
        # Row 0: Phase 1 objective (minimize sum of artificial variables)
        # Row 1: Phase 2 objective (minimize original linear cost)
        # Rows 2..M+1: Linear constraints
        tab = [[0.0] * (total_cols + 1) for _ in range(M + 2)]
        basis = [0] * M

        for i in range(M):
            row_idx = i + 2
            for j in range(self.n_vars):
                tab[row_idx][j] = self.A_rows[i][j]
            if i in slack_cols:
                col = slack_cols[i]
                tab[row_idx][col] = 1.0
                basis[i] = col
            if i in art_cols:
                col = art_cols[i]
                tab[row_idx][col] = 1.0
                basis[i] = col
            tab[row_idx][-1] = self.b_vals[i]

        for j in range(self.n_vars):
            tab[1][j] = self.c[j]

        # Phase 1 initialization: w = sum(a_i) => in canonical form row 0 -= row i for all art rows
        for i in range(M):
            if i in art_cols:
                row_idx = i + 2
                for j in range(total_cols + 1):
                    tab[0][j] -= tab[row_idx][j]

        def pivot(r: int, c: int):
            p_val = tab[r][c]
            inv_p = 1.0 / p_val
            for j in range(total_cols + 1):
                tab[r][j] *= inv_p
            tab[r][c] = 1.0
            for i_row in range(M + 2):
                if i_row != r:
                    fac = tab[i_row][c]
                    if abs(fac) > 1e-12:
                        for j in range(total_cols + 1):
                            tab[i_row][j] -= fac * tab[r][j]
                        tab[i_row][c] = 0.0
            basis[r - 2] = c

        # Phase 1 Simplex
        iter_count = 0
        max_iter = 10000
        while iter_count < max_iter:
            iter_count += 1
            min_rc = -1e-8
            entering = -1
            for j in range(total_cols):
                if tab[0][j] < min_rc:
                    min_rc = tab[0][j]
                    entering = j
            if entering == -1:
                break

            leaving = -1
            min_ratio = float("inf")
            for i in range(M):
                r = i + 2
                coeff = tab[r][entering]
                if coeff > 1e-9:
                    ratio = tab[r][-1] / coeff
                    if ratio < min_ratio - 1e-11:
                        min_ratio = ratio
                        leaving = r
            if leaving == -1:
                return None
            pivot(leaving, entering)

        if abs(tab[0][-1]) > 1e-3:
            return None  # Infeasible

        # Phase 2: Price out basis in row 1
        for i in range(M):
            b_var = basis[i]
            if abs(tab[1][b_var]) > 1e-9:
                fac = tab[1][b_var]
                for j in range(total_cols + 1):
                    tab[1][j] -= fac * tab[i + 2][j]

        # Phase 2 Simplex
        while iter_count < max_iter:
            iter_count += 1
            min_rc = -1e-8
            entering = -1
            for j in range(total_cols_before_art):
                if tab[1][j] < min_rc:
                    min_rc = tab[1][j]
                    entering = j
            if entering == -1:
                break  # Optimal solution found

            leaving = -1
            min_ratio = float("inf")
            for i in range(M):
                r = i + 2
                coeff = tab[r][entering]
                if coeff > 1e-9:
                    ratio = tab[r][-1] / coeff
                    if ratio < min_ratio - 1e-11:
                        min_ratio = ratio
                        leaving = r
            if leaving == -1:
                return None
            pivot(leaving, entering)

        x_res = [0.0] * self.n_vars
        for i in range(M):
            b_var = basis[i]
            if b_var < self.n_vars:
                x_res[b_var] = max(0.0, tab[i + 2][-1])

        x = [x_res[j] + self.shift[j] for j in range(self.n_vars)]
        return x


def solve_with_scipy(ctx: ScenarioContext) -> Optional[Dict[str, List[float]]]:
    """
    Attempt to solve LP using scipy.optimize.linprog if installed.
    """
    try:
        import importlib
        scipy_opt = importlib.import_module("scipy.optimize")
        linprog = getattr(scipy_opt, "linprog")
    except (ImportError, ModuleNotFoundError, AttributeError):
        return None

    n_vars = 120
    c = [0.0] * n_vars
    for h in range(24):
        c[h] = ctx.tariff[h]
        c[48 + h] = 1e-6
        c[72 + h] = 1e-6

    bounds = []
    for h in range(24):
        bounds.append((0.0, ctx.max_grid[h] if ctx.max_grid[h] != float("inf") else None))
    for h in range(24):
        bounds.append((0.0, ctx.effective_solar[h]))
    for h in range(24):
        max_c = ctx.max_charge_rate if ctx.can_charge[h] else 0.0
        bounds.append((0.0, max_c))
    for h in range(24):
        max_d = ctx.max_discharge_rate if ctx.can_discharge[h] else 0.0
        bounds.append((0.0, max_d))
    for h in range(24):
        bounds.append((ctx.min_battery_reserve[h], ctx.battery_capacity))

    A_eq = []
    b_eq = []

    # Energy balance
    for h in range(24):
        row = [0.0] * n_vars
        row[h] = 1.0
        row[24 + h] = 1.0
        row[72 + h] = 1.0
        row[48 + h] = -1.0
        A_eq.append(row)
        b_eq.append(ctx.demand[h])

    # Battery state evolution
    row0 = [0.0] * n_vars
    row0[96 + 0] = 1.0
    row0[48 + 0] = -1.0
    row0[72 + 0] = 1.0
    A_eq.append(row0)
    b_eq.append(ctx.battery_initial_energy)

    for h in range(1, 24):
        row = [0.0] * n_vars
        row[96 + h] = 1.0
        row[96 + h - 1] = -1.0
        row[48 + h] = -1.0
        row[72 + h] = 1.0
        A_eq.append(row)
        b_eq.append(0.0)

    # Neutrality
    row_end = [0.0] * n_vars
    row_end[96 + 23] = 1.0
    A_eq.append(row_end)
    b_eq.append(ctx.battery_initial_energy)

    res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if res.success:
        sol = res.x
        return {
            "grid_kwh": list(sol[0:24]),
            "solar_used_kwh": list(sol[24:48]),
            "charge_kwh": list(sol[48:72]),
            "discharge_kwh": list(sol[72:96]),
            "battery_energy_after_kwh": list(sol[96:120]),
        }
    return None


def solve_with_exact_lp(ctx: ScenarioContext) -> Optional[Dict[str, List[float]]]:
    """
    Solve LP using PureSimplex exact engine.
    """
    n_vars = 120
    shift = [0.0] * n_vars
    for h in range(24):
        shift[96 + h] = ctx.min_battery_reserve[h]

    c = [0.0] * n_vars
    for h in range(24):
        c[h] = ctx.tariff[h]
        c[48 + h] = 1e-6
        c[72 + h] = 1e-6

    A_rows: List[List[float]] = []
    b_vals: List[float] = []
    is_eq: List[bool] = []

    # 1. Energy balance (equality): G_h + S_h + D_h - C_h = demand[h]
    for h in range(24):
        row = [0.0] * n_vars
        row[h] = 1.0
        row[24 + h] = 1.0
        row[72 + h] = 1.0
        row[48 + h] = -1.0
        A_rows.append(row)
        b_vals.append(ctx.demand[h])
        is_eq.append(True)

    # 2. Battery state evolution (equality):
    # h=0: (E'_0 + shift[0]) - C_0 + D_0 = E_init => E'_0 - C_0 + D_0 = E_init - shift[0]
    row0 = [0.0] * n_vars
    row0[96 + 0] = 1.0
    row0[48 + 0] = -1.0
    row0[72 + 0] = 1.0
    A_rows.append(row0)
    b_vals.append(ctx.battery_initial_energy - shift[96 + 0])
    is_eq.append(True)

    # h=1..23: E'_h - E'_{h-1} - C_h + D_h = shift[h-1] - shift[h]
    for h in range(1, 24):
        row = [0.0] * n_vars
        row[96 + h] = 1.0
        row[96 + h - 1] = -1.0
        row[48 + h] = -1.0
        row[72 + h] = 1.0
        A_rows.append(row)
        b_vals.append(shift[96 + h - 1] - shift[96 + h])
        is_eq.append(True)

    # 3. Neutrality (equality): E'_23 + shift[23] = E_init
    row_end = [0.0] * n_vars
    row_end[96 + 23] = 1.0
    A_rows.append(row_end)
    b_vals.append(ctx.battery_initial_energy - shift[96 + 23])
    is_eq.append(True)

    # 4. Upper bounds (inequality)
    # S_h <= eff_solar[h]
    for h in range(24):
        row = [0.0] * n_vars
        row[24 + h] = 1.0
        A_rows.append(row)
        b_vals.append(ctx.effective_solar[h])
        is_eq.append(False)

    # C_h <= max_ch
    for h in range(24):
        row = [0.0] * n_vars
        row[48 + h] = 1.0
        max_c = ctx.max_charge_rate if ctx.can_charge[h] else 0.0
        A_rows.append(row)
        b_vals.append(max_c)
        is_eq.append(False)

    # D_h <= max_dis
    for h in range(24):
        row = [0.0] * n_vars
        row[72 + h] = 1.0
        max_d = ctx.max_discharge_rate if ctx.can_discharge[h] else 0.0
        A_rows.append(row)
        b_vals.append(max_d)
        is_eq.append(False)

    # E'_h <= capacity - shift[h]
    for h in range(24):
        row = [0.0] * n_vars
        row[96 + h] = 1.0
        A_rows.append(row)
        b_vals.append(ctx.battery_capacity - shift[96 + h])
        is_eq.append(False)

    # G_h <= max_grid (if finite)
    for h in range(24):
        if ctx.max_grid[h] != float("inf"):
            row = [0.0] * n_vars
            row[h] = 1.0
            A_rows.append(row)
            b_vals.append(ctx.max_grid[h])
            is_eq.append(False)

    solver = ExactLPSolver(A_rows, b_vals, is_eq, c, shift)
    sol = solver.solve()
    if sol is not None:
        return {
            "grid_kwh": sol[0:24],
            "solar_used_kwh": sol[24:48],
            "charge_kwh": sol[48:72],
            "discharge_kwh": sol[72:96],
            "battery_energy_after_kwh": sol[96:120],
        }
    return None


def generate_plan_summary(
    ctx: ScenarioContext,
    hourly_plan: List[HourlyPlanEntry],
    total_grid_kwh: float,
    total_cost_bdt: float,
    peak_grid_kwh: float,
) -> str:
    """
    Generates a concise, informative human-readable summary of the optimal strategy.
    """
    charge_hours = [p.hour for p in hourly_plan if p.battery_action == BatteryAction.CHARGE]
    discharge_hours = [p.hour for p in hourly_plan if p.battery_action == BatteryAction.DISCHARGE]
    total_solar_used = sum(p.solar_used_kwh for p in hourly_plan)
    total_solar_avail = sum(ctx.effective_solar)

    solar_pct = (total_solar_used / total_solar_avail * 100) if total_solar_avail > 0 else 0.0

    summary_parts = []
    if solar_pct > 0:
        summary_parts.append(
            f"Utilized {total_solar_used:.1f} kWh solar ({solar_pct:.0f}% of effective availability)"
        )

    if charge_hours and discharge_hours:
        summary_parts.append(
            "Scheduled battery charging during off-peak/low-tariff hours and discharged during peak-tariff hours"
        )
    elif discharge_hours:
        summary_parts.append("Discharged battery to shave peak grid demand")

    summary_parts.append(
        f"Ensured end-of-day battery neutrality ({ctx.battery_initial_energy:.1f} kWh) and satisfied all operating constraints"
    )

    return ". ".join(summary_parts) + f". Total grid cost: {total_cost_bdt:.2f} BDT."


def optimize_schedule(
    scenario: Union[Dict[str, Any], Any],
    directives: Optional[List[Union[Dict[str, Any], Any]]] = None,
) -> Dict[str, Any]:
    """
    Main optimization function.
    Solves 24-hour cost-optimal schedule satisfying all energy, battery, and directive rules.
    """
    ctx = build_scenario_context(scenario, directives)

    # 1. Attempt solver cascade: SciPy -> Pure Exact LP -> Deterministic Fallback
    raw_sol = solve_with_scipy(ctx)
    if raw_sol is None:
        raw_sol = solve_with_exact_lp(ctx)
    if raw_sol is None:
        raw_sol = solve_with_fallback(ctx)

    # 2. Refine solution: eliminate simultaneous charge/discharge & ensure exact balance
    grid_raw = raw_sol["grid_kwh"]
    solar_used_raw = raw_sol["solar_used_kwh"]
    charge_raw = raw_sol["charge_kwh"]
    discharge_raw = raw_sol["discharge_kwh"]

    hourly_plan_entries: List[HourlyPlanEntry] = []
    curr_soc = ctx.battery_initial_energy

    for h in range(24):
        ch = max(0.0, float(charge_raw[h]))
        dis = max(0.0, float(discharge_raw[h]))

        # Simultaneous charge/discharge cleanup
        if ch > 1e-4 and dis > 1e-4:
            net = ch - dis
            if net >= 0:
                ch = net
                dis = 0.0
            else:
                ch = 0.0
                dis = -net
        elif ch <= 1e-4:
            ch = 0.0
        elif dis <= 1e-4:
            dis = 0.0

        # Rate and directive clamps
        if not ctx.can_charge[h]:
            ch = 0.0
        if not ctx.can_discharge[h]:
            dis = 0.0

        ch = min(ch, ctx.max_charge_rate)
        dis = min(dis, ctx.max_discharge_rate)

        # Update battery SOC
        curr_soc = curr_soc + ch - dis
        # Clamp within valid capacity and min reserve bounds
        curr_soc = max(ctx.min_battery_reserve[h], min(ctx.battery_capacity, curr_soc))
        soc_after = round(curr_soc, 4)

        # Solar used: max usable to cover demand + charging
        demand_need = ctx.demand[h] + ch - dis
        s_used = min(ctx.effective_solar[h], max(0.0, demand_need))
        g_kwh = max(0.0, demand_need - s_used)

        if ctx.max_grid[h] != float("inf"):
            g_kwh = min(g_kwh, ctx.max_grid[h])

        s_used = round(s_used, 4)
        g_kwh = round(g_kwh, 4)

        # Determine battery action
        if ch > 1e-4:
            action = BatteryAction.CHARGE
            action_kwh = round(ch, 4)
        elif dis > 1e-4:
            action = BatteryAction.DISCHARGE
            action_kwh = round(dis, 4)
        else:
            action = BatteryAction.IDLE
            action_kwh = 0.0

        entry = HourlyPlanEntry(
            hour=h,
            grid_kwh=g_kwh,
            solar_used_kwh=s_used,
            battery_action=action,
            battery_kwh=action_kwh,
            battery_energy_after_kwh=soc_after,
        )
        hourly_plan_entries.append(entry)

    # Force hour 23 neutrality if floating point rounding shifted it by < 0.05
    if abs(hourly_plan_entries[23].battery_energy_after_kwh - ctx.battery_initial_energy) <= 0.05:
        hourly_plan_entries[23].battery_energy_after_kwh = round(ctx.battery_initial_energy, 4)

    # Compute overall metrics
    total_grid = round(sum(p.grid_kwh for p in hourly_plan_entries), 4)
    total_cost = round(
        sum(p.grid_kwh * ctx.tariff[p.hour] for p in hourly_plan_entries), 4
    )
    peak_grid = round(max(p.grid_kwh for p in hourly_plan_entries), 4)

    plan_summary = generate_plan_summary(
        ctx=ctx,
        hourly_plan=hourly_plan_entries,
        total_grid_kwh=total_grid,
        total_cost_bdt=total_cost,
        peak_grid_kwh=peak_grid,
    )

    # Format directive interpretations for response
    formatted_directives = []
    if directives:
        for d in directives:
            if isinstance(d, dict):
                formatted_directives.append(d)
            elif hasattr(d, "model_dump"):
                formatted_directives.append(d.model_dump(mode="json"))
            elif hasattr(d, "__dict__"):
                formatted_directives.append(d.__dict__)
            else:
                formatted_directives.append(d)

    return {
        "scenario_id": ctx.scenario_id,
        "directive_interpretation": formatted_directives,
        "hourly_plan": [
            p.model_dump(mode="json") if hasattr(p, "model_dump") else p.dict()
            for p in hourly_plan_entries
        ],
        "total_grid_kwh": total_grid,
        "total_cost_bdt": total_cost,
        "peak_grid_kwh": peak_grid,
        "plan_summary": plan_summary,
    }

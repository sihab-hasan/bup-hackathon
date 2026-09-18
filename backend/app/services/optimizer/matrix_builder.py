from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
import math


@dataclass
class ScenarioContext:
    scenario_id: str
    hours: List[int]
    demand: List[float]
    solar: List[float]
    effective_solar: List[float]
    tariff: List[float]
    
    # Battery parameters
    battery_capacity: float
    battery_initial_energy: float
    battery_min_energy: float
    max_charge_rate: float
    max_discharge_rate: float
    
    # Directive overrides per hour
    min_battery_reserve: List[float]
    can_charge: List[bool]
    can_discharge: List[bool]
    max_grid: List[float]


def build_scenario_context(
    scenario: Union[Dict[str, Any], Any],
    directives: Optional[List[Union[Dict[str, Any], Any]]] = None,
) -> ScenarioContext:
    """
    Parses scenario data and applies validated directive constraints to construct
    the optimization model context.
    """
    # Extract top-level attributes
    if hasattr(scenario, "scenario_id"):
        scenario_id = str(scenario.scenario_id)
        raw_hours = scenario.hours
        raw_battery = scenario.battery
    elif isinstance(scenario, dict):
        scenario_id = str(scenario.get("scenario_id", "UNKNOWN"))
        raw_hours = scenario.get("hours", [])
        raw_battery = scenario.get("battery", {})
    else:
        raise ValueError("Invalid scenario object provided.")

    # Sort hourly entries by hour 0..23
    hours_dict: Dict[int, Dict[str, float]] = {}
    for entry in raw_hours:
        if hasattr(entry, "hour"):
            h = int(entry.hour)
            d = float(entry.demand_kwh)
            s = float(entry.solar_kwh)
            t = float(entry.tariff_bdt_per_kwh)
        elif isinstance(entry, dict):
            h = int(entry["hour"])
            d = float(entry["demand_kwh"])
            s = float(entry["solar_kwh"])
            t = float(entry["tariff_bdt_per_kwh"])
        else:
            continue
        hours_dict[h] = {"demand": d, "solar": s, "tariff": t}

    if len(hours_dict) != 24:
        # Fallback for missing hours or non-consecutive
        for h in range(24):
            if h not in hours_dict:
                hours_dict[h] = {"demand": 0.0, "solar": 0.0, "tariff": 0.0}

    hours_list = list(range(24))
    demand = [hours_dict[h]["demand"] for h in hours_list]
    solar = [hours_dict[h]["solar"] for h in hours_list]
    effective_solar = [hours_dict[h]["solar"] for h in hours_list]
    tariff = [hours_dict[h]["tariff"] for h in hours_list]

    # Extract battery parameters
    if hasattr(raw_battery, "capacity_kwh"):
        battery_capacity = float(raw_battery.capacity_kwh)
        battery_initial = float(raw_battery.initial_energy_kwh)
        battery_min = float(raw_battery.minimum_energy_kwh)
        max_ch = float(raw_battery.max_charge_kwh_per_hour)
        max_dis = float(raw_battery.max_discharge_kwh_per_hour)
    elif isinstance(raw_battery, dict):
        battery_capacity = float(raw_battery.get("capacity_kwh", 0.0))
        battery_initial = float(raw_battery.get("initial_energy_kwh", 0.0))
        battery_min = float(raw_battery.get("minimum_energy_kwh", 0.0))
        max_ch = float(raw_battery.get("max_charge_kwh_per_hour", 0.0))
        max_dis = float(raw_battery.get("max_discharge_kwh_per_hour", 0.0))
    else:
        battery_capacity = 0.0
        battery_initial = 0.0
        battery_min = 0.0
        max_ch = 0.0
        max_dis = 0.0

    # Initialize per-hour constraint arrays
    min_battery_reserve = [battery_min] * 24
    can_charge = [True] * 24
    can_discharge = [True] * 24
    max_grid = [float("inf")] * 24

    # Apply directives
    if directives:
        for d in directives:
            # Check if directive applies
            applies = False
            d_type = None
            adj = None

            if hasattr(d, "applies"):
                applies = bool(d.applies)
                d_type = getattr(d, "directive_type", "")
                if hasattr(d_type, "value"):
                    d_type = d_type.value
                adj = getattr(d, "structured_adjustment", None)
            elif isinstance(d, dict):
                applies = bool(d.get("applies", False))
                d_type = d.get("directive_type", "")
                if hasattr(d_type, "value"):
                    d_type = d_type.value
                adj = d.get("structured_adjustment")

            if not applies or not adj:
                continue

            # Convert adjustment to dict if object
            adj_dict = {}
            if hasattr(adj, "model_dump"):
                adj_dict = adj.model_dump()
            elif hasattr(adj, "__dict__"):
                adj_dict = adj.__dict__
            elif isinstance(adj, dict):
                adj_dict = adj

            affected_hours = adj_dict.get("hours", [])

            if d_type == "solar_reduction":
                factor = float(adj_dict.get("factor", 1.0))
                factor = max(0.0, min(1.0, factor))
                for h in affected_hours:
                    if 0 <= h < 24:
                        effective_solar[h] = solar[h] * factor

            elif d_type == "minimum_battery_reserve":
                min_kwh = float(adj_dict.get("minimum_energy_kwh", battery_min))
                for h in affected_hours:
                    if 0 <= h < 24:
                        min_battery_reserve[h] = max(min_battery_reserve[h], min_kwh)

            elif d_type == "no_charge_window":
                for h in affected_hours:
                    if 0 <= h < 24:
                        can_charge[h] = False

            elif d_type == "no_discharge_window":
                for h in affected_hours:
                    if 0 <= h < 24:
                        can_discharge[h] = False

            elif d_type == "max_grid_window":
                grid_limit = float(adj_dict.get("max_grid_kwh", float("inf")))
                for h in affected_hours:
                    if 0 <= h < 24:
                        max_grid[h] = min(max_grid[h], grid_limit)

    return ScenarioContext(
        scenario_id=scenario_id,
        hours=hours_list,
        demand=demand,
        solar=solar,
        effective_solar=effective_solar,
        tariff=tariff,
        battery_capacity=battery_capacity,
        battery_initial_energy=battery_initial,
        battery_min_energy=battery_min,
        max_charge_rate=max_ch,
        max_discharge_rate=max_dis,
        min_battery_reserve=min_battery_reserve,
        can_charge=can_charge,
        can_discharge=can_discharge,
        max_grid=max_grid,
    )

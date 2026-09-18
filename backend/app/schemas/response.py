from typing import List
from pydantic import BaseModel, Field
from app.schemas.directives import DirectiveInterpretation
from app.schemas.enums import BatteryAction


class HourlyPlanEntry(BaseModel):
    hour: int = Field(..., ge=0, le=23, description="Hour from 0 to 23")
    grid_kwh: float = Field(..., ge=0.0, description="Non-negative grid energy purchased")
    solar_used_kwh: float = Field(..., ge=0.0, description="Solar energy used in this hour")
    battery_action: BatteryAction = Field(..., description="Action: charge, discharge, or idle")
    battery_kwh: float = Field(..., ge=0.0, description="Magnitude of battery action, 0 when idle")
    battery_energy_after_kwh: float = Field(
        ..., ge=0.0, description="Battery energy state after completing this hour"
    )


class OptimizeEnergyResponse(BaseModel):
    scenario_id: str = Field(..., description="Must match request scenario_id")
    directive_interpretation: List[DirectiveInterpretation] = Field(
        ..., description="Directive interpretation per operator note in note_index order"
    )
    hourly_plan: List[HourlyPlanEntry] = Field(..., description="Exactly 24 hourly plan entries")
    total_grid_kwh: float = Field(..., ge=0.0, description="Sum of grid_kwh across 24 hours")
    total_cost_bdt: float = Field(..., ge=0.0, description="Total grid electricity cost in BDT")
    peak_grid_kwh: float = Field(..., ge=0.0, description="Maximum hourly grid_kwh")
    plan_summary: str = Field(..., description="Human-readable explanation of optimization strategy")

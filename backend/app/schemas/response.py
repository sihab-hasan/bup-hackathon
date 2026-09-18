from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.directives import DirectiveInterpretation
from app.schemas.enums import BatteryAction


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HourlyPlanItem(StrictModel):
    hour: int = Field(ge=0, le=23)
    grid_kwh: float = Field(ge=0, allow_inf_nan=False)
    solar_used_kwh: float = Field(ge=0, allow_inf_nan=False)
    battery_action: BatteryAction
    battery_kwh: float = Field(ge=0, allow_inf_nan=False)
    battery_energy_after_kwh: float = Field(ge=0, allow_inf_nan=False)


# Optimizer PR compatibility while the public API keeps HourlyPlanItem.
HourlyPlanEntry = HourlyPlanItem


class OptimizerResult(StrictModel):
    hourly_plan: list[HourlyPlanItem] = Field(min_length=24, max_length=24)
    plan_summary: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_plan_hours(self) -> OptimizerResult:
        plan_hours = [item.hour for item in self.hourly_plan]
        if set(plan_hours) != set(range(24)):
            raise ValueError(
                "hourly_plan must contain each hour from 0 through 23 exactly once"
            )
        self.hourly_plan = sorted(self.hourly_plan, key=lambda item: item.hour)
        self.plan_summary = self.plan_summary.strip()
        return self


class OptimizationResponse(StrictModel):
    scenario_id: str
    directive_interpretation: list[DirectiveInterpretation]
    hourly_plan: list[HourlyPlanItem]
    total_grid_kwh: float = Field(ge=0, allow_inf_nan=False)
    total_cost_bdt: float = Field(ge=0, allow_inf_nan=False)
    peak_grid_kwh: float = Field(ge=0, allow_inf_nan=False)
    plan_summary: str


class HealthResponse(StrictModel):
    status: str = "ok"


class ErrorDetail(StrictModel):
    code: str
    message: str


class ErrorResponse(StrictModel):
    error: ErrorDetail

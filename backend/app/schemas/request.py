from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HourInput(StrictModel):
    hour: int = Field(ge=0, le=23)
    demand_kwh: float = Field(ge=0, allow_inf_nan=False)
    solar_kwh: float = Field(ge=0, allow_inf_nan=False)
    tariff_bdt_per_kwh: float = Field(ge=0, allow_inf_nan=False)


class BatteryConfig(StrictModel):
    capacity_kwh: float = Field(gt=0, allow_inf_nan=False)
    initial_energy_kwh: float = Field(ge=0, allow_inf_nan=False)
    minimum_energy_kwh: float = Field(ge=0, allow_inf_nan=False)
    max_charge_kwh_per_hour: float = Field(ge=0, allow_inf_nan=False)
    max_discharge_kwh_per_hour: float = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_energy_bounds(self) -> BatteryConfig:
        if self.minimum_energy_kwh > self.capacity_kwh:
            raise ValueError("minimum_energy_kwh cannot exceed capacity_kwh")
        if self.initial_energy_kwh > self.capacity_kwh:
            raise ValueError("initial_energy_kwh cannot exceed capacity_kwh")
        if self.initial_energy_kwh < self.minimum_energy_kwh:
            raise ValueError("initial_energy_kwh cannot be below minimum_energy_kwh")
        return self


OPENAPI_REQUEST_EXAMPLE = {
    "scenario_id": "swagger-sample",
    "operator_notes": ["No operational changes today."],
    "hours": [
        {
            "hour": hour,
            "demand_kwh": 1,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5,
        }
        for hour in range(24)
    ],
    "battery": {
        "capacity_kwh": 10,
        "initial_energy_kwh": 5,
        "minimum_energy_kwh": 1,
        "max_charge_kwh_per_hour": 2,
        "max_discharge_kwh_per_hour": 2,
    },
}


class OptimizationRequest(StrictModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": OPENAPI_REQUEST_EXAMPLE},
    )
    scenario_id: str = Field(min_length=1, max_length=200)
    operator_notes: list[str] = Field(min_length=1, max_length=3)
    hours: list[HourInput] = Field(min_length=24, max_length=24)
    battery: BatteryConfig

    @model_validator(mode="after")
    def validate_scenario(self) -> OptimizationRequest:
        scenario_id = self.scenario_id.strip()
        notes = [note.strip() for note in self.operator_notes]
        if not scenario_id:
            raise ValueError("scenario_id cannot be blank")
        if any(not note for note in notes):
            raise ValueError("operator_notes cannot contain blank notes")

        received_hours = [item.hour for item in self.hours]
        if set(received_hours) != set(range(24)):
            raise ValueError("hours must contain each hour from 0 through 23 exactly once")

        self.scenario_id = scenario_id
        self.operator_notes = notes
        self.hours = sorted(self.hours, key=lambda item: item.hour)
        return self

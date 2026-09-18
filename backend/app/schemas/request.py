from typing import List
from pydantic import BaseModel, Field


class HourEntry(BaseModel):
    hour: int = Field(..., ge=0, le=23, description="Hour of the day from 0 to 23")
    demand_kwh: float = Field(..., ge=0.0, description="Campus demand in kWh")
    solar_kwh: float = Field(..., ge=0.0, description="Base solar energy available in kWh")
    tariff_bdt_per_kwh: float = Field(..., ge=0.0, description="Grid electricity price in BDT per kWh")


class BatteryConfig(BaseModel):
    capacity_kwh: float = Field(..., ge=0.0, description="Maximum energy battery can store in kWh")
    initial_energy_kwh: float = Field(..., ge=0.0, description="Battery energy at start of hour 0 in kWh")
    minimum_energy_kwh: float = Field(..., ge=0.0, description="Base reserve level battery must never go below in kWh")
    max_charge_kwh_per_hour: float = Field(..., ge=0.0, description="Maximum energy added per hour in kWh")
    max_discharge_kwh_per_hour: float = Field(..., ge=0.0, description="Maximum energy removed per hour in kWh")


class OptimizeEnergyRequest(BaseModel):
    scenario_id: str = Field(..., description="Unique scenario identifier")
    operator_notes: List[str] = Field(..., description="List of 1 to 3 natural-language notes")
    hours: List[HourEntry] = Field(..., description="Exactly 24 hourly entries for hours 0 to 23")
    battery: BatteryConfig = Field(..., description="Battery configuration parameters")

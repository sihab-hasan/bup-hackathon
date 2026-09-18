from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field
from app.schemas.enums import DirectiveType


class SolarReductionAdjustment(BaseModel):
    hours: List[int] = Field(..., description="List of affected hours (0-23)")
    factor: float = Field(..., ge=0.0, le=1.0, description="Usable solar fraction (0.0 to 1.0)")


class MinimumBatteryReserveAdjustment(BaseModel):
    hours: List[int] = Field(..., description="List of affected hours (0-23)")
    minimum_energy_kwh: float = Field(..., ge=0.0, description="Minimum battery energy reserve in kWh")


class NoChargeWindowAdjustment(BaseModel):
    hours: List[int] = Field(..., description="List of affected hours where battery charging is blocked")


class NoDischargeWindowAdjustment(BaseModel):
    hours: List[int] = Field(..., description="List of affected hours where battery discharging is blocked")


class MaxGridWindowAdjustment(BaseModel):
    hours: List[int] = Field(..., description="List of affected hours")
    max_grid_kwh: float = Field(..., ge=0.0, description="Maximum allowed grid import in kWh")


StructuredAdjustment = Union[
    SolarReductionAdjustment,
    MinimumBatteryReserveAdjustment,
    NoChargeWindowAdjustment,
    NoDischargeWindowAdjustment,
    MaxGridWindowAdjustment,
    dict,
    None,
]


class DirectiveInterpretation(BaseModel):
    note_index: int = Field(..., description="0-based index of corresponding operator note")
    applies: bool = Field(..., description="True if non-no_op, False only for no_op")
    directive_type: DirectiveType = Field(..., description="Supported directive type")
    structured_adjustment: Optional[Any] = Field(
        None, description="Structured parameters for the directive, or None for no_op"
    )
    explanation: str = Field(..., description="Human-readable explanation of interpretation")

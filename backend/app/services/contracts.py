from __future__ import annotations

from typing import Protocol

from app.schemas import (
    BatteryConfig,
    DirectiveInterpretation,
    OptimizationRequest,
    OptimizerResult,
)


class NoteInterpreter(Protocol):
    async def interpret_notes(
        self,
        operator_notes: list[str],
        battery: BatteryConfig,
    ) -> list[DirectiveInterpretation]: ...


class EnergyOptimizer(Protocol):
    def optimize(
        self,
        scenario: OptimizationRequest,
        directives: list[DirectiveInterpretation],
    ) -> OptimizerResult: ...


class ScheduleValidator(Protocol):
    def validate(
        self,
        scenario: OptimizationRequest,
        directives: list[DirectiveInterpretation],
        result: OptimizerResult,
    ) -> None: ...

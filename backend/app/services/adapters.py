from app.core.exceptions import (
    InvalidScheduleError,
    LLMUnavailableError,
    OptimizationUnavailableError,
)
from app.schemas import (
    BatteryConfig,
    DirectiveInterpretation,
    OptimizationRequest,
    OptimizerResult,
)


class UnconfiguredNoteInterpreter:
    async def interpret_notes(
        self,
        operator_notes: list[str],
        battery: BatteryConfig,
    ) -> list[DirectiveInterpretation]:
        raise LLMUnavailableError("LLM interpreter has not been configured")


class UnconfiguredEnergyOptimizer:
    def optimize(
        self,
        scenario: OptimizationRequest,
        directives: list[DirectiveInterpretation],
    ) -> OptimizerResult:
        raise OptimizationUnavailableError("Energy optimizer has not been configured")


class UnconfiguredScheduleValidator:
    def validate(
        self,
        scenario: OptimizationRequest,
        directives: list[DirectiveInterpretation],
        result: OptimizerResult,
    ) -> None:
        raise InvalidScheduleError("Schedule validator has not been configured")

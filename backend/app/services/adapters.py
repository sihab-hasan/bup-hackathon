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
    def __init__(self, message: str = "LLM interpreter has not been configured") -> None:
        self.message = message

    async def interpret_notes(
        self,
        operator_notes: list[str],
        battery: BatteryConfig,
    ) -> list[DirectiveInterpretation]:
        raise LLMUnavailableError(self.message)


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

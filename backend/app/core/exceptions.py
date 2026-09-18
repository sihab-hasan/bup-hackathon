from dataclasses import dataclass


@dataclass(slots=True)
class AppError(Exception):
    status_code: int
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


class LLMUnavailableError(AppError):
    def __init__(self, message: str = "LLM service is unavailable") -> None:
        super().__init__(503, "llm_unavailable", message)


class LLMOutputError(AppError):
    def __init__(self, message: str = "LLM returned an invalid interpretation") -> None:
        super().__init__(502, "invalid_llm_output", message)


class OptimizationUnavailableError(AppError):
    def __init__(self, message: str = "Optimization service is unavailable") -> None:
        super().__init__(503, "optimizer_unavailable", message)


class InfeasibleScenarioError(AppError):
    def __init__(self, message: str = "Scenario has no feasible schedule") -> None:
        super().__init__(422, "infeasible_scenario", message)


class InvalidScheduleError(AppError):
    def __init__(self, message: str = "Generated schedule failed validation") -> None:
        super().__init__(500, "invalid_generated_schedule", message)

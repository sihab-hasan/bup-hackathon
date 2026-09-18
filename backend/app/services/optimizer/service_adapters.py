from app.core.exceptions import InvalidScheduleError
from app.schemas import DirectiveInterpretation, OptimizationRequest, OptimizerResult
from app.services.optimizer.balance_auditor import validate_schedule
from app.services.optimizer.solver import optimize_schedule


class GridWiseEnergyOptimizer:
    def optimize(
        self,
        scenario: OptimizationRequest,
        directives: list[DirectiveInterpretation],
    ) -> OptimizerResult:
        result = optimize_schedule(scenario, directives)
        return OptimizerResult.model_validate(
            {
                "hourly_plan": result["hourly_plan"],
                "plan_summary": result["plan_summary"],
            }
        )


class GridWiseScheduleValidator:
    def validate(
        self,
        scenario: OptimizationRequest,
        directives: list[DirectiveInterpretation],
        result: OptimizerResult,
    ) -> None:
        audit = validate_schedule(scenario, directives, result)
        if not audit.is_valid:
            details = "; ".join(audit.errors[:3])
            raise InvalidScheduleError(f"Generated schedule failed validation: {details}")

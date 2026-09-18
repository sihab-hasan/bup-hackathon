from __future__ import annotations

import asyncio
from math import fsum

from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.core.exceptions import (
    AppError,
    InvalidScheduleError,
    LLMUnavailableError,
    OptimizationUnavailableError,
)
from app.schemas import OptimizationRequest, OptimizationResponse
from app.services.contracts import EnergyOptimizer, NoteInterpreter, ScheduleValidator
from app.services.guardrails.directive_rules import validate_directive_interpretations


class EnergyService:
    def __init__(
        self,
        interpreter: NoteInterpreter,
        optimizer: EnergyOptimizer,
        schedule_validator: ScheduleValidator,
        settings: Settings,
    ) -> None:
        self.interpreter = interpreter
        self.optimizer = optimizer
        self.schedule_validator = schedule_validator
        self.settings = settings

    async def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
        try:
            directives = await asyncio.wait_for(
                self.interpreter.interpret_notes(
                    request.operator_notes,
                    request.battery,
                ),
                timeout=self.settings.llm_timeout_seconds,
            )
        except TimeoutError as exc:
            raise LLMUnavailableError("LLM request timed out") from exc
        except AppError:
            raise
        except Exception as exc:
            raise LLMUnavailableError() from exc

        validated_directives = validate_directive_interpretations(
            directives,
            note_count=len(request.operator_notes),
            battery=request.battery,
        )

        try:
            result = await asyncio.wait_for(
                run_in_threadpool(
                    self.optimizer.optimize,
                    request,
                    validated_directives,
                ),
                timeout=self.settings.optimizer_timeout_seconds,
            )
        except TimeoutError as exc:
            raise OptimizationUnavailableError("Optimizer timed out") from exc
        except AppError:
            raise
        except Exception as exc:
            raise OptimizationUnavailableError() from exc

        try:
            await run_in_threadpool(
                self.schedule_validator.validate,
                request,
                validated_directives,
                result,
            )
        except AppError:
            raise
        except Exception as exc:
            raise InvalidScheduleError() from exc

        tariffs = {hour.hour: hour.tariff_bdt_per_kwh for hour in request.hours}
        total_grid = fsum(item.grid_kwh for item in result.hourly_plan)
        total_cost = fsum(
            item.grid_kwh * tariffs[item.hour] for item in result.hourly_plan
        )
        peak_grid = max(item.grid_kwh for item in result.hourly_plan)

        return OptimizationResponse(
            scenario_id=request.scenario_id,
            directive_interpretation=validated_directives,
            hourly_plan=result.hourly_plan,
            total_grid_kwh=round(total_grid, 2),
            total_cost_bdt=round(total_cost, 2),
            peak_grid_kwh=round(peak_grid, 2),
            plan_summary=result.plan_summary,
        )

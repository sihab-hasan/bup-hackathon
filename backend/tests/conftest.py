from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_energy_service
from app.core.config import get_settings
from app.main import app
from app.schemas import (
    BatteryAction,
    BatteryConfig,
    DirectiveInterpretation,
    DirectiveType,
    HourlyPlanItem,
    OptimizationRequest,
    OptimizerResult,
)
from app.services.energy import EnergyService


class FakeInterpreter:
    async def interpret_notes(
        self,
        operator_notes: list[str],
        battery: BatteryConfig,
    ) -> list[DirectiveInterpretation]:
        return [
            DirectiveInterpretation(
                note_index=index,
                applies=False,
                directive_type=DirectiveType.NO_OP,
                structured_adjustment=None,
                explanation="This note does not affect the energy schedule.",
            )
            for index, _ in enumerate(operator_notes)
        ]


class FakeOptimizer:
    def optimize(
        self,
        scenario: OptimizationRequest,
        directives: list[DirectiveInterpretation],
    ) -> OptimizerResult:
        return OptimizerResult(
            hourly_plan=[
                HourlyPlanItem(
                    hour=hour.hour,
                    grid_kwh=hour.demand_kwh,
                    solar_used_kwh=0,
                    battery_action=BatteryAction.IDLE,
                    battery_kwh=0,
                    battery_energy_after_kwh=scenario.battery.initial_energy_kwh,
                )
                for hour in scenario.hours
            ],
            plan_summary="Mock schedule for API integration tests.",
        )


class FakeScheduleValidator:
    def validate(
        self,
        scenario: OptimizationRequest,
        directives: list[DirectiveInterpretation],
        result: OptimizerResult,
    ) -> None:
        return None


@pytest.fixture
def valid_payload() -> dict[str, object]:
    return {
        "scenario_id": "integration-case",
        "operator_notes": ["No operational changes today."],
        "hours": [
            {
                "hour": hour,
                "demand_kwh": 10 + hour,
                "solar_kwh": 0,
                "tariff_bdt_per_kwh": 5,
            }
            for hour in range(24)
        ],
        "battery": {
            "capacity_kwh": 50,
            "initial_energy_kwh": 20,
            "minimum_energy_kwh": 10,
            "max_charge_kwh_per_hour": 5,
            "max_discharge_kwh_per_hour": 5,
        },
    }


@pytest.fixture
def client() -> Iterator[TestClient]:
    service = EnergyService(
        interpreter=FakeInterpreter(),
        optimizer=FakeOptimizer(),
        schedule_validator=FakeScheduleValidator(),
        settings=get_settings(),
    )
    app.dependency_overrides[get_energy_service] = lambda: service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

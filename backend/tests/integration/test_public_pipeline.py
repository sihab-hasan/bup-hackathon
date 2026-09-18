import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.deps import get_energy_service
from app.core.config import get_settings
from app.main import app
from app.schemas import BatteryConfig, DirectiveInterpretation
from app.services.energy import EnergyService
from app.services.optimizer.balance_auditor import validate_schedule
from app.services.optimizer.service_adapters import (
    GridWiseEnergyOptimizer,
    GridWiseScheduleValidator,
)


SAMPLE_PACK = (
    Path(__file__).parents[3]
    / "BUP_CSE_FEST_2026_Participant_Docs"
    / "BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json"
)


class ExpectedInterpreter:
    def __init__(self, directives: list[dict[str, object]]) -> None:
        self.directives = directives

    async def interpret_notes(
        self,
        operator_notes: list[str],
        battery: BatteryConfig,
    ) -> list[DirectiveInterpretation]:
        return [
            DirectiveInterpretation.model_validate(item) for item in self.directives
        ]


def test_production_dependencies_use_real_optimizer_and_validator():
    get_energy_service.cache_clear()
    service = get_energy_service()

    assert isinstance(service.optimizer, GridWiseEnergyOptimizer)
    assert isinstance(service.schedule_validator, GridWiseScheduleValidator)


def test_all_public_cases_pass_the_full_api_optimization_pipeline():
    cases = json.loads(SAMPLE_PACK.read_text(encoding="utf-8"))["cases"]

    with TestClient(app) as client:
        for case in cases:
            expected_directives = case["expected_output"]["directive_interpretation"]
            service = EnergyService(
                interpreter=ExpectedInterpreter(expected_directives),
                optimizer=GridWiseEnergyOptimizer(),
                schedule_validator=GridWiseScheduleValidator(),
                settings=get_settings(),
            )
            app.dependency_overrides[get_energy_service] = lambda: service

            started = time.perf_counter()
            response = client.post("/optimize-energy", json=case["input"])
            elapsed = time.perf_counter() - started

            assert response.status_code == 200, (case["id"], response.text)
            assert elapsed < 30, case["id"]
            body = response.json()
            assert body["scenario_id"] == case["input"]["scenario_id"]
            assert len(body["directive_interpretation"]) == len(
                case["input"]["operator_notes"]
            )
            assert len(body["hourly_plan"]) == 24
            audit = validate_schedule(case["input"], expected_directives, body)
            assert audit.is_valid, (case["id"], audit.errors)

    app.dependency_overrides.clear()

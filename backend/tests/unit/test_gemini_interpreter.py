from types import SimpleNamespace

import pytest

from app.core.exceptions import LLMOutputError, LLMUnavailableError
from app.schemas import BatteryConfig, DirectiveType
from app.services.interpreter.gemini import GeminiNoteInterpreter


class FakeGeminiClient:
    def __init__(self, response=None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls = []

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


@pytest.fixture
def battery():
    return BatteryConfig(
        capacity_kwh=200,
        initial_energy_kwh=100,
        minimum_energy_kwh=40,
        max_charge_kwh_per_hour=50,
        max_discharge_kwh_per_hour=50,
    )


@pytest.mark.asyncio
async def test_interprets_structured_gemini_response(battery):
    response = SimpleNamespace(
        parsed={
            "directives": [
                {
                    "note_index": 0,
                    "applies": True,
                    "directive_type": "solar_reduction",
                    "hours": [11, 12, 13],
                    "factor": 0.2,
                    "explanation": "An 80% reduction leaves 20% usable solar.",
                },
                {
                    "note_index": 1,
                    "applies": False,
                    "directive_type": "no_op",
                    "explanation": "The note is unrelated to energy operations.",
                },
            ]
        }
    )
    client = FakeGeminiClient(response=response)
    interpreter = GeminiNoteInterpreter(
        api_key="test-key", model="test-model", client=client
    )

    directives = await interpreter.interpret_notes(
        ["Solar will be reduced by 80% from 11 AM to 2 PM.", "Club notice."],
        battery,
    )

    assert directives[0].directive_type == DirectiveType.SOLAR_REDUCTION
    assert directives[0].structured_adjustment == {
        "hours": [11, 12, 13],
        "factor": 0.2,
    }
    assert directives[1].directive_type == DirectiveType.NO_OP
    assert directives[1].structured_adjustment is None
    assert client.calls[0]["model"] == "test-model"
    assert "Battery capacity: 200.0 kWh" in client.calls[0]["contents"]


@pytest.mark.asyncio
async def test_rejects_fields_for_wrong_directive(battery):
    response = SimpleNamespace(
        parsed={
            "directives": [
                {
                    "note_index": 0,
                    "applies": True,
                    "directive_type": "no_charge_window",
                    "hours": [2, 3],
                    "factor": 0.5,
                    "explanation": "Charging is disabled.",
                }
            ]
        }
    )
    interpreter = GeminiNoteInterpreter(
        api_key="test-key",
        model="test-model",
        client=FakeGeminiClient(response=response),
    )

    with pytest.raises(LLMOutputError, match="invalid fields"):
        await interpreter.interpret_notes(["Do not charge from 2 to 4."], battery)


@pytest.mark.asyncio
async def test_rejects_malformed_response(battery):
    interpreter = GeminiNoteInterpreter(
        api_key="test-key",
        model="test-model",
        client=FakeGeminiClient(response=SimpleNamespace(parsed=None, text="bad")),
    )

    with pytest.raises(LLMOutputError, match="invalid structured output"):
        await interpreter.interpret_notes(["No changes."], battery)


@pytest.mark.asyncio
async def test_maps_provider_failure_to_service_error(battery):
    interpreter = GeminiNoteInterpreter(
        api_key="test-key",
        model="test-model",
        client=FakeGeminiClient(error=RuntimeError("network down")),
    )

    with pytest.raises(LLMUnavailableError, match="Gemini request failed"):
        await interpreter.interpret_notes(["No changes."], battery)

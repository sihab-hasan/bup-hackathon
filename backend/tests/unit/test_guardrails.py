import pytest

from app.core.exceptions import LLMOutputError
from app.schemas import BatteryConfig, DirectiveInterpretation, DirectiveType
from app.services.guardrails.directive_rules import validate_directive_interpretations


@pytest.fixture
def battery():
    return BatteryConfig(
        capacity_kwh=200,
        initial_energy_kwh=100,
        minimum_energy_kwh=20,
        max_charge_kwh_per_hour=40,
        max_discharge_kwh_per_hour=40,
    )


def test_accepts_public_sample_solar_reduction_shape(battery):
    directives = [
        DirectiveInterpretation(
            note_index=0,
            applies=True,
            directive_type=DirectiveType.SOLAR_REDUCTION,
            structured_adjustment={"hours": [12, 13], "factor": 0.25},
            explanation="Solar availability is reduced to 25%.",
        )
    ]

    assert validate_directive_interpretations(directives, 1, battery) == directives


def test_rejects_out_of_order_hours(battery):
    directives = [
        DirectiveInterpretation(
            note_index=0,
            applies=True,
            directive_type=DirectiveType.NO_CHARGE_WINDOW,
            structured_adjustment={"hours": [14, 13]},
            explanation="Charging is unavailable.",
        )
    ]

    with pytest.raises(LLMOutputError, match="unique and ascending"):
        validate_directive_interpretations(directives, 1, battery)


def test_rejects_wrong_no_op_semantics(battery):
    directives = [
        DirectiveInterpretation(
            note_index=0,
            applies=True,
            directive_type=DirectiveType.NO_OP,
            structured_adjustment=None,
            explanation="No scheduling impact.",
        )
    ]

    with pytest.raises(LLMOutputError, match="no_op"):
        validate_directive_interpretations(directives, 1, battery)


def test_rejects_missing_interpretation(battery):
    with pytest.raises(LLMOutputError, match="exactly one"):
        validate_directive_interpretations([], 1, battery)

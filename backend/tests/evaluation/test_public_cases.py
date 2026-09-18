import json
from pathlib import Path

from app.schemas import (
    DirectiveInterpretation,
    OptimizationRequest,
    OptimizationResponse,
)
from app.services.guardrails.directive_rules import validate_directive_interpretations


SAMPLE_PACK = (
    Path(__file__).parents[3]
    / "BUP_CSE_FEST_2026_Participant_Docs"
    / "BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json"
)


def test_all_public_cases_match_api_contract():
    data = json.loads(SAMPLE_PACK.read_text(encoding="utf-8"))

    for case in data["cases"]:
        request = OptimizationRequest.model_validate(case["input"])
        expected = OptimizationResponse.model_validate(case["expected_output"])
        validate_directive_interpretations(
            expected.directive_interpretation,
            note_count=len(request.operator_notes),
            battery=request.battery,
        )


def test_public_directives_include_explanation():
    data = json.loads(SAMPLE_PACK.read_text(encoding="utf-8"))

    for case in data["cases"]:
        for item in case["expected_output"]["directive_interpretation"]:
            directive = DirectiveInterpretation.model_validate(item)
            assert directive.explanation

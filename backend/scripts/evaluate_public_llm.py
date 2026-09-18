from __future__ import annotations

import asyncio
import json
import statistics
import time
from pathlib import Path

from app.core.config import get_settings
from app.schemas import OptimizationRequest
from app.services.guardrails.directive_rules import validate_directive_interpretations
from app.services.interpreter.factory import create_note_interpreter


SAMPLE_PACK = (
    Path(__file__).parents[2]
    / "BUP_CSE_FEST_2026_Participant_Docs"
    / "BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json"
)


def comparable(item: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in item.items()
        if key != "explanation"
    }


async def main() -> int:
    settings = get_settings()
    if not settings.api_key:
        print("ERROR: API_KEY is not configured")
        return 2

    interpreter = create_note_interpreter(settings)
    cases = json.loads(SAMPLE_PACK.read_text(encoding="utf-8"))["cases"]
    latencies: list[float] = []
    passed = 0

    for case in cases:
        request = OptimizationRequest.model_validate(case["input"])
        started = time.perf_counter()
        try:
            directives = await asyncio.wait_for(
                interpreter.interpret_notes(request.operator_notes, request.battery),
                timeout=settings.llm_timeout_seconds,
            )
            validate_directive_interpretations(
                directives,
                note_count=len(request.operator_notes),
                battery=request.battery,
            )
            actual = [
                comparable(item.model_dump(mode="json")) for item in directives
            ]
            expected = [
                comparable(item)
                for item in case["expected_output"]["directive_interpretation"]
            ]
            is_match = actual == expected
            detail = "PASS" if is_match else "MISMATCH"
            if not is_match:
                detail += f"\n  expected={expected}\n  actual={actual}"
        except Exception as exc:
            is_match = False
            detail = f"ERROR {type(exc).__name__}: {exc}"

        elapsed = time.perf_counter() - started
        latencies.append(elapsed)
        passed += int(is_match)
        print(f"{case['id']}: {detail} ({elapsed:.2f}s)", flush=True)

    ordered = sorted(latencies)
    p95_index = max(0, int(0.95 * len(ordered) + 0.999999) - 1)
    print(
        f"SUMMARY: {passed}/{len(cases)} cases passed; "
        f"mean={statistics.fmean(latencies):.2f}s; p95={ordered[p95_index]:.2f}s"
    )
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

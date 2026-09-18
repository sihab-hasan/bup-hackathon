from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


SAMPLE_PACK = (
    Path(__file__).parents[2]
    / "BUP_CSE_FEST_2026_Participant_Docs"
    / "BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json"
)


def request_json(url: str, payload: dict[str, object] | None = None) -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{request.method} {url} returned {exc.code}: {detail}") from exc


def main() -> int:
    base_url = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
    health = request_json(f"{base_url}/health")
    if health != {"status": "ok"}:
        raise RuntimeError(f"Unexpected health response: {health}")

    first_case = json.loads(SAMPLE_PACK.read_text(encoding="utf-8"))["cases"][0]
    result = request_json(f"{base_url}/optimize-energy", first_case["input"])
    if result.get("scenario_id") != first_case["input"]["scenario_id"]:
        raise RuntimeError("Optimization response did not echo scenario_id")
    if len(result.get("directive_interpretation", [])) != 2:
        raise RuntimeError("Optimization response has the wrong directive count")
    if len(result.get("hourly_plan", [])) != 24:
        raise RuntimeError("Optimization response does not contain 24 hours")

    print(f"PASS: {base_url}/health")
    print(f"PASS: {base_url}/optimize-energy ({result['scenario_id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from collections.abc import Iterable
from math import isfinite

from app.core.exceptions import LLMOutputError
from app.schemas import BatteryConfig, DirectiveInterpretation, DirectiveType


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LLMOutputError(f"{name} must be a number")
    number = float(value)
    if not isfinite(number):
        raise LLMOutputError(f"{name} must be finite")
    return number


def _hours(value: object) -> list[int]:
    if not isinstance(value, list) or not value:
        raise LLMOutputError("structured_adjustment.hours must be a non-empty list")
    if any(isinstance(hour, bool) or not isinstance(hour, int) for hour in value):
        raise LLMOutputError("directive hours must contain integers only")
    if any(hour < 0 or hour > 23 for hour in value):
        raise LLMOutputError("directive hours must be between 0 and 23")
    if value != sorted(set(value)):
        raise LLMOutputError("directive hours must be unique and ascending")
    return value


def _exact_keys(adjustment: dict[str, object], expected: set[str]) -> None:
    if set(adjustment) != expected:
        names = ", ".join(sorted(expected))
        raise LLMOutputError(f"structured_adjustment must contain exactly: {names}")


def validate_directive_interpretations(
    directives: Iterable[DirectiveInterpretation],
    note_count: int,
    battery: BatteryConfig,
) -> list[DirectiveInterpretation]:
    validated = list(directives)
    if len(validated) != note_count:
        raise LLMOutputError("LLM must return exactly one interpretation per operator note")
    if [item.note_index for item in validated] != list(range(note_count)):
        raise LLMOutputError("note_index values must match operator note order")

    for item in validated:
        if item.directive_type == DirectiveType.NO_OP:
            if item.applies or item.structured_adjustment is not None:
                raise LLMOutputError(
                    "no_op requires applies=false and structured_adjustment=null"
                )
            continue

        if not item.applies or item.structured_adjustment is None:
            raise LLMOutputError(
                "non-no_op directives require applies=true and structured_adjustment"
            )

        adjustment = item.structured_adjustment
        if item.directive_type in {
            DirectiveType.NO_CHARGE_WINDOW,
            DirectiveType.NO_DISCHARGE_WINDOW,
        }:
            _exact_keys(adjustment, {"hours"})
            _hours(adjustment["hours"])
        elif item.directive_type == DirectiveType.SOLAR_REDUCTION:
            _exact_keys(adjustment, {"hours", "factor"})
            _hours(adjustment["hours"])
            factor = _number(adjustment["factor"], "factor")
            if factor < 0 or factor > 1:
                raise LLMOutputError("solar reduction factor must be between 0 and 1")
        elif item.directive_type == DirectiveType.MINIMUM_BATTERY_RESERVE:
            _exact_keys(adjustment, {"hours", "minimum_energy_kwh"})
            _hours(adjustment["hours"])
            reserve = _number(
                adjustment["minimum_energy_kwh"], "minimum_energy_kwh"
            )
            if reserve < 0 or reserve > battery.capacity_kwh:
                raise LLMOutputError("minimum reserve must be within battery capacity")
        elif item.directive_type == DirectiveType.MAX_GRID_WINDOW:
            _exact_keys(adjustment, {"hours", "max_grid_kwh"})
            _hours(adjustment["hours"])
            cap = _number(adjustment["max_grid_kwh"], "max_grid_kwh")
            if cap < 0:
                raise LLMOutputError("maximum grid import must be non-negative")

    return validated

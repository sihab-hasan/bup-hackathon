from functools import lru_cache

from app.core.config import get_settings
from app.services.interpreter.factory import create_note_interpreter
from app.services.adapters import (
    UnconfiguredEnergyOptimizer,
    UnconfiguredScheduleValidator,
)
from app.services.energy import EnergyService


@lru_cache
def get_energy_service() -> EnergyService:
    settings = get_settings()
    return EnergyService(
        interpreter=create_note_interpreter(settings),
        optimizer=UnconfiguredEnergyOptimizer(),
        schedule_validator=UnconfiguredScheduleValidator(),
        settings=settings,
    )

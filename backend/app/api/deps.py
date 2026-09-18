from functools import lru_cache

from app.core.config import get_settings
from app.services.adapters import (
    UnconfiguredEnergyOptimizer,
    UnconfiguredNoteInterpreter,
    UnconfiguredScheduleValidator,
)
from app.services.energy import EnergyService


@lru_cache
def get_energy_service() -> EnergyService:
    return EnergyService(
        interpreter=UnconfiguredNoteInterpreter(),
        optimizer=UnconfiguredEnergyOptimizer(),
        schedule_validator=UnconfiguredScheduleValidator(),
        settings=get_settings(),
    )

from functools import lru_cache

from app.core.config import get_settings
from app.services.interpreter.factory import create_note_interpreter
from app.services.energy import EnergyService
from app.services.optimizer.service_adapters import (
    GridWiseEnergyOptimizer,
    GridWiseScheduleValidator,
)


@lru_cache
def get_energy_service() -> EnergyService:
    settings = get_settings()
    return EnergyService(
        interpreter=create_note_interpreter(settings),
        optimizer=GridWiseEnergyOptimizer(),
        schedule_validator=GridWiseScheduleValidator(),
        settings=settings,
    )

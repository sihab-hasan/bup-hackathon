from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_energy_service
from app.schemas import OptimizationRequest, OptimizationResponse
from app.services.energy import EnergyService


router = APIRouter(tags=["optimization"])


@router.post("/optimize-energy", response_model=OptimizationResponse)
async def optimize_energy(
    request: OptimizationRequest,
    service: Annotated[EnergyService, Depends(get_energy_service)],
) -> OptimizationResponse:
    return await service.optimize(request)

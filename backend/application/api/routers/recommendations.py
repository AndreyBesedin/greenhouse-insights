from fastapi import APIRouter, Depends, HTTPException

from application.api.dependencies import get_simulation_service
from application.simulation_service import RecommendationAlreadyReviewed, SimulationService
from domain.recommendation import Recommendation

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/{recommendation_id}/approve")
async def approve_recommendation(
    recommendation_id: str, service: SimulationService = Depends(get_simulation_service)
) -> Recommendation:
    try:
        result = await service.approve_recommendation(recommendation_id)
    except RecommendationAlreadyReviewed as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="recommendation not found")
    return result


@router.post("/{recommendation_id}/dismiss")
async def dismiss_recommendation(
    recommendation_id: str, service: SimulationService = Depends(get_simulation_service)
) -> Recommendation:
    try:
        result = await service.dismiss_recommendation(recommendation_id)
    except RecommendationAlreadyReviewed as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="recommendation not found")
    return result

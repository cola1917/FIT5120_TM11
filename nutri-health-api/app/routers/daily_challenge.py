"""
Daily healthy challenge router.
Provides task selection and completion feedback endpoints.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.daily_challenge import DailyHealthyChallenge
from app.schemas.daily_challenge import (
    DailyChallengeCompleteRequest,
    DailyChallengeCompleteResponse,
    DailyChallengeTask,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/daily-challenge", tags=["daily-challenge"])


def _challenge_query(db: Session, exclude_id: int | None = None):
    query = db.query(DailyHealthyChallenge)
    if exclude_id is not None:
        query = query.filter(DailyHealthyChallenge.id != exclude_id)
    return query


@router.get("/next", response_model=DailyChallengeTask, summary="Get next daily challenge")
async def get_next_challenge(
    exclude_id: int | None = Query(None, ge=1, description="Exclude the current task id"),
    db: Session = Depends(get_db),
):
    """
    Return a random daily challenge.

    If exclude_id is provided, that task will not be returned.
    """
    query = _challenge_query(db, exclude_id=exclude_id)
    task = query.order_by(func.random()).first()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No daily challenge available",
        )

    logger.info("Selected daily challenge id=%s exclude_id=%s", task.id, exclude_id)
    return DailyChallengeTask(id=task.id, task_name=task.task_name, tips=task.tips)


@router.post("/complete", response_model=DailyChallengeCompleteResponse, summary="Complete daily challenge")
async def complete_challenge(
    payload: DailyChallengeCompleteRequest,
    db: Session = Depends(get_db),
):
    """
    Return the completion feedback for a daily challenge.
    """
    task = db.get(DailyHealthyChallenge, payload.id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Daily challenge '{payload.id}' not found",
        )

    logger.info("Completed daily challenge id=%s", task.id)
    return DailyChallengeCompleteResponse(id=task.id, task_name=task.task_name, feedback=task.feedback)

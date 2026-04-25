"""
Daily healthy challenge router.
Provides task selection and completion feedback endpoints.
"""

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.daily_challenge import DailyHealthyChallenge
from app.models.user_daily_challenge import UserDailyChallengeCompletion
from app.schemas.daily_challenge import (
    DailyChallengeCompleteRequest,
    DailyChallengeCompleteResponse,
    DailyChallengeStatusResponse,
    DailyChallengeTask,
)
from app.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/daily-challenge", tags=["daily-challenge"])


# Child-friendly messages for completed challenge
COMPLETED_MESSAGE = "🌟 Wow, you're amazing! You've finished today's challenge! 🎉 Come back tomorrow for a brand new adventure!"


def _challenge_query(db: Session, exclude_id: int | None = None):
    query = db.query(DailyHealthyChallenge)
    if exclude_id is not None:
        query = query.filter(DailyHealthyChallenge.id != exclude_id)
    return query


@router.get("/status", response_model=DailyChallengeStatusResponse, summary="Check if user completed today's challenge")
async def check_challenge_status(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Check if the current user has already completed today's daily challenge.
    
    Returns a message for children if the challenge is already completed.
    """
    username = current_user.get("username", "unknown")
    today = date.today()
    
    # Check if user has completed challenge today
    completion = db.query(UserDailyChallengeCompletion).filter(
        UserDailyChallengeCompletion.username == username,
        UserDailyChallengeCompletion.completion_date == today,
    ).first()
    
    if completion:
        logger.info("User %s has already completed today's challenge", username)
        return DailyChallengeStatusResponse(
            completed_today=True,
            message=COMPLETED_MESSAGE,
        )
    
    logger.info("User %s has not completed today's challenge yet", username)
    return DailyChallengeStatusResponse(completed_today=False)


@router.get("/next", response_model=DailyChallengeTask, summary="Get next daily challenge")
async def get_next_challenge(
    exclude_id: int | None = Query(None, ge=1, description="Exclude the current task id"),
    current_user: dict = Depends(get_current_user),
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
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the completion feedback for a daily challenge.
    Also records the completion for the user to prevent re-completion today.
    """
    task = db.get(DailyHealthyChallenge, payload.id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Daily challenge '{payload.id}' not found",
        )

    username = current_user.get("username", "unknown")
    today = date.today()
    
    # Check if user has already completed a challenge today
    existing_completion = db.query(UserDailyChallengeCompletion).filter(
        UserDailyChallengeCompletion.username == username,
        UserDailyChallengeCompletion.completion_date == today,
    ).first()
    
    if not existing_completion:
        # Record the completion
        completion = UserDailyChallengeCompletion(
            username=username,
            completion_date=today,
        )
        db.add(completion)
        db.commit()
        logger.info("Recorded challenge completion for user %s on %s", username, today)

    logger.info("Completed daily challenge id=%s", task.id)
    return DailyChallengeCompleteResponse(id=task.id, task_name=task.task_name, feedback=task.feedback)

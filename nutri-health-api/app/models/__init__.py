"""Application models package."""

from app.models.cache import ScanCache
from app.models.daily_challenge import DailyHealthyChallenge
from app.models.user_daily_challenge import UserDailyChallengeCompletion
from app.models.cn_food import (
    CnCtgnme,
    CnFdes,
    CnFoodTag,
    CnGpcnme,
    CnNutdes,
    CnNutval,
    CnWght,
    RemoteAlternative,
)

__all__ = [
    "ScanCache",
    "DailyHealthyChallenge",
    "UserDailyChallengeCompletion",
    "CnCtgnme",
    "CnFdes",
    "CnFoodTag",
    "CnGpcnme",
    "CnNutdes",
    "CnNutval",
    "CnWght",
    "RemoteAlternative",
]

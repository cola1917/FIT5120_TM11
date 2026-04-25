"""
User Daily Challenge Completion Model.
Tracks which users have completed today's challenge.
"""

from datetime import date
from sqlalchemy import Column, Integer, Date, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class UserDailyChallengeCompletion(Base):
    __tablename__ = "user_daily_challenge_completion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(128), nullable=False, index=True)
    completion_date = Column(Date, nullable=False, default=date.today)
    
    # Ensure one completion per user per day
    __table_args__ = (
        UniqueConstraint('username', 'completion_date', name='uq_user_date'),
    )

    def __repr__(self):
        return f"<UserDailyChallengeCompletion(username={self.username}, date={self.completion_date})>"

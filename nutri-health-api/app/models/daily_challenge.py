"""
Daily healthy challenge task model.
"""

from sqlalchemy import Column, Integer, String, Text

from app.database import Base


class DailyHealthyChallenge(Base):
    __tablename__ = "daily_healthy_challenge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_name = Column(String(128), nullable=False, unique=True)
    tips = Column(Text, nullable=False)
    feedback = Column(Text, nullable=False)

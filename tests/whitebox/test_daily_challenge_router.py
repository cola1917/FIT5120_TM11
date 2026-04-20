import importlib

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def daily_challenge_module(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@localhost:5432/nutrihealth")
    import app.routers.daily_challenge as daily_challenge

    return importlib.reload(daily_challenge)


@pytest.fixture()
def sqlite_session(daily_challenge_module):
    engine = create_engine("sqlite:///:memory:")
    daily_challenge_module.DailyHealthyChallenge.__table__.create(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        db.add_all(
            [
                daily_challenge_module.DailyHealthyChallenge(
                    id=1,
                    task_name="Strong Bone Milk",
                    tips="Drink your milk today!",
                    feedback="Your bones are getting hard as rocks!",
                ),
                daily_challenge_module.DailyHealthyChallenge(
                    id=2,
                    task_name="Power Up Water",
                    tips="Take a big sip of water!",
                    feedback="Your body is clean and fresh inside!",
                ),
                daily_challenge_module.DailyHealthyChallenge(
                    id=3,
                    task_name="Immune Shield Fruit",
                    tips="Eat a piece of sweet fruit!",
                    feedback="You just built a shield against germs!",
                ),
            ]
        )
        db.commit()
        yield db
    finally:
        db.close()


@pytest.fixture()
def single_row_session(daily_challenge_module):
    engine = create_engine("sqlite:///:memory:")
    daily_challenge_module.DailyHealthyChallenge.__table__.create(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        db.add(
            daily_challenge_module.DailyHealthyChallenge(
                id=1,
                task_name="Strong Bone Milk",
                tips="Drink your milk today!",
                feedback="Your bones are getting hard as rocks!",
            )
        )
        db.commit()
        yield db
    finally:
        db.close()


@pytest.mark.asyncio
async def test_get_next_challenge_returns_random_task(daily_challenge_module, sqlite_session):
    result = await daily_challenge_module.get_next_challenge(exclude_id=None, db=sqlite_session)

    assert result.id in {1, 2, 3}
    assert result.task_name
    assert result.tips


@pytest.mark.asyncio
async def test_get_next_challenge_excludes_current_task(daily_challenge_module, sqlite_session):
    result = await daily_challenge_module.get_next_challenge(exclude_id=1, db=sqlite_session)

    assert result.id in {2, 3}
    assert result.id != 1


@pytest.mark.asyncio
async def test_get_next_challenge_raises_when_no_task_available(daily_challenge_module, single_row_session):
    with pytest.raises(HTTPException) as exc_info:
        await daily_challenge_module.get_next_challenge(exclude_id=1, db=single_row_session)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_complete_challenge_returns_feedback(daily_challenge_module, sqlite_session):
    result = await daily_challenge_module.complete_challenge(
        payload=daily_challenge_module.DailyChallengeCompleteRequest(id=2),
        db=sqlite_session,
    )

    assert result.id == 2
    assert result.task_name == "Power Up Water"
    assert result.feedback == "Your body is clean and fresh inside!"


@pytest.mark.asyncio
async def test_complete_challenge_raises_for_missing_id(daily_challenge_module, sqlite_session):
    with pytest.raises(HTTPException) as exc_info:
        await daily_challenge_module.complete_challenge(
            payload=daily_challenge_module.DailyChallengeCompleteRequest(id=999),
            db=sqlite_session,
        )

    assert exc_info.value.status_code == 404

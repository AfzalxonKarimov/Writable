"""
Engine/session setup, plus small helper functions that handlers will call
constantly: get_or_create_user, set_user_state, etc. Keeping these here
means handlers never touch raw SQLAlchemy session logic directly.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

import config
from db.models import Base, User

engine = create_async_engine(config.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    """Create tables if they don't exist yet. Call once on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_or_create_user(telegram_id: int, username: str | None, first_name: str | None) -> User:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=telegram_id, username=username, first_name=first_name)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


async def set_user_state(telegram_id: int, state: str, pending_data: dict | None = None) -> None:
    """
    Persist the user's current FSM state + pending_data to the DB.
    Called after EVERY step of the conversation flow -- this is what makes
    'Continue' on /start actually work after a restart or a multi-day gap.
    """
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user is None:
            return
        user.current_state = state
        if pending_data is not None:
            user.pending_data = pending_data
        await session.commit()


async def get_user(telegram_id: int) -> User | None:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()


async def clear_pending_data(telegram_id: int) -> None:
    await set_user_state(telegram_id, "IDLE", pending_data={})

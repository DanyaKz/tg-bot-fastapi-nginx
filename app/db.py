import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

class Base(DeclarativeBase):
    pass

_engine = None
_SessionLocal = None

def init_engine_and_sessionmaker(echo: bool = False):
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_async_engine(
            DATABASE_URL,
            echo=echo,
            pool_pre_ping=True,   
        )
        _SessionLocal = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)

def get_engine():
    return _engine

def get_sessionmaker():
    return _SessionLocal


async def get_session() -> AsyncSession:
    SessionLocal = get_sessionmaker()
    if SessionLocal is None:
        raise RuntimeError("SessionLocal is not initialized. Did you call init_engine_and_sessionmaker() in startup?")
    async with SessionLocal() as session:
        yield session

async def dispose_engine():
    global _engine, _SessionLocal
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _SessionLocal = None

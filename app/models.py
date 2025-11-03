from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Float, DateTime, BigInteger, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64))
    first_name: Mapped[Optional[str]] = mapped_column(String(128))
    last_name: Mapped[Optional[str]] = mapped_column(String(128))
    

class FxRate(Base):
    __tablename__ = "fx_rates"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    base: Mapped[str] = mapped_column(String(8), index=True)      
    quote: Mapped[str] = mapped_column(String(8), index=True)     
    rate: Mapped[float] = mapped_column(Float, nullable=False)    
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("base", "quote", "as_of", name="uq_fx_snapshot"),
        Index("ix_fx_base_quote_asof", "base", "quote", "as_of"),
    )

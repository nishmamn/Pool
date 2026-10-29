from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

engine = create_engine("sqlite:///pool.db")
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Pool(Base):
    __tablename__ = "pools"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    product_title: Mapped[str] = mapped_column(String(300))
    product_url: Mapped[str] = mapped_column(String(1000))
    target_amount: Mapped[float] = mapped_column(Float)
    deadline: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Contribution(Base):
    __tablename__ = "contributions"
    id: Mapped[int] = mapped_column(primary_key=True)
    pool_id: Mapped[int] = mapped_column(ForeignKey("pools.id"))
    contributor: Mapped[str] = mapped_column(String(100))
    amount: Mapped[float] = mapped_column(Float)
    order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    authorization_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    pool_id: Mapped[int | None] = mapped_column(nullable=True)
    kind: Mapped[str] = mapped_column(String(50))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


def init_db() -> None:
    Base.metadata.create_all(engine)


def log_event(pool_id, kind: str, detail: str = "") -> None:
    with SessionLocal() as s:
        s.add(Event(pool_id=pool_id, kind=kind, detail=detail))
        s.commit()


def create_pool(title, product_title, product_url, target_amount, deadline) -> Pool:
    with SessionLocal() as s:
        pool = Pool(
            title=title,
            product_title=product_title,
            product_url=product_url,
            target_amount=target_amount,
            deadline=deadline,
        )
        s.add(pool)
        s.commit()
    log_event(pool.id, "pool_created", f"{title}: goal ${target_amount:.2f}")
    return pool


def add_contribution(pool_id, contributor, amount, order_id=None,
                     authorization_id=None, status="pending") -> Contribution:
    with SessionLocal() as s:
        c = Contribution(
            pool_id=pool_id,
            contributor=contributor,
            amount=amount,
            order_id=order_id,
            authorization_id=authorization_id,
            status=status,
        )
        s.add(c)
        s.commit()
    log_event(pool_id, "contribution_added", f"{contributor} ${amount:.2f} ({status})")
    return c


def pool_total(pool_id) -> float:
    with SessionLocal() as s:
        rows = s.scalars(
            select(Contribution).where(
                Contribution.pool_id == pool_id,
                Contribution.status == "authorized",
            )
        ).all()
        return sum(c.amount for c in rows)


def list_events(pool_id):
    with SessionLocal() as s:
        return s.scalars(select(Event).where(Event.pool_id == pool_id)).all()
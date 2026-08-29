import enum
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AdminRole(str, enum.Enum):
    super_admin = "super_admin"
    moderator = "moderator"


class EventStatus(str, enum.Enum):
    pending = "pending"  # awaiting super_admin approval (moderator-created)
    active = "active"
    full = "full"
    cancelled = "cancelled"
    completed = "completed"


class RegistrationStatus(str, enum.Enum):
    active = "active"
    cancelled = "cancelled"


class University(Base):
    __tablename__ = "universities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="university")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    university_id: Mapped[int] = mapped_column(ForeignKey("universities.id"), nullable=False)
    interests: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    language: Mapped[str] = mapped_column(String(2), default="uz")  # uz / ru / en
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    university: Mapped["University"] = relationship(back_populates="users")
    registrations: Mapped[list["Registration"]] = relationship(back_populates="user")


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=True)
    role: Mapped[AdminRole] = mapped_column(Enum(AdminRole), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    events: Mapped[list["Event"]] = relationship(back_populates="created_by")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=True)
    speaker: Mapped[str] = mapped_column(String(150), nullable=True)
    format: Mapped[str] = mapped_column(String(50), nullable=False)
    participant_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[EventStatus] = mapped_column(Enum(EventStatus), default=EventStatus.pending)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("admins.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    created_by: Mapped["Admin"] = relationship(back_populates="events")
    registrations: Mapped[list["Registration"]] = relationship(back_populates="event")


class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = (UniqueConstraint("user_id", "event_id", name="uq_user_event"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    status: Mapped[RegistrationStatus] = mapped_column(Enum(RegistrationStatus), default=RegistrationStatus.active)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="registrations")
    event: Mapped["Event"] = relationship(back_populates="registrations")

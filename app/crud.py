from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import UNIVERSITIES, settings
from app.models import (
    Admin,
    AdminRole,
    Event,
    EventStatus,
    Registration,
    RegistrationStatus,
    University,
    User,
)


class RegistrationError(Exception):
    """Raised for expected registration failures (full, already registered, etc.)."""


# ---------- Universities ----------

async def seed_universities(session: AsyncSession) -> None:
    existing = (await session.execute(select(University.name))).scalars().all()
    missing = [name for name in UNIVERSITIES if name not in existing]
    for name in missing:
        session.add(University(name=name))
    if missing:
        await session.commit()


async def list_universities(session: AsyncSession) -> list[University]:
    result = await session.execute(select(University).order_by(University.name))
    return list(result.scalars().all())


# ---------- Users ----------

async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    telegram_id: int,
    full_name: str,
    university_id: int,
    interests: list[str],
    language: str = "uz",
) -> User:
    user = User(
        telegram_id=telegram_id,
        full_name=full_name,
        university_id=university_id,
        interests=interests,
        language=language,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# ---------- Admins ----------

async def get_admin_by_telegram_id(session: AsyncSession, telegram_id: int) -> Admin | None:
    result = await session.execute(select(Admin).where(Admin.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def ensure_super_admins(session: AsyncSession) -> None:
    """Promote configured SUPER_ADMIN_IDS to super_admin on startup."""
    for tg_id in settings.super_admin_ids:
        admin = await get_admin_by_telegram_id(session, tg_id)
        if admin is None:
            session.add(Admin(telegram_id=tg_id, role=AdminRole.super_admin))
    await session.commit()


# ---------- Events ----------

async def list_active_events(session: AsyncSession) -> list[Event]:
    result = await session.execute(
        select(Event)
        .where(Event.status.in_([EventStatus.active, EventStatus.full]))
        .order_by(Event.event_date)
    )
    return list(result.scalars().all())


async def get_event(session: AsyncSession, event_id: int) -> Event | None:
    result = await session.execute(select(Event).where(Event.id == event_id))
    return result.scalar_one_or_none()


async def create_event(
    session: AsyncSession,
    admin: Admin,
    title: str,
    description: str,
    event_date: datetime,
    location: str,
    speaker: str,
    format_: str,
    participant_limit: int,
) -> Event:
    # Super admin events go live immediately; moderator events wait for approval
    # if REQUIRE_EVENT_APPROVAL is on (see app/config.py).
    if admin.role == AdminRole.super_admin or not settings.REQUIRE_EVENT_APPROVAL:
        status = EventStatus.active
    else:
        status = EventStatus.pending

    event = Event(
        title=title,
        description=description,
        event_date=event_date,
        location=location,
        speaker=speaker,
        format=format_,
        participant_limit=participant_limit,
        status=status,
        created_by_id=admin.id,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def approve_event(session: AsyncSession, event: Event) -> Event:
    event.status = EventStatus.active
    await session.commit()
    await session.refresh(event)
    return event


def can_manage_event(admin: Admin, event: Event) -> bool:
    """Super admin manages everything; moderator only their own events."""
    if admin.role == AdminRole.super_admin:
        return True
    return event.created_by_id == admin.id


async def cancel_event(session: AsyncSession, event: Event) -> Event:
    event.status = EventStatus.cancelled
    await session.commit()
    await session.refresh(event)
    return event


# ---------- Registrations (race-condition safe) ----------

async def register_for_event(session: AsyncSession, user: User, event_id: int) -> Registration:
    """Locks the event row so concurrent registrations for the last seat
    can't both succeed. Note: does NOT open its own `session.begin()` —
    AsyncSession autobegins a transaction on first use, and the caller's
    session may already be mid-transaction (e.g. from an earlier lookup),
    so we commit/rollback manually instead of nesting a second begin()."""
    try:
        event = (
            await session.execute(
                select(Event).where(Event.id == event_id).with_for_update()
            )
        ).scalar_one_or_none()

        if event is None:
            raise RegistrationError("Event topilmadi.")
        if event.status not in (EventStatus.active, EventStatus.full):
            raise RegistrationError("Bu event uchun registratsiya yopiq.")

        existing = (
            await session.execute(
                select(Registration).where(
                    Registration.user_id == user.id, Registration.event_id == event_id
                )
            )
        ).scalar_one_or_none()

        if existing and existing.status == RegistrationStatus.active:
            raise RegistrationError("Siz allaqachon ro'yxatdan o'tgansiz.")

        current_count = (
            await session.execute(
                select(func.count()).where(
                    Registration.event_id == event_id,
                    Registration.status == RegistrationStatus.active,
                )
            )
        ).scalar_one()

        if current_count >= event.participant_limit:
            event.status = EventStatus.full
            await session.commit()
            raise RegistrationError("Kechirasiz, joylar tugadi.")

        if existing:
            existing.status = RegistrationStatus.active
            registration = existing
        else:
            registration = Registration(user_id=user.id, event_id=event_id)
            session.add(registration)

        # Recompute after this registration; flip to full if it was the last seat.
        if current_count + 1 >= event.participant_limit:
            event.status = EventStatus.full

        await session.commit()
    except RegistrationError:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise

    await session.refresh(registration)
    return registration


async def cancel_registration(session: AsyncSession, user: User, event_id: int) -> None:
    try:
        registration = (
            await session.execute(
                select(Registration).where(
                    Registration.user_id == user.id,
                    Registration.event_id == event_id,
                    Registration.status == RegistrationStatus.active,
                )
            )
        ).scalar_one_or_none()

        if registration is None:
            raise RegistrationError("Faol registratsiya topilmadi.")

        registration.status = RegistrationStatus.cancelled

        event = (
            await session.execute(
                select(Event).where(Event.id == event_id).with_for_update()
            )
        ).scalar_one_or_none()
        if event and event.status == EventStatus.full:
            event.status = EventStatus.active  # a seat just opened up

        await session.commit()
    except RegistrationError:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        raise


async def list_user_registrations(session: AsyncSession, user: User) -> list[Registration]:
    result = await session.execute(
        select(Registration)
        .where(Registration.user_id == user.id, Registration.status == RegistrationStatus.active)
        .order_by(Registration.registered_at.desc())
    )
    return list(result.scalars().all())


async def list_event_participants(session: AsyncSession, event_id: int) -> list[User]:
    result = await session.execute(
        select(User)
        .join(Registration, Registration.user_id == User.id)
        .where(Registration.event_id == event_id, Registration.status == RegistrationStatus.active)
    )
    return list(result.scalars().all())


# ---------- Stats (basic — pitch traction numbers) ----------

async def get_basic_stats(session: AsyncSession) -> dict:
    members = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    active_regs = (
        await session.execute(
            select(func.count()).where(Registration.status == RegistrationStatus.active)
        )
    ).scalar_one()
    events_total = (await session.execute(select(func.count()).select_from(Event))).scalar_one()
    return {"members": members, "active_registrations": active_regs, "events_total": events_total}

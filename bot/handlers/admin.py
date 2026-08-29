import csv
import io
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app import crud
from app.database import async_session
from app.models import EventStatus
from bot.keyboards import admin_menu_kb, event_formats_kb, event_manage_kb
from bot.states import CreateEvent

router = Router(name="admin")


async def _require_admin(telegram_id: int):
    async with async_session() as session:
        return await crud.get_admin_by_telegram_id(session, telegram_id)


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    admin = await _require_admin(message.from_user.id)
    if not admin:
        return  # silently ignore — not an admin, no need to reveal the command exists
    await message.answer(
        "Admin panel", reply_markup=admin_menu_kb(is_super_admin=admin.role.value == "super_admin")
    )


@router.callback_query(F.data == "admin_create_event")
async def start_create_event(callback: CallbackQuery, state: FSMContext) -> None:
    admin = await _require_admin(callback.from_user.id)
    if not admin:
        await callback.answer("Ruxsat yo'q.", show_alert=True)
        return
    await state.set_state(CreateEvent.title)
    await callback.message.answer("Event nomini kiriting:")
    await callback.answer()


@router.message(CreateEvent.title)
async def create_event_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(CreateEvent.description)
    await message.answer("Tavsifini kiriting:")


@router.message(CreateEvent.description)
async def create_event_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await state.set_state(CreateEvent.date)
    await message.answer("Sana va vaqtini kiriting (format: 25.09.2026 18:00):")


@router.message(CreateEvent.date)
async def create_event_date(message: Message, state: FSMContext) -> None:
    try:
        event_date = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer("Noto'g'ri format. Qaytadan kiriting (masalan: 25.09.2026 18:00):")
        return
    await state.update_data(event_date=event_date.isoformat())
    await state.set_state(CreateEvent.location)
    await message.answer("Joylashuvni kiriting:")


@router.message(CreateEvent.location)
async def create_event_location(message: Message, state: FSMContext) -> None:
    await state.update_data(location=message.text.strip())
    await state.set_state(CreateEvent.speaker)
    await message.answer("Spikerni kiriting (yo'q bo'lsa '-' yozing):")


@router.message(CreateEvent.speaker)
async def create_event_speaker(message: Message, state: FSMContext) -> None:
    await state.update_data(speaker=message.text.strip())
    await state.set_state(CreateEvent.format)
    await message.answer("Formatni tanlang:", reply_markup=event_formats_kb())


@router.callback_query(CreateEvent.format, F.data.startswith("fmt:"))
async def create_event_format(callback: CallbackQuery, state: FSMContext) -> None:
    fmt = callback.data.split(":", 1)[1]
    await state.update_data(format=fmt)
    await state.set_state(CreateEvent.limit)
    await callback.message.answer("Participant limitni kiriting (raqam):")
    await callback.answer()


@router.message(CreateEvent.limit)
async def create_event_limit(message: Message, state: FSMContext) -> None:
    try:
        limit = int(message.text.strip())
        if limit <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Iltimos musbat raqam kiriting:")
        return

    data = await state.get_data()
    admin = await _require_admin(message.from_user.id)

    async with async_session() as session:
        event = await crud.create_event(
            session,
            admin=admin,
            title=data["title"],
            description=data["description"],
            event_date=datetime.fromisoformat(data["event_date"]),
            location=data["location"],
            speaker=data["speaker"],
            format_=data["format"],
            participant_limit=limit,
        )

    await state.clear()
    if event.status == EventStatus.pending:
        await message.answer("Event yaratildi va super admin tasdig'ini kutmoqda. 🕓")
    else:
        await message.answer("Event yaratildi va e'lon qilindi. ✅")


@router.callback_query(F.data == "admin_my_events")
async def show_my_events(callback: CallbackQuery) -> None:
    admin = await _require_admin(callback.from_user.id)
    if not admin:
        await callback.answer("Ruxsat yo'q.", show_alert=True)
        return

    async with async_session() as session:
        from sqlalchemy import select
        from app.models import Event

        if admin.role.value == "super_admin":
            result = await session.execute(select(Event).order_by(Event.event_date))
        else:
            result = await session.execute(
                select(Event).where(Event.created_by_id == admin.id).order_by(Event.event_date)
            )
        events = list(result.scalars().all())

    if not events:
        await callback.message.answer("Hozircha eventlar yo'q.")
        await callback.answer()
        return

    for event in events:
        can_manage = crud.can_manage_event(admin, event)
        await callback.message.answer(
            f"{event.title} — {event.status.value} — {event.event_date.strftime('%d.%m.%Y %H:%M')}",
            reply_markup=event_manage_kb(event.id, can_manage),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_pending")
async def show_pending_events(callback: CallbackQuery) -> None:
    admin = await _require_admin(callback.from_user.id)
    if not admin or admin.role.value != "super_admin":
        await callback.answer("Ruxsat yo'q.", show_alert=True)
        return

    async with async_session() as session:
        from sqlalchemy import select
        from app.models import Event

        result = await session.execute(select(Event).where(Event.status == EventStatus.pending))
        pending = list(result.scalars().all())

    if not pending:
        await callback.message.answer("Tasdiqlash kutayotgan eventlar yo'q.")
        await callback.answer()
        return

    for event in pending:
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve:{event.id}")]]
        )
        await callback.message.answer(f"🕓 {event.title} — {event.event_date.strftime('%d.%m.%Y %H:%M')}", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("approve:"))
async def approve_event(callback: CallbackQuery) -> None:
    admin = await _require_admin(callback.from_user.id)
    if not admin or admin.role.value != "super_admin":
        await callback.answer("Ruxsat yo'q.", show_alert=True)
        return

    event_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        event = await crud.get_event(session, event_id)
        if event:
            await crud.approve_event(session, event)

    await callback.message.edit_text(f"✅ Tasdiqlandi: {event.title if event else event_id}")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_cancel:"))
async def admin_cancel_event(callback: CallbackQuery) -> None:
    admin = await _require_admin(callback.from_user.id)
    event_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        event = await crud.get_event(session, event_id)
        if not event or not admin or not crud.can_manage_event(admin, event):
            await callback.answer("Ruxsat yo'q.", show_alert=True)
            return
        await crud.cancel_event(session, event)

    await callback.answer("Event bekor qilindi.", show_alert=True)


@router.callback_query(F.data.startswith("export:"))
async def export_participants(callback: CallbackQuery) -> None:
    admin = await _require_admin(callback.from_user.id)
    if not admin:
        await callback.answer("Ruxsat yo'q.", show_alert=True)
        return

    event_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        participants = await crud.list_event_participants(session, event_id)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Full name", "Telegram ID", "University ID", "Interests"])
    for p in participants:
        writer.writerow([p.full_name, p.telegram_id, p.university_id, ", ".join(p.interests or [])])

    file = BufferedInputFile(buf.getvalue().encode("utf-8"), filename=f"event_{event_id}_participants.csv")
    await callback.message.answer_document(file)
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery) -> None:
    admin = await _require_admin(callback.from_user.id)
    if not admin or admin.role.value != "super_admin":
        await callback.answer("Ruxsat yo'q.", show_alert=True)
        return

    async with async_session() as session:
        stats = await crud.get_basic_stats(session)

    await callback.message.answer(
        f"📊 Statistika\n\n"
        f"Jami a'zolar: {stats['members']}\n"
        f"Faol registratsiyalar: {stats['active_registrations']}\n"
        f"Jami eventlar: {stats['events_total']}"
    )
    await callback.answer()

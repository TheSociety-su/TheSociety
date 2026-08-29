from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app import crud
from app.crud import RegistrationError
from app.database import async_session
from app.models import RegistrationStatus
from bot.keyboards import event_detail_kb, events_list_kb

router = Router(name="events")


async def _require_user(telegram_id: int):
    async with async_session() as session:
        return await crud.get_user_by_telegram_id(session, telegram_id)


@router.message(Command("events"))
async def cmd_events(message: Message) -> None:
    user = await _require_user(message.from_user.id)
    if not user:
        await message.answer("Avval /start bosib ro'yxatdan o'ting.")
        return

    async with async_session() as session:
        events = await crud.list_active_events(session)

    if not events:
        await message.answer("Hozircha faol eventlar yo'q. Keyinroq qayta tekshiring.")
        return

    await message.answer("📅 Faol eventlar:", reply_markup=events_list_kb(events))


@router.callback_query(F.data.startswith("event:"))
async def show_event_detail(callback: CallbackQuery) -> None:
    event_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        event = await crud.get_event(session, event_id)
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)

        already_registered = False
        if user:
            regs = await crud.list_user_registrations(session, user)
            already_registered = any(r.event_id == event_id for r in regs)

    if not event:
        await callback.answer("Event topilmadi.", show_alert=True)
        return

    text = (
        f"<b>{event.title}</b>\n\n"
        f"{event.description or ''}\n\n"
        f"📅 {event.event_date.strftime('%d.%m.%Y %H:%M')}\n"
        f"📍 {event.location or '-'}\n"
        f"🎤 {event.speaker or '-'}\n"
        f"🏷 {event.format}\n"
        f"👥 Limit: {event.participant_limit}\n"
        f"Status: {event.status.value}"
    )
    await callback.message.answer(text, reply_markup=event_detail_kb(event, already_registered), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("register:"))
async def register_event(callback: CallbackQuery) -> None:
    event_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Avval /start bosib ro'yxatdan o'ting.", show_alert=True)
            return
        try:
            await crud.register_for_event(session, user, event_id)
        except RegistrationError as e:
            await callback.answer(str(e), show_alert=True)
            return

    await callback.answer("Ro'yxatdan o'tdingiz! ✅ Tasdiqlash yuborildi.", show_alert=True)


@router.callback_query(F.data.startswith("cancel_reg:"))
async def cancel_registration(callback: CallbackQuery) -> None:
    event_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        user = await crud.get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Avval /start bosib ro'yxatdan o'ting.", show_alert=True)
            return
        try:
            await crud.cancel_registration(session, user, event_id)
        except RegistrationError as e:
            await callback.answer(str(e), show_alert=True)
            return

    await callback.answer("Registratsiya bekor qilindi.", show_alert=True)


@router.message(Command("my"))
async def cmd_my_registrations(message: Message) -> None:
    user = await _require_user(message.from_user.id)
    if not user:
        await message.answer("Avval /start bosib ro'yxatdan o'ting.")
        return

    async with async_session() as session:
        regs = await crud.list_user_registrations(session, user)
        events = [await crud.get_event(session, r.event_id) for r in regs]

    active_events = [e for e in events if e and e.status != RegistrationStatus.cancelled]
    if not active_events:
        await message.answer("Sizda faol registratsiyalar yo'q.")
        return

    await message.answer("🗒 Mening registratsiyalarim:", reply_markup=events_list_kb(active_events))

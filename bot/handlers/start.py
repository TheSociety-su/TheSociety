from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import crud
from app.database import async_session
from bot.keyboards import interests_kb, main_menu_kb, universities_kb
from bot.states import Onboarding

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    async with async_session() as session:
        user = await crud.get_user_by_telegram_id(session, message.from_user.id)

    if user:
        await message.answer(
            f"Xush kelibsiz qaytganingizdan xursandmiz, {user.full_name}! 👋",
            reply_markup=main_menu_kb(),
        )
        return

    await state.set_state(Onboarding.waiting_name)
    await message.answer(
        "THE SOCIETY botiga xush kelibsiz! 🎓\n"
        "Students from different universities, one community.\n\n"
        "Avval to'liq ismingizni kiriting:"
    )


@router.message(Onboarding.waiting_name)
async def onboarding_name(message: Message, state: FSMContext) -> None:
    full_name = (message.text or "").strip()
    if len(full_name) < 2:
        await message.answer("Ism juda qisqa, qaytadan kiriting:")
        return

    await state.update_data(full_name=full_name)
    await state.set_state(Onboarding.waiting_university)

    async with async_session() as session:
        universities = await crud.list_universities(session)

    await message.answer("Universitetingizni tanlang:", reply_markup=universities_kb(universities))


@router.callback_query(Onboarding.waiting_university, F.data.startswith("uni:"))
async def onboarding_university(callback: CallbackQuery, state: FSMContext) -> None:
    university_id = int(callback.data.split(":")[1])
    await state.update_data(university_id=university_id, interests=[])
    await state.set_state(Onboarding.waiting_interests)

    await callback.message.edit_text(
        "Qiziqishlaringizni tanlang (bir nechtasini belgilash mumkin), so'ng 'Tayyor'ni bosing:",
        reply_markup=interests_kb([]),
    )
    await callback.answer()


@router.callback_query(Onboarding.waiting_interests, F.data.startswith("int:"))
async def onboarding_toggle_interest(callback: CallbackQuery, state: FSMContext) -> None:
    category = callback.data.split(":", 1)[1]
    data = await state.get_data()
    interests: list[str] = data.get("interests", [])

    if category in interests:
        interests.remove(category)
    else:
        interests.append(category)

    await state.update_data(interests=interests)
    await callback.message.edit_reply_markup(reply_markup=interests_kb(interests))
    await callback.answer()


@router.callback_query(Onboarding.waiting_interests, F.data == "int_done")
async def onboarding_finish(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()

    async with async_session() as session:
        user = await crud.create_user(
            session,
            telegram_id=callback.from_user.id,
            full_name=data["full_name"],
            university_id=data["university_id"],
            interests=data.get("interests", []),
        )

    await state.clear()
    await callback.message.edit_text(
        f"Tabriklaymiz, {user.full_name}! Ro'yxatdan muvaffaqiyatli o'tdingiz. ✅"
    )
    await callback.message.answer("Quyidagi tugmalardan foydalaning:", reply_markup=main_menu_kb())
    await callback.answer()

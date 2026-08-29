from aiogram.fsm.state import State, StatesGroup


class Onboarding(StatesGroup):
    waiting_name = State()
    waiting_university = State()
    waiting_interests = State()


class CreateEvent(StatesGroup):
    title = State()
    description = State()
    date = State()
    location = State()
    speaker = State()
    format = State()
    limit = State()

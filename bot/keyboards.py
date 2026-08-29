from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.config import EVENT_FORMATS, INTEREST_CATEGORIES
from app.models import Event, University

BTN_EVENTS = "📅 Eventlar"
BTN_MY = "🗒 Mening registratsiyalarim"


def main_menu_kb() -> ReplyKeyboardMarkup:
    """Persistent bottom keyboard shown after onboarding — replaces typing /events and /my."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_EVENTS), KeyboardButton(text=BTN_MY)]],
        resize_keyboard=True,
    )


def universities_kb(universities: list[University]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=u.name, callback_data=f"uni:{u.id}")] for u in universities
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def interests_kb(selected: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for cat in INTEREST_CATEGORIES:
        mark = "✅ " if cat in selected else ""
        rows.append([InlineKeyboardButton(text=f"{mark}{cat}", callback_data=f"int:{cat}")])
    rows.append([InlineKeyboardButton(text="Tayyor ➡️", callback_data="int_done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def event_formats_kb() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f, callback_data=f"fmt:{f}")] for f in EVENT_FORMATS]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def events_list_kb(events: list[Event]) -> InlineKeyboardMarkup:
    rows = []
    for e in events:
        label = e.title if e.status.value != "full" else f"{e.title} (joy yo'q)"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"event:{e.id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def event_detail_kb(event: Event, already_registered: bool) -> InlineKeyboardMarkup:
    if already_registered:
        btn = InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel_reg:{event.id}")
    elif event.status.value == "full":
        btn = InlineKeyboardButton(text="Joylar tugagan", callback_data="noop")
    else:
        btn = InlineKeyboardButton(text="✅ Ro'yxatdan o'tish", callback_data=f"register:{event.id}")
    return InlineKeyboardMarkup(inline_keyboard=[[btn]])


def admin_menu_kb(is_super_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="➕ Event yaratish", callback_data="admin_create_event")],
        [InlineKeyboardButton(text="📋 Mening eventlarim", callback_data="admin_my_events")],
    ]
    if is_super_admin:
        rows.append([InlineKeyboardButton(text="🕓 Tasdiqlash kutilmoqda", callback_data="admin_pending")])
        rows.append([InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def event_manage_kb(event_id: int, can_manage: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="👥 Ishtirokchilar (CSV)", callback_data=f"export:{event_id}")]]
    if can_manage:
        rows.append([InlineKeyboardButton(text="🚫 Eventni bekor qilish", callback_data=f"admin_cancel:{event_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

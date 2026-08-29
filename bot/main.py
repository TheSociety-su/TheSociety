import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.crud import ensure_super_admins, seed_universities
from app.database import async_session, init_db
from bot.handlers import admin, events, start

logging.basicConfig(level=logging.INFO)


async def on_startup() -> None:
    await init_db()
    async with async_session() as session:
        await seed_universities(session)
        await ensure_super_admins(session)


async def main() -> None:
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start.router)
    dp.include_router(events.router)
    dp.include_router(admin.router)

    await on_startup()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

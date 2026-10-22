import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.database.db import Database
from app.database.seed import seed_initial_data
from app.services.notification import NotificationService
from app.handlers import common, client, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("booking_bot")


async def main():
    logger.info("Initializing Telegram Booking Bot...")

    # Initialize Database
    db = Database(settings.db_path)
    await db.init_tables()
    await seed_initial_data(db)

    # Initialize Bot & Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Notification service
    notification_service = NotificationService(bot)

    # Dependency Injection into handlers
    dp["db"] = db
    dp["notification_service"] = notification_service

    # Register Routers
    dp.include_router(common.router)
    dp.include_router(client.router)
    dp.include_router(admin.router)

    logger.info(f"Bot started successfully! Salon: {settings.SALON_NAME}")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")

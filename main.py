import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db, init_default_settings, init_default_faq, init_forbidden_topics
from handlers import get_router
from logging_config import setup_logging
from utils.auto_hide import auto_hide_inactive_users

logger = setup_logging()

async def main():
    logger.info("Starting bot initialization...")
    
    await init_db()
    await init_default_settings()
    await init_default_faq()
    await init_forbidden_topics()
    
    logger.info("Database initialized")
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    router = get_router()
    dp.include_router(router)
    
    asyncio.create_task(auto_hide_inactive_users())
    logger.info("Auto-hide background task started")
    
    logger.info("Bot configured, starting polling...")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
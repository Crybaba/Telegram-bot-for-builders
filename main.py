import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault
from config import BOT_TOKEN
from bot.worker_handlers import router as worker_router
from bot.foreman_handlers import router as foreman_router
from database.connection import engine
from database.models import Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global bot instance
bot = None

async def main():
    """Main function to start the bot"""
    global bot
    
    # Create tables if they don't exist
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        return

    # Initialize bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Set bot commands menu
    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="Запустить бота / Главное меню"),
            BotCommand(command="about", description="Информация о боте и создателях"),
        ],
        scope=BotCommandScopeDefault()
    )

    # Include routers
    dp.include_router(worker_router)
    dp.include_router(foreman_router)

    # Start polling
    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main()) 
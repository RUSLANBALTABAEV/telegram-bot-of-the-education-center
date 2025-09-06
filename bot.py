import asyncio
from loader import bot, dp 
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from config.bot_config import API_TOKEN
from handlers.registration import registration_router
from handlers.auth import auth_router
from handlers.start import start_router
from handlers.courses import courses_router
from handlers.admin import admin_router
from handlers.my_courses import my_courses_router
from handlers.certificates import certificates_router
from notifier import setup_scheduler
from db.models import create_db, seed_courses
from db.session import engine

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

async def main():
    await create_db(engine)
    await seed_courses(engine)

    dp.include_router(start_router)
    dp.include_router(registration_router)
    dp.include_router(auth_router)
    dp.include_router(courses_router)
    dp.include_router(my_courses_router)
    dp.include_router(admin_router)
    dp.include_router(certificates_router) 

    # запускаем уведомления
    setup_scheduler() 

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

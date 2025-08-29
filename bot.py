import asyncio
from aiogram import Bot, Dispatcher
from config.bot_config import API_TOKEN
from handlers.registration import registration_router
from handlers.auth import auth_router
from handlers.start import start_router 
from handlers.courses import courses_router
from db.models import create_db, seed_courses
from db.session import engine

bot = Bot(API_TOKEN)
dp = Dispatcher()


async def main():
    # Создаём таблицы (если их ещё нет)
    await create_db(engine)
    # Заполняем базовые курсы (если ещё нет)
    await seed_courses(engine)

    # Подключаем роутеры
    dp.include_router(start_router)
    dp.include_router(registration_router)
    dp.include_router(auth_router)
    dp.include_router(courses_router)

    # Убираем старые апдейты и запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from aiogram import Bot, Dispatcher
from config.bot_config import API_TOKEN
from handlers.registration import registration_router
from handlers.auth import auth_router
from db.models import create_db
from db.session import engine

bot = Bot(API_TOKEN)
dp = Dispatcher()


async def main():
    # Создаём таблицы (если их ещё нет)
    await create_db(engine)
    # Подключаем роутеры
    dp.include_router(registration_router)
    dp.include_router(auth_router)

    # Убираем старые апдейты и запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

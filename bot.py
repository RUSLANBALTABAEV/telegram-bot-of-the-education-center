# ============ bot.py ============
"""
Главный файл запуска Telegram бота.
Инициализирует базу данных, регистрирует роутеры и запускает polling.
"""
import asyncio

from loader import bot, dp
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


async def main() -> None:
    """
    Главная функция для запуска бота.

    Выполняет:
    - Создание таблиц в БД
    - Добавление дефолтных курсов
    - Регистрацию роутеров
    - Запуск планировщика уведомлений
    - Запуск polling
    """
    # Создаём таблицы
    await create_db(engine)

    # Добавляем дефолтные курсы
    await seed_courses()

    # Регистрируем роутеры
    dp.include_router(start_router)
    dp.include_router(registration_router)
    dp.include_router(auth_router)
    dp.include_router(courses_router)
    dp.include_router(my_courses_router)
    dp.include_router(admin_router)
    dp.include_router(certificates_router)

    # Запускаем планировщик
    setup_scheduler()

    # Очищаем апдейты и стартуем бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

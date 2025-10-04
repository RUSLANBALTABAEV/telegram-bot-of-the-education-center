# ============ notifier.py ============
"""
Модуль планировщика уведомлений о начале и окончании курсов.
Использует APScheduler для отправки уведомлений пользователям.
"""
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from db.session import async_session
from db.models import Enrollment, User, Course
from loader import bot
from i18n.locales import get_text

# Создаём планировщик с часовым поясом Ташкента
scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")


async def notify_start_course() -> None:
    """
    Уведомить пользователей о начале курсов сегодня.

    Проверяет все записи, где start_date равна сегодняшней дате,
    и отправляет уведомления соответствующим пользователям.
    """
    today = datetime.now(scheduler.timezone).date()

    async with async_session() as session:
        result = await session.execute(
            select(Enrollment, Course, User)
            .join(Course, Enrollment.course_id == Course.id)
            .join(User, Enrollment.user_id == User.id)
            .where(Enrollment.start_date == today)
        )
        rows = result.all()

        for enr, course, user in rows:
            if user and user.user_id:
                try:
                    lang = user.language or "ru"
                    message_text = get_text(
                        "course_starts_today",
                        lang,
                        title=course.title
                    )
                    await bot.send_message(
                        user.user_id,
                        message_text,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Ошибка при уведомлении о начале курса: {e}")


async def notify_end_course() -> None:
    """
    Уведомить пользователей об окончании курсов сегодня.

    Проверяет все записи, где end_date равна сегодняшней дате,
    и отправляет уведомления соответствующим пользователям.
    """
    today = datetime.now(scheduler.timezone).date()

    async with async_session() as session:
        result = await session.execute(
            select(Enrollment, Course, User)
            .join(Course, Enrollment.course_id == Course.id)
            .join(User, Enrollment.user_id == User.id)
            .where(Enrollment.end_date == today)
        )
        rows = result.all()

        for enr, course, user in rows:
            if user and user.user_id:
                try:
                    lang = user.language or "ru"
                    message_text = get_text(
                        "course_ends_today",
                        lang,
                        title=course.title
                    )
                    await bot.send_message(
                        user.user_id,
                        message_text,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Ошибка при уведомлении о конце курса: {e}")


def setup_scheduler() -> None:
    """
    Настроить и запустить планировщик уведомлений.

    Добавляет задачи на уведомление о начале и окончании курсов.
    Уведомления отправляются каждый день в 9:00.
    """
    # Уведомления каждый день в 9:00
    scheduler.add_job(notify_start_course, "cron", hour=9, minute=0)
    scheduler.add_job(notify_end_course, "cron", hour=9, minute=0)
    scheduler.start()

from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from db.session import async_session
from db.models import Enrollment, User, Course
from loader import bot
from i18n.locales import get_text

scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

async def notify_start_course():
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
                    message_text = get_text("course_starts_today", lang, title=course.title)
                    await bot.send_message(
                        user.user_id,
                        message_text,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Ошибка при уведомлении о начале курса: {e}")

async def notify_end_course():
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
                    message_text = get_text("course_ends_today", lang, title=course.title)
                    await bot.send_message(
                        user.user_id,
                        message_text,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Ошибка при уведомлении о конце курса: {e}")

def setup_scheduler():
    # Тестовые интервалы - каждый день в 9:00
    scheduler.add_job(notify_start_course, "cron", hour=9, minute=0)
    scheduler.add_job(notify_end_course, "cron", hour=9, minute=0)
    scheduler.start()

# notifier.py
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from db.session import async_session
from db.models import Enrollment, User, Course
from loader import bot   # ✅ берём bot отсюда

scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")  # часовой пояс можно поменять

# уведомление о старте курса
async def notify_start_course():
    today = datetime.today().date()
    async with async_session() as session:
        result = await session.execute(
            select(Enrollment).where(Enrollment.start_date == today)
        )
        enrollments = result.scalars().all()

        for enr in enrollments:
            user = await session.get(User, enr.user_id)
            course = await session.get(Course, enr.course_id)
            if user and user.user_id:
                try:
                    await bot.send_message(
                        user.user_id,
                        f"🚀 Сегодня стартует курс: <b>{course.title}</b>!\nЖелаем удачи 🎉",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Ошибка при отправке уведомления: {e}")

# уведомление об окончании курса
async def notify_end_course():
    today = datetime.today().date()
    async with async_session() as session:
        result = await session.execute(
            select(Enrollment).where(Enrollment.end_date == today)
        )
        enrollments = result.scalars().all()

        for enr in enrollments:
            user = await session.get(User, enr.user_id)
            course = await session.get(Course, enr.course_id)
            if user and user.user_id:
                try:
                    await bot.send_message(
                        user.user_id,
                        f"📅 Сегодня завершился курс: <b>{course.title}</b>.\nСпасибо за обучение 🙌",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Ошибка при отправке уведомления: {e}")

# запуск планировщика
def setup_scheduler():
    scheduler.add_job(notify_start_course, "cron", hour=9, minute=0)  # каждый день в 09:00
    scheduler.add_job(notify_end_course, "cron", hour=9, minute=5)   # каждый день в 09:05
    scheduler.start()

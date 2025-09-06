from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from db.session import async_session
from db.models import Enrollment, User, Course
from loader import bot   # ✅ импортируем bot отсюда

# Планировщик с нужным часовым поясом
scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

# Уведомление о старте курсов
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
                    await bot.send_message(
                        user.user_id,
                        f"🚀 Сегодня стартует курс: <b>{course.title}</b>!\nЖелаем удачи 🎉",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Ошибка при уведомлении о начале курса: {e}")

# Уведомление об окончании курсов
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
                    await bot.send_message(
                        user.user_id,
                        f"📅 Сегодня завершился курс: <b>{course.title}</b>.\nСпасибо за обучение 🙌",
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Ошибка при уведомлении о конце курса: {e}")

# Запуск планировщика
def setup_scheduler():
    # 🔹 Для теста — каждые 1–2 минуты
    scheduler.add_job(notify_start_course, "interval", minutes=1)
    scheduler.add_job(notify_end_course, "interval", minutes=2)

    # 🔹 Для продакшена — раскомментируй и убери interval
    # scheduler.add_job(notify_start_course, "cron", hour=9, minute=0)
    # scheduler.add_job(notify_end_course, "cron", hour=9, minute=5)

    scheduler.start()

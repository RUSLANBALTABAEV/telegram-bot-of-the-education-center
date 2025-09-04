from aiogram import Router, F, types
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import User, Course, Certificate, Enrollment, async_session
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config.bot_config import ADMIN_ID

my_courses_router = Router()

# --- Мои курсы ---
@my_courses_router.message(Command("mycourses"))
@my_courses_router.message(F.text == "Мои курсы")
async def show_my_courses(message: types.Message):
    async with async_session() as session:
        result = await session.execute(
            select(Enrollment).options(selectinload(Enrollment.course)).where(
                Enrollment.user_id == message.from_user.id
            )
        )
        enrollments = result.scalars().all()

    if not enrollments:
        await message.answer("📭 У вас пока нет курсов.")
        return

    for enr in enrollments:
        course = enr.course
        status = "✅ Завершён" if enr.is_completed else f"📅 До {enr.end_date or 'не указано'}"
        text = (
            f"📘 <b>{course.title}</b>\n\n"
            f"{course.description or 'Без описания'}\n\n"
            f"💰 Цена: {course.price} руб.\n\n"
            f"Статус: {status}"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🚪 Отписаться", callback_data=f"unenroll:{course.id}")]
            ]
        )

        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

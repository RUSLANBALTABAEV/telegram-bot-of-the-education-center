from aiogram import Router, F, types
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import User, Course, Certificate, Enrollment
from db.session import async_session
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

my_courses_router = Router()

# --- Мои курсы ---
@my_courses_router.message(Command("mycourses"))
@my_courses_router.message(F.text == "Мои курсы")
async def show_my_courses(message: types.Message):
    async with async_session() as session:
        # находим пользователя по Telegram ID
        result_user = await session.execute(
            select(User).where(User.user_id == message.from_user.id)
        )
        user = result_user.scalar_one_or_none()

        if not user:
            await message.answer("⚠️ Вы не зарегистрированы. Используйте /register.")
            return

        result = await session.execute(
            select(Enrollment)
            .options(selectinload(Enrollment.course))
            .where(Enrollment.user_id == user.id)
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

from aiogram import Router, F, types
from aiogram.filters import Command
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import User, Course, Certificate, async_session
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

my_courses_router = Router()

# --- Мои курсы ---
@my_courses_router.message(Command("mycourses"))
@my_courses_router.message(F.text == "Мои курсы")
async def show_my_courses(message: types.Message):
    async with async_session() as session:
        result = await session.execute(
            select(User).options(selectinload(User.courses)).where(User.user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

    if not user or not user.courses:
        await message.answer("📭 У вас пока нет курсов.")
        return

    for course in user.courses:
        text = (
            f"📘 <b>{course.title}</b>\n\n"
            f"{course.description or 'Без описания'}\n\n"
            f"💰 Цена: {course.price} руб."
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🚪 Отписаться", callback_data=f"unenroll:{course.id}")]
            ]
        )

        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# --- Сертификаты ---
@my_courses_router.message(Command("certificates"))
@my_courses_router.message(F.text == "Мои сертификаты")
async def show_certificates(message: types.Message):
    async with async_session() as session:
        result = await session.execute(
            select(User).options(selectinload(User.certificates)).where(User.user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

    if not user or not user.certificates:
        await message.answer("📭 У вас пока нет сертификатов.")
        return

    for cert in user.certificates:
        await message.answer_document(cert.file_id, caption=f"🏅 {cert.title}")

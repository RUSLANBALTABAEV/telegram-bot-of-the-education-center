from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import User, Course, async_session

courses_router = Router()

@courses_router.message(Command("courses"))
@courses_router.message(F.text == "Курсы")
async def show_courses(message):
    async with async_session() as session:
        result = await session.execute(select(Course))
        courses = result.scalars().all()

    if not courses:
        await message.answer("📚 Курсов пока нет.")
        return

    text = "📚 Доступные курсы:\nВыберите курс:"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=course.title, callback_data=f"course:{course.id}")]
            for course in courses
        ]
    )
    await message.answer(text, reply_markup=keyboard)

@courses_router.callback_query(F.data.startswith("course:"))
async def show_course_info(callback: CallbackQuery):
    course_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        course = await session.get(Course, course_id)

    if not course:
        await callback.answer("⚠️ Курс не найден.", show_alert=True)
        return

    text = (
        f"📘 <b>{course.title}</b>\n\n"
        f"{course.description}\n\n"
        f"💰 Цена: {course.price} руб."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Записаться", callback_data=f"enroll:{course.id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_courses")]
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

@courses_router.callback_query(F.data.startswith("enroll:"))
async def enroll_course(callback: CallbackQuery):
    course_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        result = await session.execute(
            select(User).options(selectinload(User.courses)).where(User.user_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await callback.answer("⚠️ Сначала зарегистрируйтесь (/register) или войдите (/login).", show_alert=True)
            return

        course = await session.get(Course, course_id)
        if not course:
            await callback.answer("⚠️ Курс не найден.", show_alert=True)
            return

        if course in user.courses:
            await callback.answer("⚠️ Вы уже записаны на этот курс.", show_alert=True)
        else:
            user.courses.append(course)
            session.add(user)
            await session.commit()
            await callback.message.edit_text(f"✅ Вы успешно записались на курс «{course.title}»!")

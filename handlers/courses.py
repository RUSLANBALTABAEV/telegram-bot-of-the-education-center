from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import User, Course, async_session

courses_router = Router()

# --- Генерация списка курсов ---
async def build_courses_message():
    async with async_session() as session:
        result = await session.execute(select(Course))
        courses = result.scalars().all()

    if not courses:
        return "📚 Курсов пока нет.", None

    text = "📚 Доступные курсы:\nВыберите курс:"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=course.title, callback_data=f"course:{course.id}")]
            for course in courses
        ]
    )
    return text, keyboard

# --- /courses ---
@courses_router.message(Command("courses"))
@courses_router.message(F.text == "Курсы")
async def show_courses(message):
    text, keyboard = await build_courses_message()
    if not keyboard:
        await message.answer(text)
    else:
        await message.answer(text, reply_markup=keyboard)

# --- Информация о курсе ---
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

# --- Запись на курс ---
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

# --- Назад к списку ---
@courses_router.callback_query(F.data == "back_to_courses")
async def back_to_courses(callback: CallbackQuery):
    text, keyboard = await build_courses_message()
    if not keyboard:
        await callback.message.edit_text(text)
    else:
        await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

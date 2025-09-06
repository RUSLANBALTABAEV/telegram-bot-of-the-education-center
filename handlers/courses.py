from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import User, Course, Enrollment
from db.session import async_session
from datetime import date

courses_router = Router()


# Построение списка курсов
async def build_courses_message():
    async with async_session() as session:
        result = await session.execute(select(Course))
        courses = result.scalars().all()

    if not courses:
        return "📚 Курсов пока нет.", None

    text = "📚 Доступные курсы:\n\nВыберите курс:"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=course.title, callback_data=f"course:{course.id}")]
            for course in courses
        ]
    )
    return text, keyboard


# Список курсов
@courses_router.message(Command("courses"))
@courses_router.message(F.text == "Курсы")
async def show_courses(message: Message):
    text, keyboard = await build_courses_message()
    if not keyboard:
        await message.answer(text)
    else:
        await message.answer(text, reply_markup=keyboard)


# Информация о курсе
@courses_router.callback_query(F.data.startswith("course:"))
async def show_course_info(callback: CallbackQuery):
    course_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        course = await session.get(Course, course_id)
        if not course:
            await callback.answer("⚠️ Курс не найден.", show_alert=True)
            return

        # Проверка пользователя
        result_user = await session.execute(
            select(User).where(User.user_id == callback.from_user.id)
        )
        user = result_user.scalar_one_or_none()

        enrollment = None
        if user:
            result = await session.execute(
                select(Enrollment)
                .options(selectinload(Enrollment.course))
                .where(Enrollment.user_id == user.id, Enrollment.course_id == course_id)
            )
            enrollment = result.scalar_one_or_none()

    # Формируем текст курса
    text = (
        f"📘 <b>{course.title}</b>\n\n"
        f"{course.description}\n\n"
        f"💰 Цена: {course.price} руб.\n"
        f"📅 Даты: {course.start_date or 'не указана'} — {course.end_date or 'не указана'}"
    )

    # Кнопки
    if enrollment:
        status = "✅ Завершён" if enrollment.is_completed else f"📅 До {enrollment.end_date or 'не указано'}"
        text += f"\n\nСтатус: {status}"
        action_button = InlineKeyboardButton(text="🚪 Отписаться", callback_data=f"unenroll:{course.id}")
    else:
        action_button = InlineKeyboardButton(text="✅ Записаться", callback_data=f"enroll:{course.id}")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [action_button],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_courses")]
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# Запись на курс
@courses_router.callback_query(F.data.startswith("enroll:"))
async def enroll_course(callback: CallbackQuery):
    course_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        # Проверка пользователя
        result = await session.execute(select(User).where(User.user_id == callback.from_user.id))
        user = result.scalar_one_or_none()
        if not user:
            await callback.answer("⚠️ Сначала зарегистрируйтесь (/register).", show_alert=True)
            return

        # Проверка курса
        course = await session.get(Course, course_id)
        if not course:
            await callback.answer("⚠️ Курс не найден.", show_alert=True)
            return

        # Проверка записи
        existing = await session.execute(
            select(Enrollment).where(Enrollment.user_id == user.id, Enrollment.course_id == course_id)
        )
        if existing.scalar_one_or_none():
            await callback.answer("⚠️ Вы уже записаны.", show_alert=True)
            return

        # Создаём запись с датами из курса
        enrollment = Enrollment(
            user_id=user.id,
            course_id=course.id,
            start_date=course.start_date or date.today(),
            end_date=course.end_date,
            is_completed=False
        )
        session.add(enrollment)
        await session.commit()

    await callback.message.edit_text(f"✅ Вы записались на курс «{course.title}»!")


# Отписка
@courses_router.callback_query(F.data.startswith("unenroll:"))
async def unenroll_course(callback: CallbackQuery):
    course_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == callback.from_user.id))
        user = result.scalar_one_or_none()
        if not user:
            await callback.answer("⚠️ Сначала зарегистрируйтесь (/register).", show_alert=True)
            return

        enrollment_q = await session.execute(
            select(Enrollment).where(Enrollment.user_id == user.id, Enrollment.course_id == course_id)
        )
        enrollment = enrollment_q.scalar_one_or_none()
        if not enrollment:
            await callback.answer("⚠️ Вы не записаны на этот курс.", show_alert=True)
            return

        await session.delete(enrollment)
        await session.commit()

    await callback.message.edit_text("🚪 Вы отписались от курса.")


# Назад
@courses_router.callback_query(F.data == "back_to_courses")
async def back_to_courses(callback: CallbackQuery):
    text, keyboard = await build_courses_message()
    if not keyboard:
        await callback.message.edit_text(text)
    else:
        await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

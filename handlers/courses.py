from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.models import User, Course
from db.session import async_session
from fsm.courses import CourseFSM

courses_router = Router()


# --- Список курсов ---
@courses_router.message(Command("courses"))
@courses_router.message(F.text == "Курсы")
async def show_courses(message: types.Message, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(select(Course))
        courses = result.scalars().all()

    if not courses:
        await message.answer("📚 Курсов пока нет.")
        return

    text = "📚 Доступные курсы:\n\n"
    for course in courses:
        text += f"▫️ {course.title} — {course.description or 'Без описания'}\n💲 Стоимость: {course.price} руб.\n\n"

    text += "\nЧтобы записаться, напишите название курса."
    await message.answer(text)
    await state.set_state(CourseFSM.choosing_course)


# --- Запись на курс ---
@courses_router.message(CourseFSM.choosing_course, F.text)
async def enroll_course(message: types.Message, state: FSMContext):
    course_name = message.text.strip()

    async with async_session() as session:
        # Проверяем курс
        result = await session.execute(select(Course).where(Course.title == course_name))
        course = result.scalar_one_or_none()

        if not course:
            await message.answer("⚠️ Такого курса нет. Попробуйте снова.")
            return

        # Загружаем пользователя вместе с курсами (selectinload!)
        result = await session.execute(
            select(User).options(selectinload(User.courses)).where(User.user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("⚠️ Сначала пройдите регистрацию (/register).")
            await state.clear()
            return

        if course in user.courses:
            await message.answer("⚠️ Вы уже записаны на этот курс.")
        else:
            user.courses.append(course)
            session.add(user)
            await session.commit()
            await message.answer(f"✅ Вы успешно записались на курс «{course.title}»!")

    await state.clear()


# --- Отписка ---
@courses_router.message(Command("unsubscribe"))
@courses_router.message(F.text == "Отписаться")
async def unsubscribe_course(message: types.Message):
    async with async_session() as session:
        # Загружаем пользователя вместе с курсами
        result = await session.execute(
            select(User).options(selectinload(User.courses)).where(User.user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user or not user.courses:
            await message.answer("⚠️ Вы ещё не записаны ни на один курс.")
            return

        # Отписываем от всех курсов
        user.courses.clear()
        session.add(user)
        await session.commit()
        await message.answer("🚪 Вы отписались от всех курсов.")

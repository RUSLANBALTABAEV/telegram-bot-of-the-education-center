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
        result = await session.execute(select(Course).where(Course.title == course_name))
        course = result.scalar_one_or_none()

        if not course:
            await message.answer("⚠️ Такого курса нет. Попробуйте снова.")
            return

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


# --- Мои курсы ---
@courses_router.message(Command("mycourses"))
@courses_router.message(F.text == "Мои курсы")
async def my_courses(message: types.Message, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(
            select(User).options(selectinload(User.courses)).where(User.user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

    if not user or not user.courses:
        await message.answer("⚠️ У вас пока нет записей на курсы.")
        return

    text = "📚 Вы записаны на курсы:\n\n"
    for course in user.courses:
        text += f"▫️ {course.title}\n"

    text += "\nЧтобы отписаться от курса, напишите его название."
    await message.answer(text)
    await state.set_state(CourseFSM.unsubscribe_course)


# --- Отписка от одного курса ---
@courses_router.message(CourseFSM.unsubscribe_course, F.text)
async def unsubscribe_one(message: types.Message, state: FSMContext):
    course_name = message.text.strip()

    async with async_session() as session:
        result = await session.execute(
            select(User).options(selectinload(User.courses)).where(User.user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("⚠️ Сначала зарегистрируйтесь (/register).")
            await state.clear()
            return

        course_to_remove = next((c for c in user.courses if c.title == course_name), None)

        if not course_to_remove:
            await message.answer("⚠️ Вы не записаны на этот курс.")
        else:
            user.courses.remove(course_to_remove)
            session.add(user)
            await session.commit()
            await message.answer(f"🚪 Вы отписались от курса «{course_to_remove.title}».")

    await state.clear()

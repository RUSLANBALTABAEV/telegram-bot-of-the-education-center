from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import User, Course, async_session
from fsm.courses import CourseFSM

courses_router = Router()

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
        text += f"▫️ {course.title} — {course.description}\n💲 {course.price} руб.\n\n"

    text += "Напишите название курса для записи."
    await message.answer(text)
    await state.set_state(CourseFSM.choosing_course)


@courses_router.message(CourseFSM.choosing_course, F.text)
async def enroll_course(message: types.Message, state: FSMContext):
    course_name = message.text.strip()
    async with async_session() as session:
        result = await session.execute(select(Course).where(Course.title == course_name))
        course = result.scalar_one_or_none()

        if not course:
            await message.answer("⚠️ Такого курса нет.")
            return

        result = await session.execute(
            select(User).options(selectinload(User.courses)).where(User.user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("⚠️ Сначала зарегистрируйтесь (/register).")
        elif course in user.courses:
            await message.answer("⚠️ Вы уже записаны.")
        else:
            user.courses.append(course)
            session.add(user)
            await session.commit()
            await message.answer(f"✅ Запись на курс «{course.title}» выполнена!")

    await state.clear()


@courses_router.message(Command("mycourses"))
@courses_router.message(F.text == "Мои курсы")
async def my_courses(message: types.Message, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(
            select(User).options(selectinload(User.courses)).where(User.user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

    if not user or not user.courses:
        await message.answer("⚠️ У вас нет курсов.")
        return

    text = "📚 Ваши курсы:\n\n"
    for course in user.courses:
        text += f"▫️ {course.title}\n"

    text += "Напишите название курса для отписки."
    await message.answer(text)
    await state.set_state(CourseFSM.unsubscribe_course)


@courses_router.message(CourseFSM.unsubscribe_course, F.text)
async def unsubscribe_course(message: types.Message, state: FSMContext):
    course_name = message.text.strip()
    async with async_session() as session:
        result = await session.execute(
            select(User).options(selectinload(User.courses)).where(User.user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("⚠️ Сначала зарегистрируйтесь.")
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

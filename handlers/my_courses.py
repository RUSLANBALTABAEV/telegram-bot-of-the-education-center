from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import User, Course, async_session
from config.bot_config import ADMIN_ID

my_courses_router = Router()

# --- FSM для редактирования курса ---
class CourseEditFSM(StatesGroup):
    waiting_for_price = State()
    waiting_for_title = State()
    waiting_for_description = State()


# --- Список моих / всех курсов ---
@my_courses_router.message(Command("mycourses"))
@my_courses_router.message(F.text == "Мои курсы")
async def show_my_courses(message: types.Message):
    async with async_session() as session:
        if message.from_user.id == ADMIN_ID:
            result = await session.execute(select(Course))
            courses = result.scalars().all()
        else:
            result = await session.execute(
                select(User).options(selectinload(User.courses)).where(User.user_id == message.from_user.id)
            )
            user = result.scalar_one_or_none()
            if not user:
                await message.answer("⚠️ Сначала зарегистрируйтесь (/register) или войдите (/login).")
                return
            courses = user.courses

    if not courses:
        await message.answer("📭 Курсов пока нет.")
        return

    text = "📘 Ваши курсы:" if message.from_user.id != ADMIN_ID else "📘 Все доступные курсы:"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=course.title, callback_data=f"mycourse:{course.id}")]
            for course in courses
        ]
    )
    await message.answer(text, reply_markup=keyboard)


# --- Информация о курсе ---
@my_courses_router.callback_query(F.data.startswith("mycourse:"))
async def my_course_info(callback: CallbackQuery):
    course_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        result = await session.execute(
            select(User).options(selectinload(User.courses)).where(User.user_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        course = await session.get(Course, course_id)

    if not course:
        await callback.answer("⚠️ Курс не найден.", show_alert=True)
        return

    text = (
        f"📘 <b>{course.title}</b>\n\n"
        f"{course.description}\n\n"
        f"💰 Цена: {course.price} руб."
    )

    keyboard = [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_mycourses")]]

    if callback.from_user.id == ADMIN_ID:
        keyboard.insert(
            0,
            [
                InlineKeyboardButton(text="✏️ Название", callback_data=f"edit_title:{course.id}"),
                InlineKeyboardButton(text="📝 Описание", callback_data=f"edit_desc:{course.id}"),
            ]
        )
        keyboard.insert(
            1,
            [
                InlineKeyboardButton(text="💰 Цена", callback_data=f"edit_price:{course.id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delcourse:{course.id}"),
            ]
        )
    else:
        # для обычного пользователя — возможность отписки
        if user and course in user.courses:
            keyboard.insert(0, [InlineKeyboardButton(text="🚪 Отписаться", callback_data=f"unenroll_my:{course.id}")])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )


# --- Отписка из моих курсов ---
@my_courses_router.callback_query(F.data.startswith("unenroll_my:"))
async def unenroll_my_course(callback: CallbackQuery):
    course_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        result = await session.execute(
            select(User).options(selectinload(User.courses)).where(User.user_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        course = await session.get(Course, course_id)

        if not user or not course:
            await callback.answer("⚠️ Ошибка. Попробуйте позже.", show_alert=True)
            return

        if course not in user.courses:
            await callback.answer("⚠️ Вы не записаны на этот курс.", show_alert=True)
        else:
            user.courses.remove(course)
            session.add(user)
            await session.commit()
            await callback.message.edit_text(f"🚪 Вы отписались от курса «{course.title}».")

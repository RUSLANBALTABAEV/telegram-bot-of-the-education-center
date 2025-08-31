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
            # админ видит все курсы
            result = await session.execute(select(Course))
            courses = result.scalars().all()
        else:
            # обычный пользователь видит только свои
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

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )


# --- Возврат к списку ---
@my_courses_router.callback_query(F.data == "back_to_mycourses")
async def back_to_my_courses(callback: CallbackQuery):
    async with async_session() as session:
        if callback.from_user.id == ADMIN_ID:
            result = await session.execute(select(Course))
            courses = result.scalars().all()
        else:
            result = await session.execute(
                select(User).options(selectinload(User.courses)).where(User.user_id == callback.from_user.id)
            )
            user = result.scalar_one_or_none()
            courses = user.courses if user else []

    if not courses:
        await callback.message.edit_text("📭 Курсов пока нет.")
        return

    text = "📘 Ваши курсы:" if callback.from_user.id != ADMIN_ID else "📘 Все доступные курсы:"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=course.title, callback_data=f"mycourse:{course.id}")]
            for course in courses
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# --- Удаление курса (только админ) ---
@my_courses_router.callback_query(F.data.startswith("delcourse:"))
async def delete_course(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ У вас нет прав для удаления курсов.", show_alert=True)
        return

    course_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        course = await session.get(Course, course_id)
        if not course:
            await callback.answer("⚠️ Курс не найден.", show_alert=True)
            return
        await session.delete(course)
        await session.commit()

    await callback.message.edit_text(f"🗑 Курс «{course.title}» удалён!")


# --- Изменение цены ---
@my_courses_router.callback_query(F.data.startswith("edit_price:"))
async def edit_price(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return

    course_id = int(callback.data.split(":")[1])
    await state.update_data(course_id=course_id)
    await state.set_state(CourseEditFSM.waiting_for_price)

    await callback.message.answer("💰 Введите новую цену курса (число):")


@my_courses_router.message(CourseEditFSM.waiting_for_price, F.text.regexp(r"^\d+$"))
async def process_new_price(message: types.Message, state: FSMContext):
    data = await state.get_data()
    course_id = data.get("course_id")
    new_price = int(message.text)

    async with async_session() as session:
        course = await session.get(Course, course_id)
        if not course:
            await message.answer("⚠️ Курс не найден.")
            await state.clear()
            return

        course.price = new_price
        await session.commit()

    await message.answer(f"✅ Цена курса «{course.title}» изменена на {new_price} руб.")
    await state.clear()


# --- Изменение названия ---
@my_courses_router.callback_query(F.data.startswith("edit_title:"))
async def edit_title(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return

    course_id = int(callback.data.split(":")[1])
    await state.update_data(course_id=course_id)
    await state.set_state(CourseEditFSM.waiting_for_title)

    await callback.message.answer("✏️ Введите новое название курса:")


@my_courses_router.message(CourseEditFSM.waiting_for_title)
async def process_new_title(message: types.Message, state: FSMContext):
    data = await state.get_data()
    course_id = data.get("course_id")
    new_title = message.text.strip()

    async with async_session() as session:
        course = await session.get(Course, course_id)
        if not course:
            await message.answer("⚠️ Курс не найден.")
            await state.clear()
            return

        course.title = new_title
        await session.commit()

    await message.answer(f"✅ Название изменено на «{new_title}».")
    await state.clear()


# --- Изменение описания ---
@my_courses_router.callback_query(F.data.startswith("edit_desc:"))
async def edit_desc(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return

    course_id = int(callback.data.split(":")[1])
    await state.update_data(course_id=course_id)
    await state.set_state(CourseEditFSM.waiting_for_description)

    await callback.message.answer("📝 Введите новое описание курса:")


@my_courses_router.message(CourseEditFSM.waiting_for_description)
async def process_new_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    course_id = data.get("course_id")
    new_desc = message.text.strip()

    async with async_session() as session:
        course = await session.get(Course, course_id)
        if not course:
            await message.answer("⚠️ Курс не найден.")
            await state.clear()
            return

        course.description = new_desc
        await session.commit()

    await message.answer("✅ Описание курса обновлено.")
    await state.clear()

# handlers/admin.py

from aiogram import Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import User, Course, async_session
from config.bot_config import ADMIN_ID
from fsm.courses import CourseFSM
from aiogram.fsm.context import FSMContext

admin_router = Router()


# --- Главное меню админа ---
def admin_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Список пользователей", callback_data="show_users")],
            [InlineKeyboardButton(text="Управление курсами", callback_data="manage_courses")],
            [InlineKeyboardButton(text="Добавить курс", callback_data="add_course")]
        ]
    )


def admin_back_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔝 Главное меню администратора", callback_data="admin_menu")]]
    )


@admin_router.message(F.text == "Управление курсами и пользователями")
async def admin_main_menu(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return
    await message.answer("👤 Меню администратора:", reply_markup=admin_main_keyboard())


# --- Просмотр пользователей с фото и документами ---
@admin_router.callback_query(F.data == "show_users")
async def show_users(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    if not users:
        await callback.message.edit_text("📭 Пользователей пока нет.")
        await callback.answer()
        return

    for user in users:
        text = f"👤 {user.name} ({user.phone or 'не указан'})"
        await callback.message.answer(text)

        if user.photo:
            await callback.message.answer_photo(user.photo, caption="Фото пользователя")

        if user.document:
            await callback.message.answer_document(user.document, caption="Документ пользователя")

    await callback.message.answer("⬆️ Вернитесь в главное меню администратора:", reply_markup=admin_back_keyboard())
    await callback.answer()


# --- Управление курсами ---
@admin_router.callback_query(F.data == "manage_courses")
async def manage_courses(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(select(Course))
        courses = result.scalars().all()

    if not courses:
        await callback.message.edit_text("📭 Курсов пока нет.")
        await callback.answer()
        return

    for c in courses:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Редактировать", callback_data=f"edit_course:{c.id}"),
                    InlineKeyboardButton(text="Удалить", callback_data=f"delete_course:{c.id}")
                ]
            ]
        )
        await callback.message.answer(
            f"📘 {c.title}\n💰 {c.price} руб.\n{c.description or 'Описание отсутствует'}",
            reply_markup=keyboard
        )

    await callback.message.answer("⬆️ Вернитесь в главное меню администратора:", reply_markup=admin_back_keyboard())
    await callback.answer()


# --- Кнопка "Назад" ---
@admin_router.callback_query(F.data == "admin_menu")
async def back_to_admin_menu(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await callback.message.edit_text("👤 Меню администратора:", reply_markup=admin_main_keyboard())
    await callback.answer()


# --- Удаление курса ---
@admin_router.callback_query(F.data.startswith("delete_course:"))
async def delete_course(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    course_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        course = await session.get(Course, course_id)
        if course:
            await session.delete(course)
            await session.commit()
            await callback.message.edit_text(f"🗑 Курс «{course.title}» удалён.")
        else:
            await callback.answer("⚠️ Курс не найден.", show_alert=True)


# --- Добавление курса ---
@admin_router.callback_query(F.data == "add_course")
async def add_course_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.message.answer("Введите название нового курса:")
    await state.set_state(CourseFSM.title)
    await state.update_data(edit=False)
    await callback.answer()


# --- Редактирование курса ---
@admin_router.callback_query(F.data.startswith("edit_course:"))
async def edit_course_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    course_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        course = await session.get(Course, course_id)

    if not course:
        await callback.answer("⚠️ Курс не найден", show_alert=True)
        return

    await state.update_data(course_id=course.id, edit=True)
    await callback.message.answer(f"Введите новое название курса (текущее: {course.title}):")
    await state.set_state(CourseFSM.title)
    await callback.answer()


# --- FSM для добавления/редактирования ---
@admin_router.message(CourseFSM.title)
async def process_course_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await message.answer("Введите описание курса (или '-' для пустого):")
    await state.set_state(CourseFSM.description)


@admin_router.message(CourseFSM.description)
async def process_course_description(message: Message, state: FSMContext):
    desc = message.text.strip()
    if desc == "-":
        desc = None
    await state.update_data(description=desc)
    await message.answer("Введите цену курса (числом):")
    await state.set_state(CourseFSM.price)


@admin_router.message(CourseFSM.price)
async def process_course_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Цена должна быть положительным числом. Попробуйте ещё раз:")
        return

    data = await state.get_data()
    async with async_session() as session:
        if data.get("edit"):
            course = await session.get(Course, data["course_id"])
            course.title = data["title"]
            course.description = data["description"]
            course.price = price
            session.add(course)
            await session.commit()
            await message.answer(f"✅ Курс «{course.title}» успешно обновлён!")
        else:
            course = Course(
                title=data["title"],
                description=data["description"],
                price=price
            )
            session.add(course)
            await session.commit()
            await message.answer(f"✅ Курс «{course.title}» успешно добавлен!")

    await message.answer("⬆️ Вернитесь в главное меню администратора:", reply_markup=admin_back_keyboard())
    await state.clear()

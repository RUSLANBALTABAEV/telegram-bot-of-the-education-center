from aiogram import Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import User, Course, async_session
from config.bot_config import ADMIN_ID

admin_router = Router()

# --- Главное меню админа: одна кнопка ---
@admin_router.message(F.text == "Управление курсами и пользователями")
async def admin_main_menu(message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Список пользователей", callback_data="show_users")],
            [InlineKeyboardButton(text="Управление курсами", callback_data="manage_courses")]
        ]
    )
    await message.answer("👤 Меню администратора:", reply_markup=keyboard)


# --- Callback: показать список пользователей ---
@admin_router.callback_query(F.data == "show_users")
async def show_users(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(select(User).options(selectinload(User.courses)))
        users = result.scalars().all()

    if not users:
        await callback.message.edit_text("📭 Пользователей пока нет.")
        await callback.answer()
        return

    text = "👥 Пользователи:\n"
    for u in users:
        text += f"• {u.name} ({u.phone or 'не указан'})\n"

    # Добавляем кнопку "Назад" в админ-меню
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


# --- Callback: управление курсами ---
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

    # Добавляем кнопку "Назад" в админ-меню
    keyboard_back = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]
        ]
    )
    await callback.message.answer("Вы вернулись в меню админа:", reply_markup=keyboard_back)
    await callback.answer()


# --- Callback кнопка "Назад" в админ-меню ---
@admin_router.callback_query(F.data == "admin_menu")
async def back_to_admin_menu(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Список пользователей", callback_data="show_users")],
            [InlineKeyboardButton(text="Управление курсами", callback_data="manage_courses")]
        ]
    )
    await callback.message.edit_text("👤 Меню администратора:", reply_markup=keyboard)
    await callback.answer()


# --- Callback редактирования/удаления курса ---
@admin_router.callback_query(F.data.startswith("delete_course:"))
async def delete_course(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
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

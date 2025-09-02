from aiogram import Router, F, types
from aiogram.filters import Command
from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload
from db.models import User, Course, async_session
from config.bot_config import ADMIN_ID
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

admin_router = Router()

@admin_router.message(F.text == "Пользователи")
async def list_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return

    async with async_session() as session:
        result = await session.execute(select(User).options(selectinload(User.courses)))
        users = result.scalars().all()

    if not users:
        await message.answer("📭 Пользователей пока нет.")
        return

    text = "👥 Пользователи:\n"
    for u in users:
        text += f"• {u.name} ({u.phone})\n"
    await message.answer(text)

# --- Управление курсами ---
@admin_router.message(F.text == "Управление курсами")
async def manage_courses(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return

    async with async_session() as session:
        result = await session.execute(select(Course))
        courses = result.scalars().all()

    if not courses:
        await message.answer("📭 Курсов пока нет.")
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
        await message.answer(f"📘 {c.title}\n💰 {c.price} руб.\n{c.description or 'Описание отсутствует'}",
                             reply_markup=keyboard)

# --- Callback редактирования ---
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

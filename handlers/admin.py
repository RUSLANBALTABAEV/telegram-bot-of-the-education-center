from aiogram import Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from db.models import User, Course, Certificate
from db.session import async_session
from config.bot_config import ADMIN_ID
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import datetime
from keyboards.reply import admin_main_keyboard, admin_back_keyboard
from i18n.locales import get_text

admin_router = Router()

async def get_user_language(user_id: int) -> str:
    """Получить язык пользователя из БД"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        return user.language if user and user.language else "ru"

# ---------------- FSM ----------------
class AddCourseFSM(StatesGroup):
    title = State()
    description = State()
    price = State()
    start_date = State()
    end_date = State()

class EditCourseFSM(StatesGroup):
    course_id = State()
    title = State()
    description = State()
    price = State()
    start_date = State()
    end_date = State()

class CertificateFSM(StatesGroup):
    tg_user_id = State()
    title = State()
    file = State()

# ---------------- Админ-меню ----------------
@admin_router.message(F.text.in_(["Управление курсами и пользователями", "Manage Courses and Users", "Kurs va foydalanuvchilarni boshqarish"]))
async def admin_main_menu(message: Message):
    if message.from_user.id != ADMIN_ID:
        lang = await get_user_language(message.from_user.id)
        await message.answer(get_text("no_access", lang))
        return
    
    lang = await get_user_language(message.from_user.id)
    await message.answer(get_text("admin_main_menu", lang), reply_markup=admin_main_keyboard(lang))

@admin_router.callback_query(F.data == "admin_menu")
async def back_to_admin_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if callback.from_user.id != ADMIN_ID:
        lang = await get_user_language(callback.from_user.id)
        await callback.answer(get_text("no_access", lang), show_alert=True)
        return
    
    lang = await get_user_language(callback.from_user.id)
    try:
        await callback.message.edit_text(get_text("admin_main_menu", lang), reply_markup=admin_main_keyboard(lang))
    except Exception:
        await callback.message.answer(get_text("admin_main_menu", lang), reply_markup=admin_main_keyboard(lang))
    await callback.answer()

# ---------------- Пользователи ----------------
@admin_router.callback_query(F.data == "show_users")
async def show_users(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        lang = await get_user_language(callback.from_user.id)
        await callback.answer(get_text("no_access", lang), show_alert=True)
        return

    lang = await get_user_language(callback.from_user.id)
    
    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    if not users:
        try:
            await callback.message.edit_text(get_text("no_users", lang), reply_markup=admin_back_keyboard(lang))
        except Exception:
            await callback.message.answer(get_text("no_users", lang), reply_markup=admin_back_keyboard(lang))
        await callback.answer()
        return

    for user in users:
        user_name = user.name or get_text("without_name", lang)
        phone = user.phone or get_text("not_specified", lang)
        text = f"👤 {user_name}\n🆔 Telegram ID: {user.user_id}\n🗄 DB ID: {user.id}\n📱 {phone}"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=get_text("btn_delete", lang), callback_data=f"delete_user:{user.id}")]
            ]
        )

        try:
            if user.photo:
                await callback.message.answer_photo(photo=user.photo, caption=text, reply_markup=keyboard)
            else:
                await callback.message.answer(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text + "\n\n⚠️ Не удалось отправить фото.", reply_markup=keyboard)

    await callback.message.answer(get_text("btn_admin_back", lang), reply_markup=admin_back_keyboard(lang))
    await callback.answer()

@admin_router.callback_query(F.data.startswith("delete_user:"))
async def delete_user(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        lang = await get_user_language(callback.from_user.id)
        await callback.answer(get_text("no_access", lang), show_alert=True)
        return

    lang = await get_user_language(callback.from_user.id)
    user_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await callback.answer(get_text("user_not_found", lang), show_alert=True)
            return

        username = user.name or get_text("without_name", lang)
        telegram_id = user.user_id or get_text("unknown", lang)

        await session.delete(user)
        await session.commit()

    try:
        message_text = get_text("user_deleted", lang, name=username, telegram_id=telegram_id)
        await callback.message.answer(message_text, reply_markup=admin_back_keyboard(lang))
        await callback.message.delete()
    except Exception:
        message_text = get_text("user_deleted", lang, name=username, telegram_id=telegram_id)
        await callback.answer(message_text, show_alert=True)

    await callback.answer()

@admin_router.callback_query(F.data == "delete_all_users")
async def delete_all_users(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        lang = await get_user_language(callback.from_user.id)
        await callback.answer(get_text("no_access", lang), show_alert=True)
        return

    lang = await get_user_language(callback.from_user.id)

    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        if not users:
            await callback.answer(get_text("no_users_to_delete", lang), show_alert=True)
            return

        for user in users:
            await session.delete(user)
        await session.commit()

    try:
        await callback.message.answer(get_text("all_users_deleted", lang), reply_markup=admin_back_keyboard(lang))
        await callback.message.delete()
    except Exception:
        await callback.answer(get_text("all_users_deleted", lang), show_alert=True)

    await callback.answer()

from aiogram import Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from db.models import User, Course, Certificate
from db.session import async_session
from config.bot_config import ADMIN_ID
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from datetime import datetime
from keyboards.reply import admin_main_keyboard, admin_back_keyboard
from i18n.locales import get_text

admin_router = Router()

async def get_user_language(user_id: int) -> str:
    """Получить язык пользователя из БД"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        return user.language if user and user.language else "ru"

# ---------------- FSM ----------------
class AddCourseFSM(StatesGroup):
    title = State()
    description = State()
    price = State()
    start_date = State()
    end_date = State()

class EditCourseFSM(StatesGroup):
    course_id = State()
    title = State()
    description = State()
    price = State()
    start_date = State()
    end_date = State()

class CertificateFSM(StatesGroup):
    tg_user_id = State()
    title = State()
    file = State()

# ---------------- Админ-меню ----------------
@admin_router.message(F.text.in_(["Управление курсами и пользователями", "Manage Courses and Users", "Kurs va foydalanuvchilarni boshqarish"]))
async def admin_main_menu(message: Message):
    if message.from_user.id != ADMIN_ID:
        lang = await get_user_language(message.from_user.id)
        await message.answer(get_text("no_access", lang))
        return
    
    lang = await get_user_language(message.from_user.id)
    await message.answer(get_text("admin_main_menu", lang), reply_markup=admin_main_keyboard(lang))

@admin_router.callback_query(F.data == "admin_menu")
async def back_to_admin_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if callback.from_user.id != ADMIN_ID:
        lang = await get_user_language(callback.from_user.id)
        await callback.answer(get_text("no_access", lang), show_alert=True)
        return
    
    lang = await get_user_language(callback.from_user.id)
    try:
        await callback.message.edit_text(get_text("admin_main_menu", lang), reply_markup=admin_main_keyboard(lang))
    except Exception:
        await callback.message.answer(get_text("admin_main_menu", lang), reply_markup=admin_main_keyboard(lang))
    await callback.answer()

# ---------------- Пользователи ----------------
@admin_router.callback_query(F.data == "show_users")
async def show_users(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        lang = await get_user_language(callback.from_user.id)
        await callback.answer(get_text("no_access", lang), show_alert=True)
        return

    lang = await get_user_language(callback.from_user.id)
    
    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    if not users:
        try:
            await callback.message.edit_text(get_text("no_users", lang), reply_markup=admin_back_keyboard(lang))
        except Exception:
            await callback.message.answer(get_text("no_users", lang), reply_markup=admin_back_keyboard(lang))
        await callback.answer()
        return

    for user in users:
        user_name = user.name or get_text("without_name", lang)
        phone = user.phone or get_text("not_specified", lang)
        text = f"👤 {user_name}\n🆔 Telegram ID: {user.user_id}\n🗄 DB ID: {user.id}\n📱 {phone}"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=get_text("btn_delete", lang), callback_data=f"delete_user:{user.id}")]
            ]
        )

        try:
            if user.photo:
                await callback.message.answer_photo(photo=user.photo, caption=text, reply_markup=keyboard)
            else:
                await callback.message.answer(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text + "\n\n⚠️ Не удалось отправить фото.", reply_markup=keyboard)

    await callback.message.answer(get_text("btn_admin_back", lang), reply_markup=admin_back_keyboard(lang))
    await callback.answer()

@admin_router.callback_query(F.data.startswith("delete_user:"))
async def delete_user(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        lang = await get_user_language(callback.from_user.id)
        await callback.answer(get_text("no_access", lang), show_alert=True)
        return

    lang = await get_user_language(callback.from_user.id)
    user_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await callback.answer(get_text("user_not_found", lang), show_alert=True)
            return

        username = user.name or get_text("without_name", lang)
        telegram_id = user.user_id or get_text("unknown", lang)

        await session.delete(user)
        await session.commit()

    try:
        message_text = get_text("user_deleted", lang, name=username, telegram_id=telegram_id)
        await callback.message.answer(message_text, reply_markup=admin_back_keyboard(lang))
        await callback.message.delete()
    except Exception:
        message_text = get_text("user_deleted", lang, name=username, telegram_id=telegram_id)
        await callback.answer(message_text, show_alert=True)

    await callback.answer()

@admin_router.callback_query(F.data == "delete_all_users")
async def delete_all_users(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        lang = await get_user_language(callback.from_user.id)
        await callback.answer(get_text("no_access", lang), show_alert=True)
        return

    lang = await get_user_language(callback.from_user.id)

    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        if not users:
            await callback.answer(get_text("no_users_to_delete", lang), show_alert=True)
            return

        for user in users:
            await session.delete(user)
        await session.commit()

    try:
        await callback.message.answer(get_text("all_users_deleted", lang), reply_markup=admin_back_keyboard(lang))
        await callback.message.delete()
    except Exception:
        await callback.answer(get_text("all_users_deleted", lang), show_alert=True)

    await callback.answer()

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

# ---------------- Курсы ----------------
@admin_router.callback_query(F.data == "manage_courses")
async def manage_courses(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        lang = await get_user_language(callback.from_user.id)
        await callback.answer(get_text("no_access", lang), show_alert=True)
        return

    lang = await get_user_language(callback.from_user.id)

    async with async_session() as session:
        result = await session.execute(select(Course))
        courses = result.scalars().all()

    if not courses:
        try:
            await callback.message.edit_text(get_text("no_courses", lang), reply_markup=admin_back_keyboard(lang))
        except Exception:
            await callback.message.answer(get_text("no_courses", lang), reply_markup=admin_back_keyboard(lang))
        await callback.answer()
        return

    text = get_text("course_list", lang)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=course.title, callback_data=f"course_admin:{course.id}")]
            for course in courses
        ] + [[InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="admin_menu")]]
    )
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

@admin_router.callback_query(F.data.startswith("course_admin:"))
async def course_admin_menu(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        lang = await get_user_language(callback.from_user.id)
        await callback.answer(get_text("no_access", lang), show_alert=True)
        return

    lang = await get_user_language(callback.from_user.id)
    course_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        course = await session.get(Course, course_id)

    if not course:
        await callback.answer(get_text("course_not_found", lang), show_alert=True)
        return

    start_date = course.start_date.strftime("%d.%m.%Y") if course.start_date else get_text("not_indicated", lang)
    end_date = course.end_date.strftime("%d.%m.%Y") if course.end_date else get_text("not_indicated", lang)
    
    text = (
        f"📘 <b>{course.title}</b>\n\n"
        f"{course.description or get_text('no_description', lang)}\n"
        f"{get_text('price', lang, price=course.price)}\n"
        f"{get_text('dates', lang, start=start_date, end=end_date)}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_text("btn_edit", lang), callback_data=f"edit_course:{course.id}")],
            [InlineKeyboardButton(text=get_text("btn_delete", lang), callback_data=f"delete_course:{course.id}")],
            [InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="manage_courses")]
        ]
    )
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@admin_router.callback_query(F.data.startswith("delete_course:"))
async def delete_course(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        lang = await get_user_language(callback.from_user.id)
        await callback.answer(get_text("no_access", lang), show_alert=True)
        return

    lang = await get_user_language(callback.from_user.id)
    course_id = int(callback.data.split(":")[1])
    
    async with async_session() as session:
        course = await session.get(Course, course_id)
        if not course:
            await callback.answer(get_text("course_not_found", lang), show_alert=True)
            return
        title = course.title
        await session.delete(course)
        await session.commit()

    try:
        message_text = get_text("course_deleted", lang, title=title)
        await callback.message.answer(message_text, reply_markup=admin_back_keyboard(lang))
        await callback.message.delete()
    except Exception:
        message_text = get_text("course_deleted", lang, title=title)
        await callback.answer(message_text, show_alert=True)
    await callback.answer()

# ---------------- Добавление курса ----------------
@admin_router.callback_query(F.data == "add_course")
async def add_course_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        lang = await get_user_language(callback.from_user.id)
        await callback.answer(get_text("no_access", lang), show_alert=True)
        return

    lang = await get_user_language(callback.from_user.id)
    await state.set_state(AddCourseFSM.title)
    try:
        await callback.message.edit_text(get_text("enter_course_title", lang))
    except Exception:
        await callback.message.answer(get_text("enter_course_title", lang))
    await callback.answer()

@admin_router.message(AddCourseFSM.title)
async def add_course_title(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
        
    lang = await get_user_language(message.from_user.id)
    await state.update_data(title=message.text.strip())
    await state.set_state(AddCourseFSM.description)
    await message.answer(get_text("enter_course_description", lang))

@admin_router.message(AddCourseFSM.description)
async def add_course_description(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
        
    lang = await get_user_language(message.from_user.id)
    await state.update_data(description=message.text.strip())
    await state.set_state(AddCourseFSM.price)
    await message.answer(get_text("enter_course_price", lang))

@admin_router.message(AddCourseFSM.price, F.text.regexp(r"^\d+$"))
async def add_course_price(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
        
    lang = await get_user_language(message.from_user.id)
    await state.update_data(price=int(message.text.strip()))
    await state.set_state(AddCourseFSM.start_date)
    await message.answer(get_text("enter_start_date", lang))

@admin_router.message(AddCourseFSM.start_date)
async def add_course_start_date(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
        
    lang = await get_user_language(message.from_user.id)
    try:
        start_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer(get_text("invalid_date_format", lang))
        return
    await state.update_data(start_date=start_date)
    await state.set_state(AddCourseFSM.end_date)
    await message.answer(get_text("enter_end_date", lang))

@admin_router.message(AddCourseFSM.end_date)
async def add_course_end_date(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
        
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    
    try:
        end_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer(get_text("invalid_date_format", lang))
        return

    if end_date < data["start_date"]:
        await message.answer(get_text("end_date_before_start", lang))
        return

    async with async_session() as session:
        new_course = Course(
            title=data["title"],
            description=data["description"],
            price=data["price"],
            start_date=data["start_date"],
            end_date=end_date
        )
        try:
            session.add(new_course)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            await message.answer(get_text("course_title_exists", lang))
            await state.clear()
            return

    await message.answer(get_text("course_added", lang, title=data['title']), reply_markup=admin_back_keyboard(lang))
    await state.clear()

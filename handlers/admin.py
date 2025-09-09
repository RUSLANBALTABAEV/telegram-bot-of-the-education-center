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

admin_router = Router()


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


# ---------------- Keyboards ----------------
def admin_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Список пользователей", callback_data="show_users")],
            [InlineKeyboardButton(text="📚 Управление курсами", callback_data="manage_courses")],
            [InlineKeyboardButton(text="➕ Добавить курс", callback_data="add_course")],
            [InlineKeyboardButton(text="🏅 Выдать сертификат", callback_data="add_certificate")],
            [InlineKeyboardButton(text="🗑 Удалить всех пользователей", callback_data="delete_all_users")],
        ]
    )


def admin_back_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔝 Главное меню администратора", callback_data="admin_menu")]]
    )


# ---------------- Админ-меню ----------------
@admin_router.message(F.text == "Управление курсами и пользователями")
async def admin_main_menu(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return
    await message.answer("👤 Главное меню администратора:", reply_markup=admin_main_keyboard())


@admin_router.callback_query(F.data == "admin_menu")
async def back_to_admin_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    try:
        await callback.message.edit_text("👤 Главное меню администратора:", reply_markup=admin_main_keyboard())
    except Exception:
        await callback.message.answer("👤 Главное меню администратора:", reply_markup=admin_main_keyboard())
    await callback.answer()


# ---------------- Пользователи ----------------
@admin_router.callback_query(F.data == "show_users")
async def show_users(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    if not users:
        try:
            await callback.message.edit_text("📭 Пользователей пока нет.", reply_markup=admin_back_keyboard())
        except Exception:
            await callback.message.answer("📭 Пользователей пока нет.", reply_markup=admin_back_keyboard())
        await callback.answer()
        return

    for user in users:
        text = f"👤 {user.name or 'Без имени'}\n🆔 Telegram ID: {user.user_id}\n🗄 DB ID: {user.id}\n📱 {user.phone or '—'}"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_user:{user.id}")]
            ]
        )

        try:
            if user.photo:
                await callback.message.answer_photo(photo=user.photo, caption=text, reply_markup=keyboard)
            else:
                await callback.message.answer(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text + "\n\n⚠️ Не удалось отправить фото.", reply_markup=keyboard)

    await callback.message.answer("🔙 Главное меню администратора", reply_markup=admin_back_keyboard())
    await callback.answer()


@admin_router.callback_query(F.data.startswith("delete_user:"))
async def delete_user(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    user_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        user = await session.get(User, user_id)
        if not user:
            await callback.answer("⚠️ Пользователь не найден.", show_alert=True)
            return

        username = user.name or "Без имени"
        telegram_id = user.user_id or "неизвестный"

        await session.delete(user)
        await session.commit()

    try:
        await callback.message.answer(f"🗑 Пользователь «{username}» (TG ID: {telegram_id}) удалён.", reply_markup=admin_back_keyboard())
        await callback.message.delete()
    except Exception:
        await callback.answer(f"🗑 Пользователь «{username}» удалён.", show_alert=True)

    await callback.answer()


@admin_router.callback_query(F.data == "delete_all_users")
async def delete_all_users(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        if not users:
            await callback.answer("⚠️ Пользователей нет.", show_alert=True)
            return

        for user in users:
            await session.delete(user)
        await session.commit()

    try:
        await callback.message.answer("🗑 Все пользователи удалены.", reply_markup=admin_back_keyboard())
        await callback.message.delete()
    except Exception:
        await callback.answer("🗑 Все пользователи удалены.", show_alert=True)

    await callback.answer()


# ---------------- Курсы ----------------
@admin_router.callback_query(F.data == "manage_courses")
async def manage_courses(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(select(Course))
        courses = result.scalars().all()

    if not courses:
        try:
            await callback.message.edit_text("📚 Курсов пока нет.", reply_markup=admin_back_keyboard())
        except Exception:
            await callback.message.answer("📚 Курсов пока нет.", reply_markup=admin_back_keyboard())
        await callback.answer()
        return

    text = "📚 Список курсов:"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=course.title, callback_data=f"course_admin:{course.id}")]
            for course in courses
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]]
    )
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


# ---------------- Курсы: управление ----------------
@admin_router.callback_query(F.data.startswith("course_admin:"))
async def course_admin_menu(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    course_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        course = await session.get(Course, course_id)

    if not course:
        await callback.answer("⚠️ Курс не найден.", show_alert=True)
        return

    text = (
        f"📘 <b>{course.title}</b>\n\n"
        f"{course.description or 'Без описания'}\n"
        f"💰 {course.price} руб.\n"
        f"📅 {course.start_date or 'не указана'} — {course.end_date or 'не указана'}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_course:{course.id}")],
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_course:{course.id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="manage_courses")]
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
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    course_id = int(callback.data.split(":")[1])
    async with async_session() as session:
        course = await session.get(Course, course_id)
        if not course:
            await callback.answer("⚠️ Курс не найден.", show_alert=True)
            return
        title = course.title
        await session.delete(course)
        await session.commit()

    try:
        await callback.message.answer(f"🗑 Курс «{title}» удалён.", reply_markup=admin_back_keyboard())
        await callback.message.delete()
    except Exception:
        await callback.answer(f"🗑 Курс «{title}» удалён.", show_alert=True)
    await callback.answer()


# ---------------- Добавление курса ----------------
@admin_router.callback_query(F.data == "add_course")
async def add_course_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddCourseFSM.title)
    try:
        await callback.message.edit_text("➕ Введите название нового курса:")
    except Exception:
        await callback.message.answer("➕ Введите название нового курса:")
    await callback.answer()


@admin_router.message(AddCourseFSM.title)
async def add_course_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AddCourseFSM.description)
    await message.answer("Введите описание курса:")


@admin_router.message(AddCourseFSM.description)
async def add_course_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AddCourseFSM.price)
    await message.answer("Введите цену курса (число):")


@admin_router.message(AddCourseFSM.price, F.text.regexp(r"^\d+$"))
async def add_course_price(message: Message, state: FSMContext):
    await state.update_data(price=int(message.text.strip()))
    await state.set_state(AddCourseFSM.start_date)
    await message.answer("Введите дату начала курса (ДД.MM.ГГГГ):")


@admin_router.message(AddCourseFSM.start_date)
async def add_course_start_date(message: Message, state: FSMContext):
    try:
        start_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("⚠️ Неверный формат даты. Введите снова (ДД.MM.ГГГГ):")
        return
    await state.update_data(start_date=start_date)
    await state.set_state(AddCourseFSM.end_date)
    await message.answer("Введите дату окончания курса (ДД.MM.ГГГГ):")


@admin_router.message(AddCourseFSM.end_date)
async def add_course_end_date(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        end_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("⚠️ Неверный формат даты. Введите снова (ДД.MM.ГГГГ):")
        return

    if end_date < data["start_date"]:
        await message.answer("⚠️ Дата окончания не может быть раньше даты начала.")
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
            await message.answer("⚠️ Курс с таким названием уже существует!")
            await state.clear()
            return

    await message.answer(f"✅ Курс «{data['title']}» добавлен!", reply_markup=admin_back_keyboard())
    await state.clear()

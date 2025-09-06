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
    await callback.message.edit_text("👤 Главное меню администратора:", reply_markup=admin_main_keyboard())
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
        await callback.message.edit_text("📭 Пользователей пока нет.", reply_markup=admin_back_keyboard())
        await callback.answer()
        return

    for user in users:
        text = f"👤 {user.name or 'Без имени'}\n🆔 Telegram ID: {user.user_id}\n🗄 DB ID: {user.id}"
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_user:{user.id}")]
            ]
        )
        await callback.message.answer(text, reply_markup=keyboard)

    await callback.message.answer(reply_markup=admin_back_keyboard())
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

        await session.delete(user)
        await session.commit()

    await callback.message.edit_text(f"🗑 Пользователь «{user.name}» удалён.")
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

    await callback.message.edit_text("🗑 Все пользователи удалены.", reply_markup=admin_back_keyboard())
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
        await callback.message.edit_text("📚 Курсов пока нет.", reply_markup=admin_back_keyboard())
        await callback.answer()
        return

    text = "📚 Список курсов:"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=course.title, callback_data=f"course_admin:{course.id}")]
            for course in courses
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]]
    )
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


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
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
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
        await session.delete(course)
        await session.commit()

    await callback.message.edit_text(f"🗑 Курс «{course.title}» удалён.", reply_markup=admin_back_keyboard())
    await callback.answer()


# ----------- Добавление курса -----------
@admin_router.callback_query(F.data == "add_course")
async def add_course_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddCourseFSM.title)
    await callback.message.edit_text("➕ Введите название нового курса:")
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
    await message.answer("Введите дату начала курса (ДД.ММ.ГГГГ):")


@admin_router.message(AddCourseFSM.start_date)
async def add_course_start_date(message: Message, state: FSMContext):
    try:
        start_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("⚠️ Неверный формат даты.")
        return
    await state.update_data(start_date=start_date)
    await state.set_state(AddCourseFSM.end_date)
    await message.answer("Введите дату окончания курса (ДД.ММ.ГГГГ):")


@admin_router.message(AddCourseFSM.end_date)
async def add_course_end_date(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        end_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("⚠️ Неверный формат даты.")
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


# ----------- Редактирование курса -----------
@admin_router.callback_query(F.data.startswith("edit_course:"))
async def edit_course_start(callback: CallbackQuery, state: FSMContext):
    course_id = int(callback.data.split(":")[1])
    await state.set_state(EditCourseFSM.title)
    await state.update_data(course_id=course_id)
    await callback.message.edit_text("✏️ Введите новое название курса:")
    await callback.answer()


@admin_router.message(EditCourseFSM.title)
async def edit_course_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(EditCourseFSM.description)
    await message.answer("Введите новое описание курса:")


@admin_router.message(EditCourseFSM.description)
async def edit_course_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(EditCourseFSM.price)
    await message.answer("Введите новую цену (число):")


@admin_router.message(EditCourseFSM.price, F.text.regexp(r"^\d+$"))
async def edit_course_price(message: Message, state: FSMContext):
    await state.update_data(price=int(message.text.strip()))
    await state.set_state(EditCourseFSM.start_date)
    await message.answer("Введите новую дату начала курса (ДД.ММ.ГГГГ):")


@admin_router.message(EditCourseFSM.start_date)
async def edit_course_start_date(message: Message, state: FSMContext):
    try:
        start_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("⚠️ Неверный формат даты.")
        return
    await state.update_data(start_date=start_date)
    await state.set_state(EditCourseFSM.end_date)
    await message.answer("Введите новую дату окончания курса (ДД.ММ.ГГГГ):")


@admin_router.message(EditCourseFSM.end_date)
async def edit_course_end_date(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        end_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except ValueError:
        await message.answer("⚠️ Неверный формат даты.")
        return

    if end_date < data["start_date"]:
        await message.answer("⚠️ Дата окончания не может быть раньше даты начала.")
        return

    async with async_session() as session:
        course = await session.get(Course, data["course_id"])
        if not course:
            await message.answer("⚠️ Курс не найден.")
            await state.clear()
            return

        course.title = data["title"]
        course.description = data["description"]
        course.price = data["price"]
        course.start_date = data["start_date"]
        course.end_date = end_date

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            await message.answer("⚠️ Курс с таким названием уже существует!")
            await state.clear()
            return

    await message.answer(f"✅ Курс «{data['title']}» обновлён.", reply_markup=admin_back_keyboard())
    await state.clear()


# ---------------- Сертификаты ----------------
@admin_router.callback_query(F.data == "add_certificate")
async def add_certificate_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CertificateFSM.tg_user_id)
    await callback.message.edit_text("Введите Telegram ID пользователя:")
    await callback.answer()


@admin_router.message(CertificateFSM.tg_user_id, F.text.regexp(r"^\d+$"))
async def add_certificate_user(message: Message, state: FSMContext):
    tg_id = int(message.text.strip())
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("⚠️ Пользователь не найден.")
            await state.clear()
            return

    await state.update_data(user_db_id=user.id)
    await state.set_state(CertificateFSM.title)
    await message.answer(f"✅ Пользователь найден: {user.name}. Введите название сертификата:")


@admin_router.message(CertificateFSM.title)
async def add_certificate_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(CertificateFSM.file)
    await message.answer("Отправьте файл сертификата:")


@admin_router.message(CertificateFSM.file, F.document)
async def add_certificate_file(message: Message, state: FSMContext):
    file_id = message.document.file_id
    data = await state.get_data()
    async with async_session() as session:
        new_cert = Certificate(
            title=data["title"],
            file_id=file_id,
            user_id=data["user_db_id"]
        )
        session.add(new_cert)
        await session.commit()

    await message.answer(f"✅ Сертификат «{data['title']}» выдан.")
    await state.clear()

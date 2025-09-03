from aiogram import Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db.models import User, Course, async_session
from config.bot_config import ADMIN_ID
from fsm.courses import CourseFSM

admin_router = Router()


# --- Кнопки ---
def admin_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Список пользователей", callback_data="show_users")],
            [InlineKeyboardButton(text="Управление курсами", callback_data="manage_courses")],
            [InlineKeyboardButton(text="Добавить курс", callback_data="add_course")],
        ]
    )


def admin_back_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔝 Главное меню администратора", callback_data="admin_menu")]]
    )


def manage_courses_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить курс", callback_data="add_course")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")],
        ]
    )


# --- Вход в админ-меню ---
@admin_router.message(F.text == "Управление курсами и пользователями")
async def admin_main_menu(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        return
    await message.answer("👤 Меню администратора:", reply_markup=admin_main_keyboard())


# --- Возврат в главное меню ---
@admin_router.callback_query(F.data == "admin_menu")
async def back_to_admin_menu(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text("👤 Меню администратора:", reply_markup=admin_main_keyboard())
    await callback.answer()


# --- Просмотр пользователей ---
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

    # Текущее сообщение заменяем заголовком…
    await callback.message.edit_text("👥 Список пользователей:")
    # …а записи выводим отдельными сообщениями, чтобы не упереться в лимит длины
    for user in users:
        text = f"👤 {user.name} ({user.phone or 'не указан'})"
        await callback.message.answer(text)

        if user.photo:
            await callback.message.answer_photo(user.photo, caption="Фото пользователя")

        if user.document:
            try:
                await callback.message.answer_document(user.document, caption="Документ пользователя")
            except Exception:
                await callback.message.answer("⚠️ В поле документа сохранён неверный тип файла.")

    await callback.message.answer(
        "⬆️ Чтобы вернуться в главное меню администратора, нажмите кнопку ниже:",
        reply_markup=admin_back_keyboard(),
    )
    await callback.answer()


# --- Управление курсами (список курсов) ---
@admin_router.callback_query(F.data == "manage_courses")
async def manage_courses(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    async with async_session() as session:
        result = await session.execute(select(Course))
        courses = result.scalars().all()

    if not courses:
        text = "📚 Курсов пока нет."
    else:
        lines = ["📚 Доступные курсы:"]
        for c in courses:
            lines.append(f"• {c.title} — {c.price} руб.")
        text = "\n".join(lines)

    await callback.message.edit_text(
        f"{text}\n\nВыберите действие:",
        reply_markup=manage_courses_keyboard(),
    )
    await callback.answer()


# --- Добавление курса: старт ---
@admin_router.callback_query(F.data == "add_course")
async def add_course_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Нет доступа.", show_alert=True)
        return

    await state.set_state(CourseFSM.title)
    await callback.message.edit_text("🆕 Добавление курса\n\nВведите название курса:")
    await callback.answer()


# --- Добавление курса: название ---
@admin_router.message(CourseFSM.title)
async def add_course_title(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        await state.clear()
        return

    title = message.text.strip()
    if len(title) < 2:
        await message.answer("⚠️ Название слишком короткое. Повторите:")
        return

    await state.update_data(title=title)
    await state.set_state(CourseFSM.description)
    await message.answer("Введите описание курса (до 255 символов):")


# --- Добавление курса: описание ---
@admin_router.message(CourseFSM.description)
async def add_course_description(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        await state.clear()
        return

    desc = (message.text or "").strip()
    # Безопасно обрежем до длины поля в БД
    if len(desc) > 255:
        desc = desc[:255]

    await state.update_data(description=desc)
    await state.set_state(CourseFSM.price)
    await message.answer("Введите цену курса (целое число):")


# --- Добавление курса: цена (валидная)---
@admin_router.message(CourseFSM.price, F.text.regexp(r"^\d+$"))
async def add_course_price_ok(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Нет доступа.")
        await state.clear()
        return

    price = int(message.text)
    data = await state.get_data()

    async with async_session() as session:
        course = Course(
            title=data["title"],
            description=data.get("description") or None,
            price=price,
        )
        session.add(course)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            await message.answer("⚠️ Курс с таким названием уже существует. Операция отменена.")
            await state.clear()
            return

    await message.answer(f"✅ Курс «{data['title']}» добавлен.\n💰 Цена: {price} руб.")
    await state.clear()


# --- Добавление курса: цена (невалидная)---
@admin_router.message(CourseFSM.price)
async def add_course_price_invalid(message: Message):
    await message.answer("⚠️ Цена должна быть целым числом. Повторите ввод:")

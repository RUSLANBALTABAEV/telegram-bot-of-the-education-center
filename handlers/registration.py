"""
Обработчики для регистрации новых пользователей.
"""
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ContentType
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db.models import User
from db.session import async_session
from fsm.registration import Registration
from config.bot_config import ADMIN_ID
from keyboards.reply import main_menu
from i18n.locales import get_text

# Константы валидации
MIN_AGE = 1
MAX_AGE = 120
MIN_NAME_LENGTH = 2

registration_router = Router()


async def get_user_language(user_id: int) -> str:
    """
    Получить язык пользователя из БД.

    Args:
        user_id: Telegram ID пользователя

    Returns:
        Код языка (ru/en/uz), по умолчанию 'ru'
    """
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        return user.language if user and user.language else "ru"


@registration_router.message(Command("register"))
@registration_router.message(
    F.text.in_(["Регистрация", "Registration", "Ro'yxatdan o'tish"])
)
async def start_registration(
    message: types.Message,
    state: FSMContext
) -> None:
    """
    Начать процесс регистрации.

    Args:
        message: Входящее сообщение
        state: FSM контекст
    """
    lang = await get_user_language(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

    if user and user.name and user.is_active:
        await message.answer(
            get_text(
                "already_registered",
                lang,
                name=user.name,
                phone=user.phone or get_text("not_specified", lang)
            )
        )
        await state.clear()
        return

    await message.answer(get_text("enter_name", lang))
    await state.set_state(Registration.name)


@registration_router.message(
    Registration.name,
    F.text.func(lambda text: len(text) >= MIN_NAME_LENGTH)
)
async def process_name(message: types.Message, state: FSMContext) -> None:
    """
    Обработать введённое имя.

    Args:
        message: Сообщение с именем
        state: FSM контекст
    """
    lang = await get_user_language(message.from_user.id)
    await state.update_data(name=message.text.strip())
    await message.answer(get_text("enter_age", lang))
    await state.set_state(Registration.age)


@registration_router.message(Registration.age, F.text.regexp(r"^\d{1,3}$"))
async def process_age(message: types.Message, state: FSMContext) -> None:
    """
    Обработать введённый возраст.

    Args:
        message: Сообщение с возрастом
        state: FSM контекст
    """
    lang = await get_user_language(message.from_user.id)
    age = int(message.text)

    if not (MIN_AGE <= age <= MAX_AGE):
        await message.answer(get_text("invalid_age", lang))
        return

    await state.update_data(age=age)
    await message.answer(get_text("enter_phone", lang))
    await state.set_state(Registration.phone)


@registration_router.message(
    Registration.phone,
    F.text.regexp(r"^\+?\d{10,15}$")
)
async def process_phone(message: types.Message, state: FSMContext) -> None:
    """
    Обработать введённый номер телефона.

    Args:
        message: Сообщение с номером телефона
        state: FSM контекст
    """
    lang = await get_user_language(message.from_user.id)
    phone = message.text.strip()

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.phone == phone)
        )
        phone_owner = result.scalar_one_or_none()

    if phone_owner:
        await message.answer(get_text("phone_exists", lang))
        await state.clear()
        return

    await state.update_data(phone=phone)
    await message.answer(get_text("send_photo", lang))
    await state.set_state(Registration.photo)


@registration_router.message(Registration.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext) -> None:
    """
    Обработать отправленное фото.

    Args:
        message: Сообщение с фото
        state: FSM контекст
    """
    lang = await get_user_language(message.from_user.id)
    await state.update_data(photo=message.photo[-1].file_id)
    await message.answer(get_text("send_document", lang))
    await state.set_state(Registration.document)


@registration_router.message(
    Registration.document,
    F.content_type == ContentType.DOCUMENT
)
async def process_document(
    message: types.Message,
    state: FSMContext
) -> None:
    """
    Обработать отправленный документ и завершить регистрацию.

    Args:
        message: Сообщение с документом
        state: FSM контекст
    """
    lang = await get_user_language(message.from_user.id)
    bot = message.bot
    mime = message.document.mime_type or ""

    if not (mime.startswith("application/pdf") or
            mime.startswith("image/")):
        await message.answer(get_text("invalid_document", lang))
        return

    await state.update_data(document=message.document.file_id)
    data = await state.get_data()

    # Проверяем, есть ли уже пользователь с таким user_id
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == message.from_user.id)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            # Обновляем существующего пользователя
            existing_user.name = data["name"]
            existing_user.age = data["age"]
            existing_user.phone = data["phone"]
            existing_user.photo = data["photo"]
            existing_user.document = data["document"]
            existing_user.is_active = True
            new_user = existing_user
        else:
            # Создаем нового пользователя
            new_user = User(
                user_id=message.from_user.id,
                name=data["name"],
                age=data["age"],
                phone=data["phone"],
                photo=data["photo"],
                document=data["document"],
                language=lang
            )
            session.add(new_user)

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            await message.answer(get_text("user_exists", lang))
            await state.clear()
            return

    # Уведомление админу
    notify_text = get_text(
        "new_user_notification",
        "ru",
        name=new_user.name,
        phone=new_user.phone,
        user_id=new_user.user_id
    )

    try:
        await bot.send_message(ADMIN_ID, notify_text)
        if new_user.photo:
            await bot.send_photo(
                ADMIN_ID,
                new_user.photo,
                caption="📷 Фото пользователя"
            )
        if new_user.document:
            await bot.send_document(
                ADMIN_ID,
                new_user.document,
                caption="📄 Документ пользователя"
            )
    except Exception as e:
        print(f"⚠️ Не удалось уведомить администратора: {e}")

    await message.answer(
        get_text("registration_complete", lang),
        reply_markup=main_menu(message.from_user.id, lang)
    )
    await state.clear()

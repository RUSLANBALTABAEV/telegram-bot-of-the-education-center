from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ContentType
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from db.models import User, async_session
from fsm.registration import Registration

registration_router = Router()


# --- Старт регистрации ---
@registration_router.message(Command("register"))
@registration_router.message(F.text == "Регистрация")
async def start_registration(message: types.Message, state: FSMContext):
    print(f"👉 Запуск регистрации от {message.from_user.id} ({message.from_user.full_name})")

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

    if user:
        await message.answer(
            f"⚠️ Вы уже зарегистрированы.\n"
            f"👤 Имя: {user.name}\n"
            f"📱 Телефон: {user.phone or 'не указан'}"
        )
        await state.clear()
        return

    await message.answer("👉 Начинаем регистрацию. Введите ваше имя:")
    await state.set_state(Registration.name)


# --- Имя ---
@registration_router.message(Registration.name, F.text.len() >= 2)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Введите ваш возраст (числом):")
    await state.set_state(Registration.age)


@registration_router.message(Registration.name)
async def invalid_name(message: types.Message):
    await message.answer("⚠️ Имя должно содержать минимум 2 символа.")


# --- Возраст ---
@registration_router.message(Registration.age, F.text.regexp(r"^\d{1,3}$"))
async def process_age(message: types.Message, state: FSMContext):
    age = int(message.text)
    if not (1 <= age <= 120):
        await message.answer("⚠️ Укажите реальный возраст (1–120). Попробуйте ещё раз.")
        return
    await state.update_data(age=age)
    await message.answer("Введите ваш номер телефона (в формате +79998887766):")
    await state.set_state(Registration.phone)


@registration_router.message(Registration.age)
async def invalid_age(message: types.Message):
    await message.answer("⚠️ Возраст должен быть числом. Пример: 25")


# --- Телефон ---
PHONE_RE = r"^\+?\d{10,15}$"

@registration_router.message(Registration.phone, F.text.regexp(PHONE_RE))
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()

    async with async_session() as session:
        result = await session.execute(select(User).where(User.phone == phone))
        phone_owner = result.scalar_one_or_none()

    if phone_owner:
        await message.answer(
            "⚠️ Этот номер уже зарегистрирован.\n"
            "Если это ваш аккаунт — используйте /login."
        )
        await state.clear()
        return

    await state.update_data(phone=phone)
    await message.answer("Отправьте вашу фотографию (как фото, не файлом):")
    await state.set_state(Registration.photo)


@registration_router.message(Registration.phone)
async def invalid_phone(message: types.Message):
    await message.answer("⚠️ Неверный формат номера. Пример: +79998887766")


# --- Фото ---
@registration_router.message(Registration.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(photo=file_id)
    await message.answer("Теперь отправьте 📄 документ (PDF или изображение как файл).")
    await state.set_state(Registration.document)


@registration_router.message(Registration.photo)
async def invalid_photo(message: types.Message):
    await message.answer("⚠️ Отправьте именно фото, не текст и не стикер.")


# --- Документ (PDF/JPG/PNG как файл) ---
@registration_router.message(
    Registration.document,
    F.content_type == ContentType.DOCUMENT
)
async def process_document(message: types.Message, state: FSMContext):
    mime = message.document.mime_type or ""
    if mime.startswith("application/pdf") or mime.startswith("image/"):
        await state.update_data(document=message.document.file_id)
    else:
        await message.answer("⚠️ Допустимы только PDF или изображения (JPG/JPEG/PNG).")
        return

    data = await state.get_data()

    new_user = User(
        user_id=message.from_user.id,
        name=data["name"],
        age=data["age"],
        phone=data["phone"],
        photo=data["photo"],
        document=data["document"],
    )

    async with async_session() as session:
        try:
            session.add(new_user)
            await session.commit()
        except IntegrityError:
            await session.rollback()
            await message.answer("⚠️ Этот номер уже есть в системе. Используйте /login.")
            await state.clear()
            return

    await message.answer("✅ Регистрация завершена! Добро пожаловать 🎉")
    await state.clear()


@registration_router.message(Registration.document)
async def invalid_document(message: types.Message):
    await message.answer("⚠️ Пришлите документ PDF или изображение как файл (JPG/JPEG/PNG).")

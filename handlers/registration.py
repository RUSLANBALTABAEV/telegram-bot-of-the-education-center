from aiogram import Router, F, types, Bot
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

registration_router = Router()



@registration_router.message(Command("register"))
@registration_router.message(F.text == "Регистрация")
async def start_registration(message: types.Message, state: FSMContext):
    print(f"👉 Запуск регистрации от {message.from_user.id} ({message.from_user.full_name})")

    async with async_session() as session:
        
        result_count = await session.execute(select(User))
        total_users = len(result_count.scalars().all())

        if total_users >= 100:
            await message.answer(
                "⚠️ Достигнут лимит регистрации (100 пользователей).\n"
                "Новые пользователи не могут быть зарегистрированы."
            )
            return

        
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



@registration_router.message(Registration.name, F.text.len() >= 2)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Введите ваш возраст (числом):")
    await state.set_state(Registration.age)


@registration_router.message(Registration.name)
async def invalid_name(message: types.Message):
    await message.answer("⚠️ Имя должно содержать минимум 2 символа.")



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



@registration_router.message(Registration.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(photo=file_id)
    await message.answer("Теперь отправьте 📄 документ (PDF или изображение как файл).")
    await state.set_state(Registration.document)


@registration_router.message(Registration.photo)
async def invalid_photo(message: types.Message):
    await message.answer("⚠️ Отправьте именно фото, не текст и не стикер.")



@registration_router.message(
    Registration.document,
    F.content_type == ContentType.DOCUMENT
)
async def process_document(message: types.Message, state: FSMContext, bot: Bot):
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

    # уведомление админа
    notify_text = (
        f"👤 Новый пользователь зарегистрирован!\n\n"
        f"Имя: {new_user.name}\n"
        f"Возраст: {new_user.age}\n"
        f"Телефон: {new_user.phone}\n"
        f"DB id: {new_user.id}\n"
        f"TG id: {new_user.user_id}"
    )

    # отправляем текст и файлы администратору
    try:
        await bot.send_message(ADMIN_ID, notify_text)
        if new_user.photo:
            await bot.send_photo(ADMIN_ID, new_user.photo, caption="📷 Фото пользователя")
        if new_user.document:
            await bot.send_document(ADMIN_ID, new_user.document, caption="📄 Документ пользователя")
    except Exception:
        # если отправка админу не удалась — просто логируем (в консоль) и продолжаем
        print("⚠️ Не удалось уведомить администратора (отправка файлов/сообщения).")

    await message.answer("✅ Регистрация завершена! Добро пожаловать 🎉", reply_markup=main_menu(message.from_user.id))
    await state.clear()


@registration_router.message(Registration.document)
async def invalid_document(message: types.Message):
    await message.answer("⚠️ Пришлите документ PDF или изображение как файл (JPG/JPEG/PNG).")

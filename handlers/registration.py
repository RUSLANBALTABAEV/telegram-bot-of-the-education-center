from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from db.models import User, async_session
from fsm.registration import Registration

registration_router = Router()

@registration_router.message(Command("register"))
@registration_router.message(F.text == "Регистрация")
async def start_registration(message: types.Message, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == message.from_user.id))
        user = result.scalar_one_or_none()

    if user:
        await message.answer("✅ Вы уже зарегистрированы.")
    else:
        await message.answer("Введите ваше имя:")
        await state.set_state(Registration.name)


@registration_router.message(Registration.name, F.text)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите ваш возраст:")
    await state.set_state(Registration.age)


@registration_router.message(Registration.age, F.text.regexp(r"^\d{1,3}$"))
async def process_age(message: types.Message, state: FSMContext):
    await state.update_data(age=int(message.text))
    await message.answer("Введите ваш номер телефона (в формате +79998887766):")
    await state.set_state(Registration.phone)


@registration_router.message(Registration.phone, F.text.regexp(r"^\+?\d{10,15}$"))
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("Отправьте вашу фотографию:")
    await state.set_state(Registration.photo)


@registration_router.message(Registration.photo, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(photo=file_id)

    data = await state.get_data()

    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == message.from_user.id))
        user = result.scalar_one_or_none()

        if user:
            await message.answer("⚠️ Вы уже зарегистрированы.")
        else:
            new_user = User(
                user_id=message.from_user.id,
                name=data["name"],
                age=data["age"],
                phone=data["phone"],
                photo=data["photo"],
            )
            session.add(new_user)
            await session.commit()
            await message.answer("✅ Регистрация завершена!")

    await state.clear()

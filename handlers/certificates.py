from aiogram import Router, F, types
from sqlalchemy import select
from db.models import Certificate, User
from db.session import async_session
from config.bot_config import ADMIN_ID
from keyboards.reply import main_menu
from i18n.locales import get_text

certificates_router = Router()

async def get_user_language(user_id: int) -> str:
    """Получить язык пользователя из БД"""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        return user.language if user and user.language else "ru"

@certificates_router.message(F.text.in_(["Сертификаты", "Certificates", "Sertifikatlar"]))
async def show_all_certificates(message: types.Message):
    lang = await get_user_language(message.from_user.id)
    
    if message.from_user.id != ADMIN_ID:
        await message.answer(get_text("no_access", lang))
        return

    async with async_session() as session:
        result = await session.execute(select(Certificate))
        certificates = result.scalars().all()

        if not certificates:
            await message.answer(get_text("no_certificates", lang), reply_markup=main_menu(message.from_user.id, lang))
            return

        for cert in certificates:
            user = await session.get(User, cert.user_id)
            user_name = user.name if user else str(cert.user_id)
            text = f"🏅 {cert.title}\n{get_text('user', lang, name=user_name)}"
            await message.answer(text)

            if cert.file_id:
                try:
                    await message.answer_document(cert.file_id, caption=get_text("certificate_file", lang))
                except Exception:
                    await message.answer(get_text("certificate_file_error", lang))

@certificates_router.message(F.text.in_(["Мои сертификаты", "My Certificates", "Mening sertifikatlarim"]))
async def show_my_certificates(message: types.Message):
    lang = await get_user_language(message.from_user.id)
    
    async with async_session() as session:
        result_user = await session.execute(
            select(User).where(User.user_id == message.from_user.id)
        )
        user = result_user.scalar_one_or_none()

        if not user:
            await message.answer(
                get_text("not_registered", lang),
                reply_markup=main_menu(message.from_user.id, lang)
            )
            return

        result = await session.execute(
            select(Certificate).where(Certificate.user_id == user.id)
        )
        certificates = result.scalars().all()

    if not certificates:
        await message.answer(get_text("no_my_certificates", lang), reply_markup=main_menu(message.from_user.id, lang))
        return

    for cert in certificates:
        await message.answer(f"🏅 {cert.title}")

        if cert.file_id:
            try:
                await message.answer_document(cert.file_id, caption=get_text("your_certificate", lang))
            except Exception:
                await message.answer(get_text("certificate_file_error", lang))

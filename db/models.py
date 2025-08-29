from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column
from sqlalchemy import BigInteger, String, Integer
from sqlalchemy.ext.asyncio import AsyncAttrs


# Базовый класс моделей
class Base(AsyncAttrs, DeclarativeBase):
    pass


# Модель пользователя
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)  # Telegram user_id
    name: Mapped[str] = mapped_column(String(100))  # имя
    age: Mapped[int] = mapped_column(Integer, nullable=True)  # возраст
    phone: Mapped[str] = mapped_column(String(20), nullable=True)  # телефон
    photo: Mapped[str] = mapped_column(String, nullable=True)  # путь/ссылка на фото


# Создание таблиц
async def create_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

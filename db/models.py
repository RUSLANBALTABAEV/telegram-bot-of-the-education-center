from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, Date, Boolean, Text, select
from sqlalchemy.ext.asyncio import AsyncAttrs
from datetime import date
from db.session import async_session


# Базовый класс
class Base(AsyncAttrs, DeclarativeBase):
    pass


# 👤 Пользователи
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)  # Telegram ID
    name: Mapped[str] = mapped_column(String(100), nullable=True)

    age: Mapped[int] = mapped_column(Integer, nullable=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=True)
    photo: Mapped[str] = mapped_column(String(255), nullable=True)      # file_id фото
    document: Mapped[str] = mapped_column(String(255), nullable=True)   # file_id документа

    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    certificates: Mapped[list["Certificate"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )


# 📚 Курсы
class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    start_date: Mapped[date] = mapped_column(Date, nullable=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)

    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan"
    )


# 📝 Записи на курсы
class Enrollment(Base):
    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))

    start_date: Mapped[date] = mapped_column(Date, nullable=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="enrollments")
    course: Mapped["Course"] = relationship(back_populates="enrollments")


# 🎓 Сертификаты
class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(100))
    file_id: Mapped[str] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship(back_populates="certificates")


# 🚀 Создание таблиц
async def create_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# 🌱 Сидинг курсов (заполнение дефолтными)
async def seed_courses():
    async with async_session() as session:
        result = await session.execute(select(Course))
        courses = result.scalars().all()

        if not courses:
            default_courses = [
                Course(
                    title="Python для начинающих",
                    description="Основы синтаксиса, ООП, работа с файлами",
                    price=10000
                ),
                Course(
                    title="Веб-разработка",
                    description="HTML, CSS, JavaScript, основы backend",
                    price=12000
                ),
                Course(
                    title="Java с нуля",
                    description="ООП, коллекции, основы Spring",
                    price=15000
                ),
                Course(
                    title="Data Science",
                    description="Pandas, NumPy, машинное обучение",
                    price=20000
                ),
            ]
            session.add_all(default_courses)
            await session.commit()

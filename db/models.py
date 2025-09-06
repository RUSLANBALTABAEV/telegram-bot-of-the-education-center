from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column, relationship
from sqlalchemy import BigInteger, String, Integer, ForeignKey, Date, Boolean, select
from sqlalchemy.ext.asyncio import AsyncAttrs
from datetime import date
from db.session import async_session
from datetime import date

class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=True)

    enrollments = relationship(
        "Enrollment",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    certificates = relationship(
        "Certificate",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    start_date: Mapped[date] = mapped_column(Date, nullable=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)

    enrollments = relationship(
        "Enrollment",
        back_populates="course",
        cascade="all, delete-orphan"
    )


class Enrollment(Base):
    __tablename__ = "enrollments"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))

    user = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")


class Certificate(Base):
    __tablename__ = "certificates"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(100))
    file_id: Mapped[str] = mapped_column(String(255), nullable=True)

    user = relationship("User", back_populates="certificates")


async def create_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_courses(engine):
    async with async_session() as session:
        result = await session.execute(select(Course))
        courses = result.scalars().all()
        if not courses:
            default_courses = [
                Course(title="Python для начинающих", description="Основы синтаксиса, ООП, работа с файлами", price=10000),
                Course(title="Веб-разработка", description="HTML, CSS, JavaScript, основы backend", price=12000),
                Course(title="Java с нуля", description="ООП, коллекции, основы Spring", price=15000),
                Course(title="Data Science", description="Pandas, NumPy, машинное обучение", price=20000),
            ]
            session.add_all(default_courses)
            await session.commit()

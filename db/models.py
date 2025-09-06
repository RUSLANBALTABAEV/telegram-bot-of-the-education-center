from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column, relationship
from sqlalchemy import BigInteger, String, Integer, ForeignKey, Date, Boolean, select
from sqlalchemy.ext.asyncio import AsyncAttrs
from db.session import async_session
from datetime import date

class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=True)

    name: Mapped[str] = mapped_column(String(100))
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=True, unique=True)
    photo: Mapped[str] = mapped_column(String, nullable=True)
    document: Mapped[str] = mapped_column(String, nullable=True)

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
    
    courses = relationship("Course", secondary="enrollments", viewonly=True)


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    enrollments = relationship(
        "Enrollment",
        back_populates="course",
        cascade="all, delete-orphan"
    )


class Enrollment(Base):
    __tablename__ = "enrollments"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))

    start_date: Mapped[date] = mapped_column(Date, nullable=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")


class Certificate(Base):
    __tablename__ = "certificates"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    file_id: Mapped[str] = mapped_column(String)
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
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

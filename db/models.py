from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column, relationship
from sqlalchemy import BigInteger, String, Integer, ForeignKey, Table, Column, select
from sqlalchemy.ext.asyncio import AsyncAttrs
from db.session import async_session, engine

class Base(AsyncAttrs, DeclarativeBase):
    pass

user_course = Table(
    "user_course",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("course_id", ForeignKey("courses.id"), primary_key=True),
)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(100))
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=True, unique=True)
    photo: Mapped[str] = mapped_column(String, nullable=True)
    document: Mapped[str] = mapped_column(String, nullable=True)

    courses = relationship("Course", secondary=user_course, back_populates="users")
    certificates = relationship("Certificate", back_populates="user")

class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    users = relationship("User", secondary=user_course, back_populates="courses")

class Certificate(Base):
    __tablename__ = "certificates"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    file_id: Mapped[str] = mapped_column(String)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
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

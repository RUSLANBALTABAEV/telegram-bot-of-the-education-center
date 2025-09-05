import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import User, Course, Certificate, Enrollment
from db.session import async_session

async def main():
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.enrollments).selectinload(Enrollment.course),
                selectinload(User.certificates),
            )
        )
        users = result.scalars().all()

        for user in users:
            print(f"👤 Пользователь: {user.name} ({user.phone}) [tg_id={user.user_id}, db_id={user.id}]")

            if user.enrollments:
                print("  📚 Курсы:")
                for enr in user.enrollments:
                    course = enr.course
                    status = "✅ Завершён" if enr.is_completed else f"📅 До {enr.end_date or 'не указано'}"
                    print(f"    ▫️ {course.title} — {status}")
            else:
                print("  📚 Курсы отсутствуют")

            if user.certificates:
                print("  🏅 Сертификаты:")
                for cert in user.certificates:
                    print(f"    ▫️ {cert.title}")
            else:
                print("  🏅 Сертификаты отсутствуют")

            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())

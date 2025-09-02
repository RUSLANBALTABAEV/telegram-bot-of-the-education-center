import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import async_session, User, Course, Certificate

async def main():
    async with async_session() as session:
        result = await session.execute(
            select(User).options(selectinload(User.courses), selectinload(User.certificates))
        )
        users = result.scalars().all()

        for user in users:
            print(f"👤 Пользователь: {user.name} ({user.phone})")
            if user.courses:
                print("  📚 Курсы:")
                for course in user.courses:
                    print(f"    ▫️ {course.title}")
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

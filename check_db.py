import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.models import async_session, User, Course

async def main():
    async with async_session() as session:
        result = await session.execute(
            select(User).options(selectinload(User.courses))
        )
        users = result.scalars().all()

        for user in users:
            print(f"Пользователь: {user.name} ({user.phone})")
            if user.courses:
                print("  Курсы:")
                for course in user.courses:
                    print(f"    ▫️ {course.title}")
            else:
                print("  Курсы отсутствуют")
            print("-" * 30)

if __name__ == "__main__":
    asyncio.run(main())

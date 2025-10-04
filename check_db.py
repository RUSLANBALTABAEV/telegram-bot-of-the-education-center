# ============ check_db.py ============
"""
Утилита для проверки содержимого базы данных.
Отображает информацию о пользователях, их курсах и сертификатах.
"""
import asyncio

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.models import User, Course, Certificate, Enrollment
from db.session import async_session


async def main() -> None:
    """
    Главная функция для проверки базы данных.

    Выводит информацию о всех пользователях, включая:
    - Имя, телефон, ID
    - Записи на курсы
    - Полученные сертификаты
    """
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.enrollments).selectinload(
                    Enrollment.course
                ),
                selectinload(User.certificates),
            )
        )
        users = result.scalars().all()

        for user in users:
            print(
                f"👤 Пользователь: {user.name} ({user.phone}) "
                f"[tg_id={user.user_id}, db_id={user.id}]"
            )

            if user.enrollments:
                print("  📚 Курсы:")
                for enr in user.enrollments:
                    course = enr.course
                    if enr.is_completed:
                        status = "✅ Завершён"
                    else:
                        end_date_str = (
                            enr.end_date.strftime("%d.%m.%Y")
                            if enr.end_date
                            else "не указано"
                        )
                        status = f"📅 До {end_date_str}"
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

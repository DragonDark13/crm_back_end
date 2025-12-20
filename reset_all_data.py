from sqlalchemy import text
from postgreSQLConnect import engine
from models import Base


def reset_database():
    with engine.connect() as conn:
        # Видалення всієї схеми, разом з усіма таблицями, індексами, функціями
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        print("✅ Схема 'public' успішно видалена та створена заново.")

    # Створення таблиць з ORM
    Base.metadata.create_all(engine)
    print("✅ Всі таблиці успішно створено заново.")


if __name__ == "__main__":
    reset_database()

from sqlalchemy import text
from postgreSQLConnect import engine
from models import Base


def reset_database():
    # PostgreSQL виконує DDL транзакційно: у разі помилки попередня схема відновиться.
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        Base.metadata.create_all(conn)

    print("✅ Схема 'public' успішно створена заново.")


if __name__ == "__main__":
    reset_database()

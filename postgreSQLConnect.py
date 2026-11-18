import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from models import db

load_dotenv()

# Налаштування підключення до PostgreSQL
DATABASE_URI = os.getenv("DATABASE_URL")
if not DATABASE_URI:
    raise RuntimeError("DATABASE_URL environment variable is required")

# Створення двигуна (engine)
engine = create_engine(
    DATABASE_URI,
    echo=False,  # SQL query logging is disabled by default
    pool_size=25,  # Розмір пулу з'єднань
    max_overflow=20,  # Додаткові з'єднання при навантаженні
    pool_timeout=30  # Час очікування перед помилкою
)


def test_connection():
    try:
        with engine.connect() as connection:
            print("[OK] Зʼєднання з базою даних успішне!")
            return True
    except Exception as e:
        print(f"[ERROR] Помилка підключення до бази: {e}")
        return False


# Створення сесії
Session = sessionmaker(bind=engine)
db_session = scoped_session(Session)





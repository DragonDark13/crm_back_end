from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from app import app
from models import db

# Налаштування підключення до PostgreSQL
DATABASE_URI = "postgresql://postgres:admin@localhost:5432/shop_crm_post"  # Замініть на свої дані

# Створення двигуна (engine)
engine = create_engine(
    DATABASE_URI,
    echo=True,  # Логи SQL-запитів у консоль
    pool_size=25,  # Розмір пулу з'єднань
    max_overflow=20,  # Додаткові з'єднання при навантаженні
    pool_timeout=30  # Час очікування перед помилкою
)


def test_connection():
    try:
        with engine.connect() as connection:
            print("✅ Підключення до бази даних успішне!")
            return True
    except Exception as e:
        print(f"❌ Помилка підключення до бази даних: {e}")
        return False


# Створення сесії
Session = sessionmaker(bind=engine)
db_session = scoped_session(Session)


# Функція ініціалізації бази (створює таблиці, якщо вони не існують)
def init_db():
    """Функція ініціалізації бази даних"""
    with app.app_context():  # Додаємо контекст застосунку
        db.create_all()


# Виконати перевірку
if test_connection():
    init_db()

# Викликаємо ініціалізацію БД тільки якщо цей файл виконується напряму
if __name__ == "__main__":
    init_db()

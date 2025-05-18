from sqlalchemy import inspect

from database import engine
from models import Base


def check_all_tables_exist():
    """
    Перевіряє, чи всі таблиці з моделей у базі даних створені.
    Повертає список відсутніх таблиць.
    """
    # Отримати список таблиць із моделей
    defined_tables = set(Base.metadata.tables.keys())

    # Отримати список існуючих таблиць у базі даних
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    # Визначити, які таблиці відсутні
    missing_tables = defined_tables - existing_tables

    if missing_tables:
        print(f"Відсутні таблиці: {missing_tables}")
    else:
        print("Усі таблиці присутні в базі даних.")

    return missing_tables


def ensure_all_tables_exist():
    """
    Перевіряє наявність усіх таблиць і створює відсутні.
    """
    missing_tables = check_all_tables_exist()
    if missing_tables:
        print("Створення відсутніх таблиць...")
        Base.metadata.create_all(bind=engine)
        print("Всі таблиці успішно створені.")


ensure_all_tables_exist()

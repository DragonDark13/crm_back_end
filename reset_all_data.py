# Видалення таблиць (якщо потрібно)
from postgreSQLConnect import engine
from models import Base

Base.metadata.drop_all(engine)

# Створення таблиць заново
Base.metadata.create_all(engine)
# Створення сесії
from sqlalchemy.orm import sessionmaker

from app import engine
from services.product_service import delete_all_products

Session = sessionmaker(bind=engine)
session = Session()

# Видалення всіх товарів
delete_all_products(session)

# Закриття сесії
session.close()
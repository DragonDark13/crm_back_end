from datetime import datetime
import logging
from sqlalchemy.exc import IntegrityError

from models import  Category, Supplier, Product, Base

# Ініціалізуємо базу даних
from database import db_session

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Очищення таблиць
def reset_database():
    """Видаляє всі таблиці та створює їх заново."""
    try:
        logging.info("Dropping all tables...")
        Base.metadata.drop_all(bind=db_session.get_bind())  # Видалення всіх таблиць
        logging.info("Creating all tables...")
        Base.metadata.create_all(bind=db_session.get_bind())  # Створення всіх таблиць
        logging.info("Database reset complete.")
    except Exception as e:
        logging.error(f"Error resetting database: {e}")


reset_database()

# Create initial categories
categories = ['Сувеніри', 'Гаррі Поттер', 'Володар Перснів']

for category_name in categories:
    existing_category = db_session.query(Category).filter_by(name=category_name).first()
    if not existing_category:
        category = Category(name=category_name)
        db_session.add(category)
        db_session.commit()

db_session.commit()

data1 = [
    {"name": "Шоколад", "quantity": 3, "selling_price_per_item": 280},
    {"name": "Грифіндорський шарф", "quantity": 1, "selling_price_per_item": 1350},
    {"name": "Паличка Волдеморта", "quantity": 1, "selling_price_per_item": 810},
    {"name": "Паличка Аластора Грюма", "quantity": 1, "selling_price_per_item": 760},
    {"name": "Набір для каліграфії", "quantity": 1, "selling_price_per_item": 350},
    {"name": "Світильник 'Сова'", "quantity": 1, "selling_price_per_item": 600},
    {"name": "Чашка учня Гогвордсу", "quantity": 2, "selling_price_per_item": 300},
    {"name": "Чай 'Амортензія'", "quantity": 2, "selling_price_per_item": 60},
    {"name": "Набір шкарпеток ГП 36-42р.", "quantity": 6, "selling_price_per_item": 70},
    {"name": "Набір шкарпеток ГП 41-45р.", "quantity": 6, "selling_price_per_item": 70},
    {"name": "Карта Мародерів", "quantity": 2, "selling_price_per_item": 375},
    {"name": "Драконячі яйця", "quantity": 5, "selling_price_per_item": 25},
    {"name": "Ручки що ростуть", "quantity": 4, "selling_price_per_item": 55},
    {"name": "Олівці що ростуть", "quantity": 5, "selling_price_per_item": 45},
    {"name": "Набір з олівців що ростуть (12 шт)", "quantity": 1, "selling_price_per_item": 450},
    {"name": "Окуляри Гаррі Поттера", "quantity": 4, "selling_price_per_item": 65},
    {"name": "Ложки дерев'яні", "quantity": 2, "selling_price_per_item": 135},
    {"name": "Ложка дерев'яна з чаєм", "quantity": 1, "selling_price_per_item": 170},
    {"name": "Диплом про закінчення Хогвардса в рамці", "quantity": 3, "selling_price_per_item": 240},
    {"name": "Пазл Хатинка Гегріда без рамці", "quantity": 5, "selling_price_per_item": 360},
    {"name": "Записник учня Гогвордсу", "quantity": 5, "selling_price_per_item": 65},
    {"name": "Диплом про закінчення Гогвордсу", "quantity": 5, "selling_price_per_item": 240},
    {"name": "Лист з Гогвордсу", "quantity": 5, "selling_price_per_item": 30},
    {"name": "Квиток на автобус", "quantity": 5, "selling_price_per_item": 45},
    {"name": "Квиток на Гогвардс Експресс", "quantity": 2, "selling_price_per_item": 45},
    {"name": "Готовий набір лист з Гогвордсу", "quantity": 2, "selling_price_per_item": 200},
    {"name": "Гребінець", "quantity": 1, "selling_price_per_item": 350},
    {"name": "Кулон Маховик Часу", "quantity": 1, "selling_price_per_item": 160},
    {"name": "Кулон Платформа 9 3/4", "quantity": 2, "selling_price_per_item": 150},
    {"name": "Брелок Гогвордс", "quantity": 1, "selling_price_per_item": 140},
    {"name": "Брелок Гафлпафф", "quantity": 1, "selling_price_per_item": 140},
    {"name": "Чокер синій", "quantity": 1, "selling_price_per_item": 290},
    {"name": "Газета 'Щоденний віщун'", "quantity": 5, "selling_price_per_item": 120},
    {"name": "Свічки що вмикаются дотиком", "quantity": 8, "selling_price_per_item": 145},
    {"name": "Свічка Доббі", "quantity": 1, "selling_price_per_item": 400},
    {"name": "Свічка Розподільчий капелюх", "quantity": 1, "selling_price_per_item": 90},
    {"name": "Свічка Вежа Гогвордсу", "quantity": 2, "selling_price_per_item": 285},
    {"name": "Свічка Мандрагора в Горщику", "quantity": 1, "selling_price_per_item": 400},
    {"name": "Свічка Дамблдор", "quantity": 1, "selling_price_per_item": 210},
    {"name": "Свічка Снейп", "quantity": 1, "selling_price_per_item": 285},
    {"name": "Свічка Макгонагал", "quantity": 1, "selling_price_per_item": 150},
    {"name": "Карта Гогвордс", "quantity": 1, "selling_price_per_item": 255},
    {"name": "Рюкзак", "quantity": 1, "selling_price_per_item": 1950}
]


# Функція для завантаження продуктів у базу даних
def load_products_to_db(data):
    """Створює новий товар та обробляє його закупівлю."""
    logging.info(f"Array '{data}'.")

    for product_data in data:
        logging.info(f"Processing product '{product_data}'.")

        # Дефолтна категорія на випадок відсутності категорії у даних
        default_category = db_session.query(Category).filter_by(name='Сувеніри').first()
        if not default_category:
            default_category = Category(name='Сувеніри')
            db_session.add(default_category)
            db_session.commit()

        # Перевірка наявності продукту
        existing_product = db_session.query(Product).filter_by(name=product_data['name']).first()
        if existing_product:
            logging.warning(f"Product '{product_data['name']}' already exists. Skipping.")
            continue

        # Перевірка та обробка постачальника
        supplier_name = product_data.get('supplier_name', "Unknown Supplier")
        supplier = db_session.query(Supplier).filter_by(name=supplier_name).first()
        if not supplier:
            supplier = Supplier(name=supplier_name)
            db_session.add(supplier)
            db_session.commit()

        # Перевірка кількості
        total_quantity = product_data.get('quantity', 0)
        if total_quantity < 0:
            logging.warning(f"Invalid quantity for '{product_data['name']}'. Skipping product.")
            continue

        available_quantity = product_data.get('quantity', 0)
        if available_quantity < 0:
            logging.warning(f"Invalid quantity for '{product_data['name']}'. Skipping product.")
            continue

        try:
            # Створення нового продукту
            product = Product(
                name=product_data['name'],
                supplier=supplier,
                total_quantity=total_quantity,
                available_quantity=available_quantity,
                selling_price_per_item=product_data.get('selling_price_per_item', 0),
                created_date=datetime.now()
            )

            # Додавання дефолтної категорії до продукту
            product.categories.append(default_category)

            db_session.add(product)
            db_session.commit()
            logging.info(f"Product '{product_data['name']}' successfully added.")

        except IntegrityError as e:
            logging.error(f"Error adding product '{product_data['name']}': {e}")
            db_session.rollback()  # Откат змін у разі помилки
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            db_session.rollback()  # Откат змін у разі помилки

    logging.info("All products have been processed.")


# Виклик функції
load_products_to_db(data1)

from sqlalchemy import inspect

# Функція для завантаження продуктів у базу даних
from database import db_session, engine
from models import Product, Supplier, Base

from datetime import datetime
from decimal import Decimal
import csv
from sqlalchemy.exc import IntegrityError
from models import Product, Supplier, PurchaseHistory, StockHistory
from database import db_session


def ensure_table_exists(table_name):
    """
    Перевіряє, чи існує таблиця у базі даних. Якщо ні — створює її.
    :param table_name: Назва таблиці.
    """
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        print(f"Таблиця '{table_name}' не знайдена. Створення...")
        Base.metadata.create_all(bind=engine)
        print(f"Таблиця '{table_name}' успішно створена.")


def load_products_from_csv(file_path, created_date):
    """
    Завантажує продукти з CSV-файлу до бази даних.

    Якщо товар вже існує, то оновлює його кількість як надходження.

    :param file_path: Шлях до CSV-файлу.
    :param created_date: Дата створення або надходження продуктів (тип datetime).
    """
    with open(file_path, mode='r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            # Отримання даних з рядка CSV
            name = row['Наименование'].strip()
            supplier_name = row['Поставщик'].strip()
            quantity = int(row['Количество'].split()[0])
            total_price = Decimal(row['Стоимость за количество'].replace(',', '.'))
            price_per_item = Decimal(row['Стоимость за 1 шт'].replace(',', '.'))

            ensure_table_exists('suppliers')

            # Створення або отримання постачальника
            supplier = db_session.query(Supplier).filter_by(name=supplier_name).first()
            if not supplier:
                supplier = Supplier(name=supplier_name)
                db_session.add(supplier)
                db_session.commit()

            # Перевірка існування продукту
            product = db_session.query(Product).filter_by(name=name).first()
            if product:
                try:
                    # Оновлення наявної кількості як надходження
                    product.total_quantity += quantity
                    product.available_quantity += quantity
                    product.purchase_price_per_item = price_per_item
                    product.purchase_total_price += total_price
                    product.updated_date = created_date
                    db_session.commit()
                    print(f"Надходження '{name}' успішно зареєстровано.")

                    # Create PurchaseHistory record for update
                    purchase_history = PurchaseHistory(
                        product_id=product.id,
                        purchase_price_per_item=price_per_item,
                        purchase_total_price=total_price,
                        supplier_id=supplier.id,
                        quantity_purchase=quantity,
                        purchase_date=created_date
                    )
                    db_session.add(purchase_history)

                    # Create StockHistory record for update
                    stock_history = StockHistory(
                        product_id=product.id,
                        change_amount=quantity,
                        change_type='update',  # Indicating that this is an update
                        timestamp=created_date
                    )
                    db_session.add(stock_history)
                    db_session.commit()

                except Exception as e:
                    db_session.rollback()
                    print(f"Помилка оновлення продукту '{name}': {e}")
                continue

            try:
                # Додавання нового продукту
                product = Product(
                    name=name,
                    supplier=supplier,
                    total_quantity=quantity,
                    available_quantity=quantity,
                    purchase_total_price=total_price,
                    purchase_price_per_item=price_per_item,
                    created_date=created_date
                )
                db_session.add(product)
                db_session.commit()
                print(f"Продукт '{name}' успішно додано.")

                # Create PurchaseHistory record for new product
                purchase_history = PurchaseHistory(
                    product_id=product.id,
                    purchase_price_per_item=price_per_item,
                    purchase_total_price=total_price,
                    supplier_id=supplier.id,
                    quantity_purchase=quantity,
                    purchase_date=created_date
                )
                db_session.add(purchase_history)

                # Create StockHistory record for new product
                stock_history = StockHistory(
                    product_id=product.id,
                    change_amount=quantity,
                    change_type='create',  # Indicating this is a new product
                    timestamp=created_date
                )
                db_session.add(stock_history)

                db_session.commit()

            except IntegrityError as e:
                db_session.rollback()
                print(f"Помилка додавання продукту '{name}': {e}")
            except Exception as e:
                db_session.rollback()
                print(f"Несподівана помилка: {e}")


# Список з шляхами до CSV-файлів та відповідними датами
files_data = [
    # ('csv/15.02.2023.csv', "15.02.2023"),
    # ('csv/15.03.2023.csv', "15.03.2023"),
    # ('csv/15.05.2023.csv', "15.05.2023"),
    # ('csv/15.06.2023.csv', "15.06.2023"),
    # ('csv/15.08.2023.csv', "15.08.2023"),
    # ('csv/15.09.2024.csv', "15.09.2024"),
    # ('csv/15.12.2024.csv', "15.12.2024"),
    # ('csv/15.01.2025.csv', "15.01.2025")
]

# Цикл для виклику функції load_products_from_csv для кожного файлу
for file_path, date_str in files_data:
    created_date = datetime.strptime(date_str, "%d.%m.%Y")
    load_products_from_csv(file_path, created_date)

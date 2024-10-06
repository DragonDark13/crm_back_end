from datetime import datetime
import logging

from peewee import Model, CharField, FloatField, IntegerField, SqliteDatabase, IntegrityError

# Ініціалізуємо базу даних
from models import StockHistory, PurchaseHistory, SaleHistory, ProductCategory, Category, Supplier, Product

db = SqliteDatabase('shop_crm.db')

# Створюємо таблицю в базі даних
db.connect()
db.drop_tables([Product, StockHistory, PurchaseHistory, SaleHistory, ProductCategory, Category, Supplier])
db.create_tables([Product, StockHistory, PurchaseHistory, SaleHistory, ProductCategory, Category, Supplier])

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Приклад додавання товарів
data = [
    {"name": "Палочка Воландеморта", "supplier_name": "skladoptom.com.ua", "quantity": 0, "purchase_total_price": 507.6,
     "purchase_price_per_item": 507.6},
    {"name": "Палочка Грюма", "supplier_name": "skladoptom.com.ua", "quantity": 0, "purchase_total_price": 507.6,
     "purchase_price_per_item": 507.6},
    {"name": "Брелок с гербом Пуффендуя", "supplier_name": "skladoptom.com.ua", "quantity": 0,
     "purchase_total_price": 65.49,
     "purchase_price_per_item": 65.49},
    {"name": "Брелок с гербом Когтевран", "supplier_name": "misteria.prom.ua", "quantity": 0,
     "purchase_total_price": 86,
     "purchase_price_per_item": 86},
    {"name": "Брелок Дары Смерти", "supplier_name": "misteria.prom.ua", "quantity": 0, "purchase_total_price": 81,
     "purchase_price_per_item": 81},
    {"name": "Брелок Грифиндор круглый", "supplier_name": "misteria.prom.ua", "quantity": 0, "purchase_total_price": 60,
     "purchase_price_per_item": 60},
    {"name": "Брелок Слизерин круглый", "supplier_name": "misteria.prom.ua", "quantity": 0, "purchase_total_price": 60,
     "purchase_price_per_item": 60},
    {"name": "Брелок Когтевран круглый", "supplier_name": "misteria.prom.ua", "quantity": 0, "purchase_total_price": 60,
     "purchase_price_per_item": 60},
    {"name": "Брелок Пуфендуй круглый", "supplier_name": "misteria.prom.ua", "quantity": 0, "purchase_total_price": 60,
     "purchase_price_per_item": 60},
    {"name": "Брелок Хогвартс круглый", "supplier_name": "misteria.prom.ua", "quantity": 0, "purchase_total_price": 0,
     "purchase_price_per_item": 0},
    {"name": "Светильник Сова", "supplier_name": "misteria.prom.ua", "quantity": 0, "purchase_total_price": 390,
     "purchase_price_per_item": 390},
    {"name": "Сервиз чайный Хогвартс", "supplier_name": "Настя @tykkinykki", "quantity": 0,
     "purchase_total_price": 3800,
     "purchase_price_per_item": 3800},
    {"name": "Шарф Гриффиндор", "supplier_name": "Татьяна Явтуховская", "quantity": 0, "purchase_total_price": 900,
     "purchase_price_per_item": 900},
    {"name": "Чашка с молнией", "supplier_name": "starsandsky.com.ua", "quantity": 0, "purchase_total_price": 165,
     "purchase_price_per_item": 165},
    {"name": "Чашка с гербом Хогвартса", "supplier_name": "starsandsky.com.ua", "quantity": 0,
     "purchase_total_price": 165,
     "purchase_price_per_item": 165},
    {"name": "Чашка с оленем", "supplier_name": "starsandsky.com.ua", "quantity": 0, "purchase_total_price": 165,
     "purchase_price_per_item": 165},
    {"name": "Чашка с совой", "supplier_name": "starsandsky.com.ua", "quantity": 0, "purchase_total_price": 135,
     "purchase_price_per_item": 135},
    {"name": "Чашка с башней", "supplier_name": "starsandsky.com.ua", "quantity": 0, "purchase_total_price": 135,
     "purchase_price_per_item": 135},
    {"name": "Мешочки тканевые 23х17", "supplier_name": "https://prom.ua/ua/c2798198-gsl-internet-magazin.html",
     "quantity": 0, "purchase_total_price": 92, "purchase_price_per_item": 23},
    {"name": "Мешочки тканевые 13х10", "supplier_name": "https://prom.ua/ua/c2798198-gsl-internet-magazin.html",
     "quantity": 0, "purchase_total_price": 100, "purchase_price_per_item": 10},
    {"name": "Мешочки тканевые 10х8", "supplier_name": "https://prom.ua/ua/c2798198-gsl-internet-magazin.html",
     "quantity": 0, "purchase_total_price": 120, "purchase_price_per_item": 8}
]
# Створення початкових категорій у базі даних
categories = ['Сувеніри', 'Гаррі Поттер', 'Володар Перснів']

for category_name in categories:
    Category.get_or_create(name=category_name)


# Функція для завантаження продуктів у базу даних
def load_products_to_db(data):
    logging.info(f"Array '{data}'.")

    for product_data in data:
        logging.info(f"Product '{product_data}'.")

        try:
            # Знаходимо або створюємо постачальника
            supplier, created = Supplier.get_or_create(name=product_data['supplier_name'])
            created_date = product_data.get('created_date')

            # Логування створення StockHistory
            logging.info(f"Creating stock history for product '{product_data['name']}'.")

            # Створюємо або знаходимо продукт
            product, product_created = Product.get_or_create(
                name=product_data['name'],
                supplier=supplier,
                defaults={
                    'quantity': product_data['quantity'],
                    'purchase_total_price': product_data['purchase_total_price'],
                    'purchase_price_per_item': product_data['purchase_price_per_item'],
                    'category': Category.get(name='Сувеніри'),  # За замовчуванням ставимо категорію 'Сувеніри'
                    'created_date': created_date if created_date else datetime.now()
                }
            )

            # Створюємо запис в StockHistory для продукту
            StockHistory.create(
                product=product,  # Тут передаємо об'єкт Product, а не словник
                change_amount=product_data['quantity'],
                change_type='create',
                timestamp=created_date if created_date else datetime.now()
            )

            logging.info(f"Product '{product_data['name']}' added successfully.")

        except IntegrityError as e:
            logging.error(f"Error adding product '{product_data['name']}': {e}")


# Виклик функції
load_products_to_db(data)


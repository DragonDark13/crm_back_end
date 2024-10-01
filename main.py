from peewee import Model, CharField, FloatField, IntegerField, SqliteDatabase, IntegrityError

# Ініціалізуємо базу даних
from models import StockHistory, PurchaseHistory, SaleHistory, ProductCategory, Category, Supplier, Product

db = SqliteDatabase('shop_crm.db')

# Створюємо таблицю в базі даних
db.connect()
db.drop_tables([Product, StockHistory, PurchaseHistory, SaleHistory, ProductCategory, Category, Supplier])
db.create_tables([Product, StockHistory, PurchaseHistory, SaleHistory, ProductCategory, Category, Supplier])

# Приклад додавання товарів
data = [
    {"name": "Палочка Воландеморта", "supplier_name": "skladoptom.com.ua", "quantity": 1, "total_price": 507.6,
     "price_per_item": 507.6},
    {"name": "Палочка Грюма", "supplier_name": "skladoptom.com.ua", "quantity": 1, "total_price": 507.6,
     "price_per_item": 507.6},
    {"name": "Брелок с гербом Пуффендуя", "supplier_name": "skladoptom.com.ua", "quantity": 1, "total_price": 65.49,
     "price_per_item": 65.49},
    {"name": "Брелок с гербом Когтевран", "supplier_name": "misteria.prom.ua", "quantity": 1, "total_price": 86,
     "price_per_item": 86},
    {"name": "Брелок Дары Смерти", "supplier_name": "misteria.prom.ua", "quantity": 1, "total_price": 81,
     "price_per_item": 81},
    {"name": "Брелок Грифиндор круглый", "supplier_name": "misteria.prom.ua", "quantity": 1, "total_price": 60,
     "price_per_item": 60},
    {"name": "Брелок Слизерин круглый", "supplier_name": "misteria.prom.ua", "quantity": 1, "total_price": 60,
     "price_per_item": 60},
    {"name": "Брелок Когтевран круглый", "supplier_name": "misteria.prom.ua", "quantity": 1, "total_price": 60,
     "price_per_item": 60},
    {"name": "Брелок Пуфендуй круглый", "supplier_name": "misteria.prom.ua", "quantity": 1, "total_price": 60,
     "price_per_item": 60},
    {"name": "Брелок Хогвартс круглый", "supplier_name": "misteria.prom.ua", "quantity": 1, "total_price": 0,
     "price_per_item": 0},
    {"name": "Светильник Сова", "supplier_name": "misteria.prom.ua", "quantity": 1, "total_price": 390,
     "price_per_item": 390},
    {"name": "Сервиз чайный Хогвартс", "supplier_name": "Настя @tykkinykki", "quantity": 1, "total_price": 3800,
     "price_per_item": 3800},
    {"name": "Шарф Гриффиндор", "supplier_name": "Татьяна Явтуховская", "quantity": 1, "total_price": 900,
     "price_per_item": 900},
    {"name": "Чашка с молнией", "supplier_name": "starsandsky.com.ua", "quantity": 1, "total_price": 165,
     "price_per_item": 165},
    {"name": "Чашка с гербом Хогвартса", "supplier_name": "starsandsky.com.ua", "quantity": 1, "total_price": 165,
     "price_per_item": 165},
    {"name": "Чашка с оленем", "supplier_name": "starsandsky.com.ua", "quantity": 1, "total_price": 165,
     "price_per_item": 165},
    {"name": "Чашка с совой", "supplier_name": "starsandsky.com.ua", "quantity": 1, "total_price": 135,
     "price_per_item": 135},
    {"name": "Чашка с башней", "supplier_name": "starsandsky.com.ua", "quantity": 1, "total_price": 135,
     "price_per_item": 135},
    {"name": "Мешочки тканевые 23х17", "supplier_name": "https://prom.ua/ua/c2798198-gsl-internet-magazin.html",
     "quantity": 4, "total_price": 92, "price_per_item": 23},
    {"name": "Мешочки тканевые 13х10", "supplier_name": "https://prom.ua/ua/c2798198-gsl-internet-magazin.html",
     "quantity": 10, "total_price": 100, "price_per_item": 10},
    {"name": "Мешочки тканевые 10х8", "supplier_name": "https://prom.ua/ua/c2798198-gsl-internet-magazin.html",
     "quantity": 15, "total_price": 120, "price_per_item": 8}
]


# Функція для завантаження продуктів у базу даних
def load_products_to_db(data):
    for item in data:
        try:
            # Знаходимо або створюємо постачальника
            supplier, created = Supplier.get_or_create(name=item['supplier_name'])

            # Створюємо продукт, пов'язуючи його з постачальником
            Product.create(
                name=item['name'],
                supplier=supplier,
                quantity=item['quantity'],
                total_price=item['total_price'],
                price_per_item=item['price_per_item']
            )
            print(f"Product '{item['name']}' added successfully.")

        except IntegrityError as e:
            print(f"Error adding product '{item['name']}': {e}")


# Виклик функції
load_products_to_db(data)

# Створення початкових категорій у базі даних
categories = ['Сувеніри', 'Гаррі Поттер', 'Володар Перснів']

for category_name in categories:
    Category.get_or_create(name=category_name)

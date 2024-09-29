from peewee import Model, CharField, FloatField, IntegerField, SqliteDatabase

# Ініціалізуємо базу даних
from models import StockHistory, PurchaseHistory, SaleHistory, ProductCategory, Category, Supplier, Product

db = SqliteDatabase('shop_crm.db')



# Створюємо таблицю в базі даних
db.connect()
db.drop_tables([Product, StockHistory, PurchaseHistory, SaleHistory, ProductCategory, Category, Supplier])
db.create_tables([Product, StockHistory, PurchaseHistory, SaleHistory, ProductCategory, Category, Supplier])

# Приклад додавання товарів
products = [
    {"name": "Палочка Воландеморта",  "quantity": 1, "total_price": 507.6,
     "price_per_item": 507.6},
    {"name": "Палочка Грюма", "quantity": 1, "total_price": 507.6,
     "price_per_item": 507.6},
    {"name": "Брелок с гербом Пуффендуя", "quantity": 1, "total_price": 65.49,
     "price_per_item": 65.49}
]

for product in products:
    Product.create(**product)

# Створення початкових категорій у базі даних
categories = ['Сувеніри', 'Гаррі Поттер', 'Володар Перснів']

for category_name in categories:
    Category.get_or_create(name=category_name)

suppliers = ['постачальник1', 'постачальник2', 'постачальник3']

for suppliers_name in suppliers:
    Supplier.get_or_create(name=suppliers_name)

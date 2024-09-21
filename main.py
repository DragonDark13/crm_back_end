from peewee import Model, CharField, FloatField, IntegerField, SqliteDatabase

# Ініціалізуємо базу даних
from models import StockHistory

db = SqliteDatabase('shop_crm.db')


class Product(Model):
    name = CharField()  # Назва товару
    supplier = CharField()  # Постачальник
    quantity = IntegerField()  # Кількість товару
    total_price = FloatField()  # Вартість за кількість
    price_per_item = FloatField()  # Вартість за одиницю

    class Meta:
        database = db


# Створюємо таблицю в базі даних
db.connect()
db.drop_tables([Product, StockHistory])
db.create_tables([Product, StockHistory])

# Приклад додавання товарів
products = [
    {"name": "Палочка Воландеморта", "supplier": "skladoptom.com.ua", "quantity": 1, "total_price": 507.6,
     "price_per_item": 507.6},
    {"name": "Палочка Грюма", "supplier": "skladoptom.com.ua", "quantity": 1, "total_price": 507.6,
     "price_per_item": 507.6},
    {"name": "Брелок с гербом Пуффендуя", "supplier": "skladoptom.com.ua", "quantity": 1, "total_price": 65.49,
     "price_per_item": 65.49}
]

for product in products:
    Product.create(**product)

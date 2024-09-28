from tkinter import CASCADE

from peewee import Model, CharField, IntegerField, DateTimeField, ForeignKeyField, FloatField, DateField, DecimalField
from playhouse.sqlite_ext import SqliteDatabase
from datetime import datetime

db = SqliteDatabase('shop_crm.db')


class BaseModel(Model):
    class Meta:
        database = db


class Supplier(BaseModel):
    name = CharField(unique=True)
    contact_info = CharField(null=True)  # Додаткова інформація про контакт (можна адаптувати за потребою)

    class Meta:
        table_name = 'suppliers'


class Product(BaseModel):
    name = CharField()
    supplier = ForeignKeyField(Supplier, backref='products')  # Зв'язок з постачальником

    quantity = IntegerField()
    total_price = IntegerField()
    price_per_item = IntegerField()


class StockHistory(BaseModel):
    product = ForeignKeyField(Product, backref='stock_history', on_delete=CASCADE)
    change_amount = IntegerField()
    change_type = CharField(choices=[('add', 'Add'), ('subtract', 'Subtract')])
    timestamp = DateTimeField(default=datetime.now)


class PurchaseHistory(BaseModel):
    product = ForeignKeyField(Product, backref='purchases', on_delete=CASCADE)
    price_per_item = FloatField()
    total_price = FloatField()
    supplier = CharField()
    purchase_date = DateField()
    quantity_purchase = FloatField()


class SaleHistory(BaseModel):
    product = ForeignKeyField(Product, backref='sales', on_delete=CASCADE)
    customer = CharField()
    quantity_sold = IntegerField()
    price_per_item = DecimalField(max_digits=10, decimal_places=2)
    total_price = DecimalField(max_digits=12, decimal_places=2)
    sale_date = DateTimeField(default=datetime.now)


class Category(BaseModel):
    name = CharField(unique=True)

    class Meta:
        db_table = 'categories'


class ProductCategory(BaseModel):
    product = ForeignKeyField(Product, backref='categories', on_delete=CASCADE)
    category = ForeignKeyField(Category, backref='products')

    class Meta:
        db_table = 'product_categories'

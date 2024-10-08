from tkinter import CASCADE

from peewee import Model, CharField, IntegerField, DateTimeField, ForeignKeyField, FloatField, DateField, DecimalField
from peewee_migrate import Migrator
from playhouse.sqlite_ext import SqliteDatabase
from datetime import datetime

db = SqliteDatabase('shop_crm.db')


class BaseModel(Model):
    class Meta:
        database = db


class Supplier(BaseModel):
    name = CharField(unique=True)
    contact_info = CharField(null=True)
    email = CharField(null=True)
    phone_number = CharField(null=True)
    address = CharField(null=True)

    class Meta:
        db_table = 'suppliers'


class Product(BaseModel):
    name = CharField()
    supplier = ForeignKeyField(Supplier, null=True, backref='products')  # Додаємо null=True
    quantity = IntegerField(default=0)
    purchase_total_price = DecimalField(max_digits=10, decimal_places=2, default=0.00)
    purchase_price_per_item = DecimalField(max_digits=10, decimal_places=2, default=0.00)
    selling_total_price = DecimalField(max_digits=10, decimal_places=2, default=0.00)
    selling_price_per_item = DecimalField(max_digits=10, decimal_places=2, default=0.00)
    selling_quantity = IntegerField(default=0)
    created_date = DateTimeField(default=datetime.now)


class StockHistory(BaseModel):
    product = ForeignKeyField(Product, backref='stock_history', on_delete=CASCADE)
    change_amount = IntegerField()
    change_type = CharField(choices=[('add', 'Add'), ('subtract', 'Subtract'), ('create', 'Create')])
    timestamp = DateTimeField(default=datetime.now)


class PurchaseHistory(BaseModel):
    product = ForeignKeyField(Product, backref='purchases', on_delete=CASCADE)
    purchase_price_per_item = DecimalField(max_digits=10, decimal_places=2, default=0.00)
    purchase_total_price = DecimalField(max_digits=10, decimal_places=2, default=0.00)
    supplier = ForeignKeyField(Supplier, backref='purchase_history', on_delete=CASCADE)  # Зв'язок з постачальником
    purchase_date = DateField()
    quantity_purchase = FloatField()


class SaleHistory(BaseModel):
    product = ForeignKeyField(Product, backref='sales', on_delete=CASCADE)
    customer = CharField()
    quantity_sold = IntegerField()
    selling_price_per_item = DecimalField(max_digits=10, decimal_places=2, default=0.00)
    selling_total_price = DecimalField(max_digits=12, decimal_places=2, default=0.00)
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

        # Initialize the migrator


class Customer(BaseModel):
    name = CharField()
    contact_info = CharField(null=True)
    address = CharField(null=True)
    email = CharField(unique=True, null=True)
    phone_number = CharField(null=True)

    class Meta:
        db_table = 'customers'


class UserRole(BaseModel):
    name = CharField(unique=True)

class User(BaseModel):
    username = CharField(unique=True)
    password = CharField()
    role = ForeignKeyField(UserRole, backref='users')

    class Meta:
        db_table = 'users'
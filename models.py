from peewee import Model, CharField, IntegerField, DateTimeField, ForeignKeyField, FloatField, DateField, DecimalField
from playhouse.sqlite_ext import SqliteDatabase
from datetime import datetime

db = SqliteDatabase('shop_crm.db')


class BaseModel(Model):
    class Meta:
        database = db


class Product(BaseModel):
    name = CharField()
    supplier = CharField()
    quantity = IntegerField()
    total_price = IntegerField()
    price_per_item = IntegerField()


class StockHistory(BaseModel):
    product = ForeignKeyField(Product, backref='stock_history')
    change_amount = IntegerField()
    change_type = CharField(choices=[('add', 'Add'), ('subtract', 'Subtract')])
    timestamp = DateTimeField(default=datetime.now)


class PurchaseHistory(BaseModel):
    product = ForeignKeyField(Product, backref='purchases')
    price_per_item = FloatField()
    total_price = FloatField()
    supplier = CharField()
    purchase_date = DateField()


class SaleHistory(BaseModel):
    product = ForeignKeyField(Product, backref='sales')
    customer = CharField()
    quantity_sold = IntegerField()
    price_per_item = DecimalField(max_digits=10, decimal_places=2)
    total_price = DecimalField(max_digits=12, decimal_places=2)
    sale_date = DateTimeField(default=datetime.now)


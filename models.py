from peewee import Model, CharField, IntegerField, DateTimeField, ForeignKeyField
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

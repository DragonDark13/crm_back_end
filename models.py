from flask_login import UserMixin
from flask_security import RoleMixin
from peewee import Model, CharField, IntegerField, DateTimeField, ForeignKeyField, FloatField, DateField, \
    DecimalField, DoesNotExist
from playhouse.sqlite_ext import SqliteDatabase
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

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
    supplier = ForeignKeyField(Supplier, null=True, backref='products')  # Дозволяємо поле бути порожнім
    quantity = IntegerField(default=0)
    purchase_total_price = DecimalField(max_digits=10, decimal_places=2, default=0.00)
    purchase_price_per_item = DecimalField(max_digits=10, decimal_places=2, default=0.00)
    selling_total_price = DecimalField(max_digits=10, decimal_places=2, default=0.00)
    selling_price_per_item = DecimalField(max_digits=10, decimal_places=2, default=0.00)
    selling_quantity = IntegerField(default=0)
    created_date = DateTimeField(default=datetime.now)


class StockHistory(BaseModel):
    product = ForeignKeyField(Product, backref='stock_history', on_delete='CASCADE')
    change_amount = IntegerField()
    change_type = CharField(choices=[('add', 'Add'), ('subtract', 'Subtract'), ('create', 'Create')])
    timestamp = DateTimeField(default=datetime.now)


class PurchaseHistory(BaseModel):
    product = ForeignKeyField(Product, backref='purchases', on_delete='CASCADE')
    purchase_price_per_item = DecimalField(max_digits=10, decimal_places=2, default=0.00)
    purchase_total_price = DecimalField(max_digits=10, decimal_places=2, default=0.00)
    supplier = ForeignKeyField(Supplier, backref='purchase_history', on_delete='CASCADE')  # Зв'язок з постачальником
    purchase_date = DateField()
    quantity_purchase = FloatField()


class Customer(BaseModel):
    name = CharField(unique=True)
    contact_info = CharField(null=True)
    address = CharField(null=True)
    email = CharField(null=True)
    phone_number = CharField(null=True)

    class Meta:
        db_table = 'customers'


class SaleHistory(BaseModel):
    product = ForeignKeyField(Product, backref='sales', on_delete='CASCADE')
    customer = ForeignKeyField(Customer, backref='sales', on_delete='CASCADE')  # Зв'язок із покупцем
    quantity_sold = IntegerField()
    selling_price_per_item = DecimalField(max_digits=10, decimal_places=2, default=0.00)
    selling_total_price = DecimalField(max_digits=12, decimal_places=2, default=0.00)
    sale_date = DateTimeField(default=datetime.now)

    class Meta:
        db_table = 'sale_history'


class Category(BaseModel):
    name = CharField(unique=True)

    class Meta:
        db_table = 'categories'


class ProductCategory(BaseModel):
    product = ForeignKeyField(Product, backref='categories', on_delete='CASCADE')
    category = ForeignKeyField(Category, backref='products')

    class Meta:
        db_table = 'product_categories'

        # Initialize the migrator


class Role(BaseModel, RoleMixin):
    name = CharField(unique=True)
    description = CharField(null=True)

    class Meta:
        db_table = 'roles'


class User(BaseModel, UserMixin):
    username = CharField(unique=True)
    email = CharField(unique=True, null=True)
    password = CharField()
    active = IntegerField(default=1)
    confirmed_at = DateTimeField(null=True)

    class Meta:
        db_table = 'users'

    @classmethod
    def get_by_username(cls, username):
        try:
            return cls.get(cls.username == username)
        except DoesNotExist:
            return None

    def set_password(self, password):
        """Hashes the password and stores it."""
        self.password = generate_password_hash(password)

    def verify_password(self, password):
        """Verifies the provided password against the stored hashed password."""
        return check_password_hash(self.password, password)


class UserRoles(BaseModel):
    user = ForeignKeyField(User, backref='roles', on_delete='CASCADE')
    role = ForeignKeyField(Role, backref='users', on_delete='CASCADE')

    class Meta:
        db_table = 'user_roles'

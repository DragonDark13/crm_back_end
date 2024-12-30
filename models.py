from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_security import RoleMixin
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Date, DECIMAL, Table, create_engine
from sqlalchemy.orm import relationship, declarative_base, sessionmaker, scoped_session
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Create a SQLAlchemy instance
db = SQLAlchemy()

# Define your base model
Base = db.Model  # Use SQLAlchemy's model base

# Association table for many-to-many relationships
user_roles_table = Table(
    'user_roles', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE')),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'))
)

product_categories_table = Table(
    'product_categories', Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id', ondelete='CASCADE')),
    Column('category_id', Integer, ForeignKey('categories.id', ondelete='CASCADE'))
)


class Supplier(Base):
    __tablename__ = 'suppliers'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    contact_info = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    address = Column(String, nullable=True)
    products = relationship("Product", back_populates="supplier", cascade="all, delete-orphan")
    purchase_history = relationship("PurchaseHistory", back_populates="supplier", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    supplier_id = Column(Integer, ForeignKey('suppliers.id', ondelete='SET NULL'), nullable=True)
    total_quantity = Column(Integer, default=0)  # Загальна кількість закупленого
    available_quantity = Column(Integer, default=0)  # Кількість в наявності
    sold_quantity = Column(Integer, default=0)  # Кількість проданого
    purchase_total_price = Column(DECIMAL(10, 2), default=0.00)
    purchase_price_per_item = Column(DECIMAL(10, 2), default=0.00)
    selling_total_price = Column(DECIMAL(10, 2), default=0.00)
    selling_price_per_item = Column(DECIMAL(10, 2), default=0.00)
    selling_quantity = Column(Integer, default=0)
    created_date = Column(DateTime, default=datetime.now)
    supplier = relationship("Supplier", back_populates="products")
    stock_history = relationship("StockHistory", back_populates="product", cascade="all, delete-orphan")
    purchases = relationship("PurchaseHistory", back_populates="product", cascade="all, delete-orphan")
    sales = relationship("SaleHistory", back_populates="product", cascade="all, delete-orphan")
    categories = relationship("Category", secondary=product_categories_table, back_populates="products")
    reorder_level = Column(Integer, default=0)

    def to_dict(self):
        """Convert product instance to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'supplier_id': self.supplier_id,
            'total_quantity': self.total_quantity,
            'available_quantity': self.available_quantity,
            'sold_quantity': self.sold_quantity,
            'purchase_total_price': float(self.purchase_total_price or 0),
            'purchase_price_per_item': float(self.purchase_price_per_item or 0),
            'selling_total_price': float(self.selling_total_price or 0),
            'selling_price_per_item': float(self.selling_price_per_item or 0),
            'created_date': self.created_date.isoformat() if self.created_date else None
        }


class StockHistory(Base):
    __tablename__ = 'stock_history'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'))
    change_amount = Column(Integer, nullable=False)
    change_type = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    product = relationship("Product", back_populates="stock_history")

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'timestamp': self.timestamp,
            'change_type': self.change_type,
            'change_amount': self.change_amount
            # Add any other fields that need to be returned
        }


class PurchaseHistory(Base):
    __tablename__ = 'purchase_history'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'))
    supplier_id = Column(Integer, ForeignKey('suppliers.id', ondelete='CASCADE'))
    purchase_price_per_item = Column(DECIMAL(10, 2), default=0.00)
    purchase_total_price = Column(DECIMAL(10, 2), default=0.00)
    purchase_date = Column(Date, nullable=False)
    quantity_purchase = Column(Float, nullable=False)
    product = relationship("Product", back_populates="purchases")
    supplier = relationship("Supplier", back_populates="purchase_history")

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'supplier_id': self.supplier_id,
            'purchase_price_per_item': float(self.purchase_price_per_item),
            'purchase_total_price': float(self.purchase_total_price),
            'purchase_date': self.purchase_date.strftime('%Y-%m-%d'),
            'quantity_purchase': self.quantity_purchase,
            'supplier': {
                'id': self.supplier.id,
                'name': self.supplier.name,
                'contact_info': self.supplier.contact_info
            } if self.supplier else None
        }


class Customer(Base):
    __tablename__ = 'customers'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    contact_info = Column(String, nullable=True)
    address = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    sales = relationship("SaleHistory", back_populates="customer", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'address': self.address,
            'phone_number': self.phone_number
        }


class SaleHistory(Base):
    __tablename__ = 'sale_history'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'))
    customer_id = Column(Integer, ForeignKey('customers.id', ondelete='CASCADE'))
    quantity_sold = Column(Integer, nullable=False)
    selling_price_per_item = Column(DECIMAL(10, 2), default=0.00)
    selling_total_price = Column(DECIMAL(12, 2), default=0.00)
    sale_date = Column(DateTime, default=datetime.now)
    product = relationship("Product", back_populates="sales")
    customer = relationship("Customer", back_populates="sales")
    payment = relationship("Payment", uselist=False, back_populates="sale", cascade="all, delete-orphan")
    profit = Column(DECIMAL(10, 2), default=0.00)

    # Add back_populates for returns
    returns = relationship("ReturnHistory", back_populates="sale", cascade="all, delete-orphan")

    def to_dict(self, include_customer=False):
        result = {
            'id': self.id,
            'product_id': self.product_id,
            'customer_id': self.customer_id,
            'quantity_sold': self.quantity_sold,
            'selling_price_per_item': float(self.selling_price_per_item),
            'selling_total_price': float(self.selling_total_price),
            'sale_date': self.sale_date.strftime('%Y-%m-%d %H:%M:%S'),
            'profit': float(self.profit),
        }
        if include_customer and self.customer:
            result['customer'] = self.customer.to_dict()  # Add customer info if needed
        return result


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    products = relationship("Product", secondary=product_categories_table, back_populates="categories")


class Role(Base, RoleMixin):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    users = relationship("User", secondary=user_roles_table, back_populates="roles")


class User(Base, UserMixin):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=True)
    password = Column(String, nullable=False)
    active = Column(Integer, default=1)
    confirmed_at = Column(DateTime, nullable=True)
    fs_uniquifier = Column(String(255), unique=True, nullable=False)  # Add fs_uniquifier
    roles = relationship("Role", secondary=user_roles_table, back_populates="users")

    def set_password(self, password):
        """Hashes the password and stores it."""
        self.password = generate_password_hash(password)

    def verify_password(self, password):
        """Verifies the provided password against the stored hashed password."""
        return check_password_hash(self.password, password)


class Payment(Base):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey('sale_history.id', ondelete='CASCADE'))
    amount_paid = Column(DECIMAL(10, 2), nullable=False)
    payment_method = Column(String, nullable=False)  # Наприклад, "Card", "Cash", "Online"
    payment_date = Column(DateTime, default=datetime.now)
    sale = relationship("SaleHistory", back_populates="payment")


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    action = Column(String, nullable=False)  # Наприклад, "add_product", "update_stock"
    details = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)
    user = relationship("User")


class ReturnHistory(Base):
    __tablename__ = 'return_history'
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'))
    customer_id = Column(Integer, ForeignKey('customers.id', ondelete='CASCADE'))
    quantity_returned = Column(Integer, nullable=False)
    return_reason = Column(String, nullable=True)
    return_date = Column(DateTime, default=datetime.now)

    # sale_id to link returns to sales
    sale_id = Column(Integer, ForeignKey('sale_history.id', ondelete='CASCADE'))

    # Relationships
    product = relationship("Product", backref="returns")
    customer = relationship("Customer", backref="returns")

    # Use 'sale_history' to reference the SaleHistory in the reverse relationship
    sale = relationship("SaleHistory", back_populates="returns", overlaps="sale_history")  # Resolve the overlap warning


# Create engine and session
engine = create_engine('sqlite:///shop_crm.db')  # Example database URI
Session = sessionmaker(bind=engine)
db_session = scoped_session(Session)  # Scoped session for thread-local management

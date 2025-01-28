from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Date, DECIMAL, Table
from sqlalchemy.orm import relationship
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
    reserved_quantity = Column(Integer, nullable=False, default=0)  # Додайте default=0

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

    def to_dict(self, include_sales=False):
        customer_data = {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'address': self.address,
            'phone_number': self.phone_number
        }

        if include_sales:
            customer_data['sales'] = [
                sale.to_dict() for sale in self.sales
            ]

        return customer_data


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

    # Add packaging material fields
    packaging_material_id = Column(Integer, ForeignKey('packaging_materials.id', ondelete='SET NULL'))
    packaging_quantity = Column(Float, default=0)  # Quantity of packaging material used
    total_packaging_cost = Column(Float, default=0)
    packaging_material = relationship("PackagingMaterial")  # Link to the packaging material used in the sale
    returns = relationship("ReturnHistory", back_populates="sale", cascade="all, delete-orphan")
    packaging_sale_history = relationship("PackagingSaleHistory", back_populates="sale", cascade="all, delete-orphan")

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
            'packaging_material_id': self.packaging_material_id,
            'packaging_quantity': self.packaging_quantity,
        }
        if include_customer and self.customer:
            result['customer'] = self.customer.to_dict()  # Add customer info if needed
        return result


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    products = relationship("Product", secondary=product_categories_table, back_populates="categories")


class Role(Base, UserMixin):
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

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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


class PackagingMaterial(Base):
    __tablename__ = 'packaging_materials'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)  # Назва матеріалу
    status = db.Column(db.String(50), default='available')  # статус пакування
    packaging_material_supplier_id = Column(Integer, ForeignKey('packaging_material_suppliers.id', ondelete='SET NULL'),
                                            nullable=True)  # Link to the new supplier model
    total_quantity = Column(Float, default=0)  # Загальна кількість закупленого
    available_quantity = Column(Float, default=0)  # Кількість в наявності
    purchase_price_per_unit = Column(DECIMAL(10, 2), default=0.00)  # Закупівельна ціна за одиницю
    reorder_level = Column(Float, default=0)  # Мінімальний рівень для повторного замовлення
    total_purchase_cost = Column(DECIMAL(12, 2), default=0.00)  # Загальна сума закупленого
    available_stock_cost = Column(DECIMAL(12, 2), default=0.00)  # Загальна сума того, що в наявності
    created_date = Column(DateTime, default=datetime.now)

    packaging_material_supplier = relationship("PackagingMaterialSupplier",
                                               back_populates="packaging_materials")  # New relationship
    stock_history = relationship("PackagingStockHistory", back_populates="material", cascade="all, delete-orphan")
    purchase_history = relationship("PackagingPurchaseHistory", back_populates="material", cascade="all, delete-orphan")
    reserved_quantity = Column(Integer, nullable=False, default=0)  # Додайте default=0

    # Зарезервована кількість

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'packaging_material_supplier_id': self.packaging_material_supplier_id,
            'total_quantity': self.total_quantity,
            'available_quantity': self.available_quantity,
            'purchase_price_per_unit': float(self.purchase_price_per_unit or 0),
            'reorder_level': self.reorder_level,
            'total_purchase_cost': float(self.total_purchase_cost or 0),
            'available_stock_cost': float(self.available_stock_cost or 0),
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'supplier': self.packaging_material_supplier.to_dict() if self.packaging_material_supplier else None
        }

    def update_costs(self):
        """
        Оновлює загальну суму закупленого та суму матеріалів у наявності.
        """
        self.total_purchase_cost = self.total_quantity * float(self.purchase_price_per_unit or 0)
        self.available_stock_cost = self.available_quantity * float(self.purchase_price_per_unit or 0)


class PackagingStockHistory(Base):
    __tablename__ = 'packaging_stock_history'

    id = Column(Integer, primary_key=True)
    material_id = Column(Integer, ForeignKey('packaging_materials.id', ondelete='CASCADE'))
    change_amount = Column(Float, nullable=False)  # Зміна кількості (позитивна або негативна)
    change_type = Column(String, nullable=False)  # Тип зміни (закупівля, списання тощо)
    timestamp = Column(DateTime, default=datetime.now)
    material = relationship("PackagingMaterial", back_populates="stock_history")

    def to_dict(self):
        return {
            'id': self.id,
            'material_id': self.material_id,
            'change_amount': self.change_amount,
            'change_type': self.change_type,
            'timestamp': self.timestamp.isoformat()
        }


class PackagingPurchaseHistory(Base):
    __tablename__ = 'packaging_purchase_history'

    id = Column(Integer, primary_key=True)
    material_id = Column(Integer, ForeignKey('packaging_materials.id', ondelete='CASCADE'))
    supplier_id = Column(Integer, ForeignKey('packaging_material_suppliers.id',
                                             ondelete='SET NULL'))  # Updated to reference packaging_material_suppliers
    quantity_purchased = Column(Float, nullable=False)
    purchase_price_per_unit = Column(DECIMAL(10, 2), default=0.00)
    purchase_total_price = Column(DECIMAL(12, 2), default=0.00)
    purchase_date = Column(DateTime, default=datetime.now)
    material = relationship("PackagingMaterial", back_populates="purchase_history")
    packaging_material_supplier = relationship("PackagingMaterialSupplier")  # Updated to PackagingMaterialSupplier

    def to_dict(self):
        return {
            'id': self.id,
            'material_id': self.material_id,
            'supplier_id': self.supplier_id,
            'quantity_purchased': self.quantity_purchased,
            'purchase_price_per_unit': float(self.purchase_price_per_unit),
            'purchase_total_price': float(self.purchase_total_price),
            'purchase_date': self.purchase_date.isoformat()
        }


class PackagingMaterialSupplier(Base):
    __tablename__ = 'packaging_material_suppliers'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    contact_info = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    address = Column(String, nullable=True)
    packaging_materials = relationship("PackagingMaterial", back_populates="packaging_material_supplier",
                                       cascade="all, delete-orphan")
    purchase_history = relationship("PackagingPurchaseHistory",
                                    back_populates="packaging_material_supplier")  # New relationship added

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'contact_info': self.contact_info,
            'email': self.email,
            'phone_number': self.phone_number,
            'address': self.address,
        }


class PackagingSaleHistory(Base):
    __tablename__ = 'packaging_sale_history'

    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey('sale_history.id', ondelete='CASCADE'))
    packaging_material_id = Column(Integer, ForeignKey('packaging_materials.id', ondelete='SET NULL'))
    packaging_quantity = Column(Float, nullable=False)
    total_packaging_cost = Column(DECIMAL(12, 2), nullable=False)
    sale_date = Column(DateTime, default=datetime.now)

    sale = relationship("SaleHistory", back_populates="packaging_sale_history")
    packaging_material = relationship("PackagingMaterial")

    def to_dict(self):
        return {
            'id': self.id,
            'sale_id': self.sale_id,
            'packaging_material_id': self.packaging_material_id,
            'packaging_quantity': self.packaging_quantity,
            'total_packaging_cost': float(self.total_packaging_cost),
            'sale_date': self.sale_date.isoformat()
        }


class OtherInvestment(Base):
    __tablename__ = "other_investments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type_name = Column(String, nullable=False)  # Назва типу вкладення
    supplier = Column(String, nullable=False)
    cost = Column(Float, nullable=False)  # Вартість
    date = Column(Date, nullable=False)  # Дата

    def to_dict(self):
        """Convert OtherInvestment instance to a dictionary."""
        return {
            'id': self.id,
            'type_name': self.type_name,
            'supplier': self.supplier,
            'cost': float(self.cost or 0),  # Convert to float, handling possible None
            'date': self.date.isoformat() if self.date else None,  # Format date to ISO string
        }


class GiftSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    total_price = db.Column(db.Float, default=0.0)
    gift_selling_price = db.Column(db.Float, default=0.0)

    # Використовуємо back_populates для точного визначення зв'язків
    gift_set_products = db.relationship(
        'GiftSetProduct',
        back_populates='gift_set',
        lazy=True
    )
    gift_set_packagings = db.relationship(
        'GiftSetPackaging',
        back_populates='gift_set',
        lazy=True
    )

    # Доданий метод to_dict
    def to_dict(self):
        products = [
            {
                "product_id": item.product_id,
                "name": item.product.name,
                "type": 'product',
                "quantity": item.quantity,
                "price": item.product.purchase_price_per_item
            }
            for item in self.gift_set_products
        ]
        packagings = [
            {
                "packaging_id": item.packaging_id,
                "type": 'packaging',
                "name": item.packaging.name,
                "quantity": item.quantity,
                "price": item.packaging.purchase_price_per_unit
            }
            for item in self.gift_set_packagings
        ]

        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "total_price": self.total_price,
            "gift_selling_price": self.gift_selling_price,
            "products": products,
            "packagings": packagings
        }


class GiftSetProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gift_set_id = db.Column(db.Integer, db.ForeignKey('gift_set.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)

    gift_set = db.relationship(
        'GiftSet',
        back_populates='gift_set_products'
    )
    product = db.relationship(
        'Product',
        backref=db.backref('gift_set_products', lazy=True)
    )


class GiftSetPackaging(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gift_set_id = db.Column(db.Integer, db.ForeignKey('gift_set.id'), nullable=False)
    packaging_id = db.Column(db.Integer, db.ForeignKey('packaging_materials.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)

    gift_set = db.relationship(
        'GiftSet',
        back_populates='gift_set_packagings'
    )
    packaging = db.relationship(
        'PackagingMaterial',
        backref=db.backref('gift_set_packagings', lazy=True)
    )


class GiftSetSalesHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gift_set_id = db.Column(db.Integer, db.ForeignKey('gift_set.id'), nullable=False)
    sold_at = db.Column(db.DateTime, default=datetime.utcnow)
    sold_price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    customer_name = db.Column(db.String(255), nullable=True)  # Необов'язкове поле для покупця

    gift_set = db.relationship(
        'GiftSet',
        backref=db.backref('gift_set_sales_history', lazy=True),
        overlaps="gift_set_products,gift_set_packagings"  # Додаємо overlaps для уникнення конфліктів
    )


def to_dict(self):
    """Перетворити об'єкт в словник для відповіді API."""
    products = [
        {
            "product_id": item.product_id,
            "name": item.product.name,
            "quantity": item.quantity,
            "price": item.product.price
        }
        for item in self.gift_set_products
    ]
    packagings = [
        {
            "packaging_id": item.packaging_id,
            "type": item.packaging.type,
            "quantity": item.quantity,
            "price": item.packaging.price
        }
        for item in self.gift_set_packagings
    ]

    return {
        "id": self.id,
        "gift_set_id": self.gift_set_id,
        "sold_at": self.sold_at.isoformat(),
        "sold_price": self.sold_price,
        "quantity": self.quantity,
        "customer_name": self.customer_name,
        "products": products,
        "packagings": packagings
    }

# Create engine and session
# engine = create_engine('sqlite:///shop_crm.db')  # Example database URI
# Session = sessionmaker(bind=engine)
# db_session = scoped_session(Session)  # Scoped session for thread-local management

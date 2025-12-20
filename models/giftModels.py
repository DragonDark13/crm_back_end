from datetime import datetime

from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DECIMAL, DateTime
from sqlalchemy.orm import relationship

from models.base import Base, db


class GiftSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    total_price = db.Column(db.Float, default=0.0)
    gift_selling_price = db.Column(db.Float, default=0.0)
    is_sold = db.Column(db.Boolean, default=False)

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
    customer_id = Column(Integer, ForeignKey('customers.id'))
    customer = relationship('Customer', back_populates='gift_set_sales')

    gift_set = db.relationship(
        'GiftSet',
        backref=db.backref('gift_set_sales_history', lazy=True),
        overlaps="gift_set_products,gift_set_packagings"  # Додаємо overlaps для уникнення конфліктів
    )

    sales_history_products = db.relationship('GiftSetSalesHistoryProduct', back_populates='sales_history')
    sales_history_packagings = db.relationship('GiftSetSalesHistoryPackaging', back_populates='sales_history')

    def to_dict(self):
        """Перетворити об'єкт в словник для відповіді API."""

        # Продукти з історії продажів
        products = [
            {
                "product_id": item.gift_set_product.product_id,  # доступ через GiftSetProduct
                "name": item.gift_set_product.product.name,  # доступ через GiftSetProduct
                "quantity": item.quantity,
                "price": item.gift_set_product.product.selling_price_per_item  # доступ через GiftSetProduct
            }
            for item in self.sales_history_products  # Використовуємо зв'язок sales_history_products
        ]

        # Пакування з історії продажів
        packagings = [
            {
                "packaging_id": item.gift_set_packaging.packaging_id,  # доступ через GiftSetPackaging
                "quantity": item.quantity,
                "price": item.gift_set_packaging.packaging.purchase_price_per_unit  # доступ через GiftSetPackaging
            }
            for item in self.sales_history_packagings  # Використовуємо зв'язок sales_history_packagings
        ]

        return {
            "id": self.id,
            "gift_set_id": self.gift_set_id,
            "sold_at": self.sold_at.isoformat(),
            "sold_price": self.sold_price,
            "quantity": self.quantity,
            "customer_name": self.customer_id,
            "products": products,
            "packagings": packagings
        }


class GiftSetSalesHistoryProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sales_history_id = db.Column(db.Integer, db.ForeignKey('gift_set_sales_history.id'), nullable=False)
    gift_set_product_id = db.Column(db.Integer, db.ForeignKey('gift_set_product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    sales_history = db.relationship('GiftSetSalesHistory', back_populates='sales_history_products')
    gift_set_product = db.relationship('GiftSetProduct')


class GiftSetSalesHistoryPackaging(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sales_history_id = db.Column(db.Integer, db.ForeignKey('gift_set_sales_history.id'), nullable=False)
    gift_set_packaging_id = db.Column(db.Integer, db.ForeignKey('gift_set_packaging.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    sales_history = db.relationship('GiftSetSalesHistory', back_populates='sales_history_packagings')
    gift_set_packaging = db.relationship('GiftSetPackaging')
# Create engine and session
# engine = create_engine('sqlite:///shop_crm.db')  # Example database URI
# Session = sessionmaker(bind=engine)
# db_session = scoped_session(Session)  # Scoped session for thread-local management

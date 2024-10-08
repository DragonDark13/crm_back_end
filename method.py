
# агальний дохід від продажів: Додавання функції для підрахунку доходу.
from peewee import fn, SQL

from models import StockHistory, SaleHistory, PurchaseHistory, ProductCategory, User, Product


def calculate_total_sales(self):
    total_sales = SaleHistory.select(fn.SUM(SaleHistory.selling_total_price)).scalar() or 0
    return total_sales


# Загальна кількість проданих одиниць:
def total_items_sold(self):
    return SaleHistory.select(fn.SUM(SaleHistory.quantity_sold)).scalar() or 0


# Загальна вартість закупівель:

def average_selling_price(self):
    avg_price = SaleHistory.select(fn.AVG(SaleHistory.selling_price_per_item)).scalar() or 0
    return avg_price


# Середня ціна за одиницю продажу/закупівлі:

def average_purchase_price(self):
    avg_price = PurchaseHistory.select(fn.AVG(PurchaseHistory.purchase_price_per_item)).scalar() or 0
    return avg_price


# Метод для оновлення запасів після продажу:
def update_stock_after_sale(product_id, quantity_sold):
    product = Product.get_by_id(product_id)
    product.quantity -= quantity_sold
    product.save()

    StockHistory.create(
        product=product,
        change_amount=-quantity_sold,
        change_type='subtract'
    )


# Метод для оновлення запасів після закупівлі:
def update_stock_after_purchase(product_id, quantity_purchased):
    product = Product.get_by_id(product_id)
    product.quantity += quantity_purchased
    product.save()

    StockHistory.create(
        product=product,
        change_amount=quantity_purchased,
        change_type='add'
    )


# Звіти по постачальникам:

def supplier_report():
    report = (PurchaseHistory
              .select(PurchaseHistory.supplier, fn.SUM(PurchaseHistory.purchase_total_price).alias('total_spent'))
              .group_by(PurchaseHistory.supplier)
              .order_by(SQL('total_spent').desc()))
    return report


# Аналіз продажів та закупівель за категоріями продуктів.
def category_sales_report():
    report = (SaleHistory
              .select(ProductCategory.category, fn.SUM(SaleHistory.selling_total_price).alias('total_sales'))
              .join(ProductCategory)
              .group_by(ProductCategory.category)
              .order_by(SQL('total_sales').desc()))
    return report


# Метод для перевірки прав доступу:

def has_permission(user_id, action):
    user = User.get_by_id(user_id)
    if user.role.name == 'admin':
        return True
    # Додати інші ролі та права доступу
    return False
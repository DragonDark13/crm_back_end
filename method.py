from sqlalchemy import func
from sqlalchemy.orm import Session
from models import StockHistory, SaleHistory, PurchaseHistory, product_categories_table, User, Product
from models import db_session  # Assuming `db_session` is the SQLAlchemy db_session


def calculate_total_sales():
    total_sales = db_session.query(func.sum(SaleHistory.selling_total_price)).scalar() or 0
    return total_sales


def total_items_sold():
    return db_session.query(func.sum(SaleHistory.quantity_sold)).scalar() or 0


def average_selling_price():
    avg_price = db_session.query(func.avg(SaleHistory.selling_price_per_item)).scalar() or 0
    return avg_price


def average_purchase_price():
    avg_price = db_session.query(func.avg(PurchaseHistory.purchase_price_per_item)).scalar() or 0
    return avg_price


def update_stock_after_sale(product_id, quantity_sold):
    product = db_session.query(Product).get(product_id)
    if product:
        product.quantity -= quantity_sold
        db_session.add(product)

        stock_history = StockHistory(
            product=product,
            change_amount=-quantity_sold,
            change_type='subtract'
        )
        db_session.add(stock_history)
        db_session.commit()


def update_stock_after_purchase(product_id, quantity_purchased):
    product = db_session.query(Product).get(product_id)
    if product:
        product.quantity += quantity_purchased
        db_session.add(product)

        stock_history = StockHistory(
            product=product,
            change_amount=quantity_purchased,
            change_type='add'
        )
        db_session.add(stock_history)
        db_session.commit()


def supplier_report():
    report = (
        db_session.query(PurchaseHistory.supplier, func.sum(PurchaseHistory.purchase_total_price).label('total_spent'))
            .group_by(PurchaseHistory.supplier)
            .order_by(func.sum(PurchaseHistory.purchase_total_price).desc())
            .all())
    return report


def category_sales_report():
    report = (
        db_session.query(product_categories_table.category,
                         func.sum(SaleHistory.selling_total_price).label('total_sales'))
            .join(product_categories_table)
            .group_by(product_categories_table.category)
            .order_by(func.sum(SaleHistory.selling_total_price).desc())
            .all())
    return report


def has_permission(user_id, action):
    user = db_session.query(User).get(user_id)
    if user and user.role.name == 'admin':
        return True
    # Add other roles and access permissions
    return False


def verify_product_sale_history():
    try:
        # Отримуємо всі продукти
        products = db_session.query(Product).all()

        for product in products:
            # Знаходимо всі записи продажів для кожного продукту
            sale_records = db_session.query(SaleHistory).filter(SaleHistory.product_id == product.id).all()

            # Обчислюємо загальну кількість проданого та суму продажу
            total_quantity_sold = sum(record.quantity_sold for record in sale_records)
            total_selling_price = sum(record.selling_total_price for record in sale_records)

            # Перевіряємо дані
            if total_quantity_sold == product.sold_quantity and total_selling_price == float(product.selling_total_price):
                print(f"Product '{product.name}' verification successful!")
            else:
                print(f"Product '{product.name}' verification failed!")
                print(f"Expected quantity sold: {product.sold_quantity}, calculated: {total_quantity_sold}")
                print(f"Expected total selling price: {product.selling_total_price}, calculated: {total_selling_price}")

    except Exception as e:
        print(f"An error occurred: {e}")

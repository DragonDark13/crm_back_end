from flask import Flask, request, jsonify, send_file, Blueprint
from sqlalchemy.orm import joinedload
from io import BytesIO
import pandas as pd
from datetime import datetime

from models import Product
export_to_excel_bp = Blueprint('export_to_excel', __name__)


@export_to_excel_bp.route('/api/export-products-excel', methods=['POST'])
def export_products():
    from postgreSQLConnect import db_session

    # Отримання списку ID продуктів з фронтенду
    data = request.get_json()
    product_ids = data.get("product_ids", [])

    if not product_ids:
        return jsonify({"error": "No product IDs provided"}), 400

    # Запит до бази для отримання продуктів із деталями
    products = (
        db_session.query(Product)
            .filter(Product.id.in_(product_ids))
            .options(joinedload(Product.supplier), joinedload(Product.categories))
            .all()
    )

    # Перетворення даних у формат списку словників
    product_data = []
    for product in products:
        product_data.append({
            "Назва товару": product.name,
            "Постачальник": product.supplier.name if product.supplier else "Н/Д",
            "Категорії": ", ".join([category.name for category in product.categories]),
            "Загальна кількість": product.total_quantity,
            "Доступна кількість": product.available_quantity,
            "Продана кількість": product.sold_quantity,
            "Ціна закупівлі за одиницю": float(product.purchase_price_per_item),
            "Ціна продажу за одиницю": float(product.selling_price_per_item),
            "Дата створення": product.created_date.strftime("%Y-%m-%d"),
        })

    # Створення Excel-файлу
    df = pd.DataFrame(product_data)
    output = BytesIO()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"Products_{timestamp}.xlsx"

    # Запис даних у BytesIO
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Products")

    # Перемістити покажчик на початок файлу
    output.seek(0)

    # Повернення файлу як відповіді
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

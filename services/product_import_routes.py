import os
import tempfile

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from import_data_func.add_new_Product import load_products_from_csv, preview_products_from_csv


product_import_bp = Blueprint("product_import", __name__)

MAX_PURCHASE_CSV_SIZE = 10 * 1024 * 1024


@product_import_bp.route("/imports/products/purchases", methods=["POST"])
def import_product_purchases():
    uploaded_file = request.files.get("file")
    if uploaded_file is None or not uploaded_file.filename:
        return jsonify(error="Оберіть CSV-файл із закупівлями."), 400

    if not uploaded_file.filename.lower().endswith(".csv"):
        return jsonify(error="Підтримуються лише файли у форматі CSV."), 400

    file_content = uploaded_file.stream.read(MAX_PURCHASE_CSV_SIZE + 1)
    if not file_content:
        return jsonify(error="Обраний файл порожній."), 400
    if len(file_content) > MAX_PURCHASE_CSV_SIZE:
        return jsonify(error="Розмір файлу не повинен перевищувати 10 МБ."), 413

    safe_filename = secure_filename(uploaded_file.filename) or "purchases.csv"
    if not safe_filename.lower().endswith(".csv"):
        safe_filename = "purchases.csv"

    try:
        with tempfile.TemporaryDirectory(prefix="crm_purchase_import_") as temp_dir:
            file_path = os.path.join(temp_dir, safe_filename)
            with open(file_path, "wb") as temp_file:
                temp_file.write(file_content)

            result = load_products_from_csv(file_path)
    except (UnicodeDecodeError, ValueError) as error:
        return jsonify(error=str(error)), 400
    except Exception:
        current_app.logger.exception("Failed to import product purchases CSV")
        return jsonify(error="Не вдалося імпортувати файл. Дані не були збережені."), 500

    if result.get("status") == "already_imported":
        return jsonify(
            error="Цей файл уже імпортовано. Повторне завантаження не виконувалося.",
            result=result,
        ), 409

    return jsonify(result), 200


@product_import_bp.route("/imports/products/purchases/preview", methods=["POST"])
def preview_product_purchases():
    uploaded_file = request.files.get("file")
    if uploaded_file is None or not uploaded_file.filename:
        return jsonify(error="Оберіть CSV-файл із закупівлями."), 400

    if not uploaded_file.filename.lower().endswith(".csv"):
        return jsonify(error="Підтримуються лише файли у форматі CSV."), 400

    file_content = uploaded_file.stream.read(MAX_PURCHASE_CSV_SIZE + 1)
    if not file_content:
        return jsonify(error="Обраний файл порожній."), 400
    if len(file_content) > MAX_PURCHASE_CSV_SIZE:
        return jsonify(error="Розмір файлу не повинен перевищувати 10 МБ."), 413

    safe_filename = secure_filename(uploaded_file.filename) or "purchases.csv"
    if not safe_filename.lower().endswith(".csv"):
        safe_filename = "purchases.csv"

    try:
        with tempfile.TemporaryDirectory(prefix="crm_purchase_preview_") as temp_dir:
            file_path = os.path.join(temp_dir, safe_filename)
            with open(file_path, "wb") as temp_file:
                temp_file.write(file_content)
            result = preview_products_from_csv(file_path)
    except (UnicodeDecodeError, ValueError) as error:
        return jsonify(error=str(error)), 400
    except Exception:
        current_app.logger.exception("Failed to preview product purchases CSV")
        return jsonify(error="Не вдалося перевірити файл."), 500

    if result.get("status") == "already_imported":
        return jsonify(
            error="Цей файл уже імпортовано. Повторне завантаження не дозволене.",
            result=result,
        ), 409

    return jsonify(result), 200

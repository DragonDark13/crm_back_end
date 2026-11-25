import csv
import hashlib
import io
import json
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


from models import (
    Category,
    Product,
    ProductAuditHistory,
    ProductImportBatch,
    ProductImportRow,
    PurchaseHistory,
    StockHistory,
    Supplier,
)
from postgreSQLConnect import db_session


def _parse_decimal(value, field_name, row_number, required=False):
    raw_value = (value or "").strip().replace(" ", "")
    if not raw_value:
        if required:
            raise ValueError(f"Рядок {row_number}: не заповнено поле «{field_name}».")
        return None

    try:
        return Decimal(raw_value.replace(",", "."))
    except InvalidOperation as error:
        raise ValueError(
            f"Рядок {row_number}: некоректне число у полі «{field_name}»: {value!r}."
        ) from error


def _parse_purchase_row(row, row_number, legacy_created_date=None):
    # Старий формат залишено для сумісності з example_import_data_func.
    name = (row.get("Найменування") or row.get("Наименование") or "").strip()
    if not name:
        raise ValueError(f"Рядок {row_number}: не заповнено найменування товару.")

    quantity = _parse_decimal(
        row.get("Кількість") or row.get("Количество"),
        "Кількість",
        row_number,
        required=True,
    )
    if quantity <= 0 or quantity != quantity.to_integral_value():
        raise ValueError(
            f"Рядок {row_number}: кількість має бути додатним цілим числом."
        )
    quantity = int(quantity)

    total_price = _parse_decimal(
        row.get("Вартість за кількість") or row.get("Стоимость за количество"),
        "Вартість за кількість",
        row_number,
    )
    price_per_item = _parse_decimal(
        row.get("Вартість за 1 шт") or row.get("Стоимость за 1 шт"),
        "Вартість за 1 шт",
        row_number,
    )

    if total_price is None and price_per_item is None:
        raise ValueError(
            f"Рядок {row_number}: потрібно вказати загальну вартість або вартість одиниці."
        )
    if total_price is None:
        total_price = price_per_item * quantity
    if price_per_item is None:
        price_per_item = total_price / quantity
    if total_price < 0 or price_per_item < 0:
        raise ValueError(f"Рядок {row_number}: вартість не може бути від'ємною.")

    purchase_date_value = (
        (row.get("Дата закупівлі") or "").strip()
        or (legacy_created_date.strftime("%d.%m.%Y") if legacy_created_date else "")
    )
    if not purchase_date_value:
        raise ValueError(f"Рядок {row_number}: не заповнено дату закупівлі.")
    try:
        purchase_date = datetime.strptime(purchase_date_value, "%d.%m.%Y").date()
    except ValueError as error:
        raise ValueError(
            f"Рядок {row_number}: дата «{purchase_date_value}» має бути у форматі ДД.ММ.РРРР."
        ) from error

    supplier_name = (
        row.get("Постачальник") or row.get("Поставщик") or ""
    ).strip()
    if supplier_name.upper() in ("N/A", "—", "-"):
        supplier_name = ""
    supplier_name = supplier_name or None

    categories_value = (row.get("Категорія") or row.get("Категорії") or "").strip()
    categories = list(dict.fromkeys(
        category.strip() for category in categories_value.split(";") if category.strip()
    ))

    description = (row.get("Опис товару") or "").strip()
    if len(description) > 500:
        raise ValueError(
            f"Рядок {row_number}: опис товару перевищує обмеження 500 символів."
        )

    unit_of_measure = (row.get("Одиниця виміру") or "").strip() or None

    return {
        "name": name,
        "quantity": quantity,
        "total_price": total_price,
        "price_per_item": price_per_item,
        "purchase_date": purchase_date,
        "supplier_name": supplier_name,
        "categories": categories,
        "unit_of_measure": unit_of_measure,
        "description": description,
    }



def _fingerprint_decimal(value, scale):
    quantum = Decimal("1").scaleb(-scale)
    return format(
        Decimal(str(value or 0)).quantize(quantum, rounding=ROUND_HALF_UP),
        "f",
    )


def _purchase_fingerprint(purchase):
    """Stable identity for a purchase row, aligned with persisted DB precision."""
    payload = [
        (purchase["name"] or "").strip().casefold(),
        (purchase["supplier_name"] or "").strip().casefold(),
        purchase["purchase_date"].isoformat(),
        _fingerprint_decimal(purchase["quantity"], 0),
        _fingerprint_decimal(purchase["total_price"], 2),
        _fingerprint_decimal(purchase["price_per_item"], 3),
    ]
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _existing_purchase_occurrences(fingerprints):
    if not fingerprints:
        return {}

    rows = db_session.query(
        ProductImportRow.fingerprint,
        ProductImportRow.occurrence_index,
    ).filter(
        ProductImportRow.fingerprint.in_(set(fingerprints))
    ).all()
    occurrences = {}
    for fingerprint, occurrence_index in rows:
        current = occurrences.setdefault(
            fingerprint, {"count": 0, "max_index": 0}
        )
        current["count"] += 1
        current["max_index"] = max(current["max_index"], occurrence_index)
    return occurrences



def _filter_duplicate_purchase_rows(purchases, existing_occurrences):
    """Keeps only occurrences beyond the number already recorded in history."""
    seen_occurrences = {}
    rows_to_import = []
    duplicate_rows = 0

    for row_number, purchase in purchases:
        fingerprint = _purchase_fingerprint(purchase)
        seen_occurrences[fingerprint] = seen_occurrences.get(fingerprint, 0) + 1
        occurrence_index = seen_occurrences[fingerprint]
        existing = existing_occurrences.get(fingerprint, 0)
        existing_count = existing["count"] if isinstance(existing, dict) else existing
        max_index = existing.get("max_index", existing_count) if isinstance(existing, dict) else existing_count
        if occurrence_index <= existing_count:
            duplicate_rows += 1
            continue
        persisted_occurrence_index = max_index + occurrence_index - existing_count
        rows_to_import.append(
            (row_number, purchase, fingerprint, persisted_occurrence_index)
        )

    return rows_to_import, duplicate_rows

def _read_purchase_rows(csv_reader, created_date=None):
    purchases = []
    for row_number, row in enumerate(csv_reader, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        purchases.append(
            (row_number, _parse_purchase_row(row, row_number, created_date))
        )
    if not purchases:
        raise ValueError("У CSV-файлі немає рядків закупівель для імпорту.")
    return purchases

def _generate_article():
    last_product = db_session.query(Product).order_by(Product.id.desc()).first()
    if last_product and last_product.article.startswith("PRD-"):
        last_number = int(last_product.article.split("-")[1])
        new_number = last_number + 1
    else:
        new_number = 1
    return f"PRD-{new_number:04d}"


def preview_products_from_csv(file_path):
    """Перевіряє CSV та показує рядки, які будуть пропущені як дублікати."""
    with open(file_path, mode="rb") as source_file:
        file_content = source_file.read()

    file_hash = hashlib.sha256(file_content).hexdigest()
    existing_batch = db_session.query(ProductImportBatch).filter_by(
        file_hash=file_hash
    ).one_or_none()
    if existing_batch:
        return {
            "status": "already_imported",
            "file_name": existing_batch.file_name,
            "rows_imported": existing_batch.rows_imported,
        }

    text_content = file_content.decode("utf-8-sig")
    csv_reader = csv.DictReader(io.StringIO(text_content))
    if not csv_reader.fieldnames:
        raise ValueError("CSV-файл порожній або не містить заголовків.")

    required_headers = {
        "Найменування", "Постачальник", "Кількість",
        "Вартість за кількість", "Вартість за 1 шт",
        "Дата закупівлі", "Категорія", "Одиниця виміру", "Опис товару",
    }
    legacy_headers = {
        "Наименование", "Поставщик", "Количество",
        "Стоимость за количество", "Стоимость за 1 шт",
    }
    headers = set(csv_reader.fieldnames)
    if not required_headers.issubset(headers) and not legacy_headers.issubset(headers):
        missing = sorted(required_headers - headers)
        raise ValueError(
            "CSV має невідповідні заголовки. Відсутні колонки: "
            + ", ".join(missing)
        )

    purchases = _read_purchase_rows(csv_reader)
    fingerprints = [_purchase_fingerprint(purchase) for _, purchase in purchases]
    existing_occurrences = _existing_purchase_occurrences(fingerprints)
    rows_to_import, duplicate_rows = _filter_duplicate_purchase_rows(
        purchases, existing_occurrences
    )

    existing_product_rows = 0
    new_product_rows = 0
    new_product_names = set()
    existing_product_names = set()

    for _, purchase in rows_to_import:
        product = db_session.query(Product).filter_by(name=purchase["name"]).one_or_none()
        if product is None:
            new_product_rows += 1
            new_product_names.add(purchase["name"])
        else:
            existing_product_rows += 1
            existing_product_names.add(purchase["name"])

    return {
        "status": "preview",
        "file_name": os.path.basename(file_path),
        "rows_total": len(purchases),
        "rows_to_import": len(rows_to_import),
        "duplicate_rows": duplicate_rows,
        "existing_product_rows": existing_product_rows,
        "new_product_rows": new_product_rows,
        "existing_products_count": len(existing_product_names),
        "new_products_count": len(new_product_names),
        "new_product_names": sorted(new_product_names),
    }


def load_products_from_csv(file_path, created_date=None):
    """
    Імпортує всі закупівлі з одного CSV-файлу однією транзакцією.

    Підтримує нові українські заголовки та старий формат для прикладів.
    Повторний файл блокується за SHA-256, а повторні рядки — за fingerprint закупівлі.
    """
    with open(file_path, mode="rb") as source_file:
        file_content = source_file.read()

    file_hash = hashlib.sha256(file_content).hexdigest()
    existing_batch = db_session.query(ProductImportBatch).filter_by(
        file_hash=file_hash
    ).one_or_none()
    if existing_batch:
        return {
            "status": "already_imported",
            "file_name": existing_batch.file_name,
            "rows_imported": existing_batch.rows_imported,
        }

    try:
        text_content = file_content.decode("utf-8-sig")
        csv_reader = csv.DictReader(io.StringIO(text_content))
        if not csv_reader.fieldnames:
            raise ValueError("CSV-файл порожній або не містить заголовків.")

        required_headers = {
            "Найменування", "Постачальник", "Кількість",
            "Вартість за кількість", "Вартість за 1 шт",
            "Дата закупівлі", "Категорія", "Одиниця виміру", "Опис товару",
        }
        legacy_headers = {
            "Наименование", "Поставщик", "Количество",
            "Стоимость за количество", "Стоимость за 1 шт",
        }
        headers = set(csv_reader.fieldnames)
        if not required_headers.issubset(headers) and not legacy_headers.issubset(headers):
            missing = sorted(required_headers - headers)
            raise ValueError(
                "CSV має невідповідні заголовки. Відсутні колонки: "
                + ", ".join(missing)
            )

        purchases = _read_purchase_rows(csv_reader, created_date)
        fingerprints = [_purchase_fingerprint(purchase) for _, purchase in purchases]
        existing_occurrences = _existing_purchase_occurrences(fingerprints)
        rows_to_import, duplicate_rows_skipped = _filter_duplicate_purchase_rows(
            purchases, existing_occurrences
        )
        imported_rows = 0

        for row_number, purchase, fingerprint, occurrence_index in rows_to_import:
            supplier = None
            if purchase["supplier_name"]:
                supplier = db_session.query(Supplier).filter_by(
                    name=purchase["supplier_name"]
                ).one_or_none()
                if supplier is None:
                    supplier = Supplier(name=purchase["supplier_name"])
                    db_session.add(supplier)
                    db_session.flush()

            product = db_session.query(Product).filter_by(
                name=purchase["name"]
            ).with_for_update().one_or_none()

            if product is None:
                product = Product(
                    name=purchase["name"],
                    supplier=supplier,
                    total_quantity=0,
                    available_quantity=0,
                    purchase_total_price=Decimal("0"),
                    purchase_price_per_item=Decimal("0"),
                    created_date=datetime.combine(purchase["purchase_date"], datetime.min.time()),
                    article=_generate_article(),
                    product_description=purchase["description"],
                    unit_of_measure=purchase["unit_of_measure"],
                )
                product.total_quantity = purchase["quantity"]
                product.available_quantity = purchase["quantity"]
                product.purchase_total_price = purchase["total_price"]
                product.purchase_price_per_item = purchase["price_per_item"]
                db_session.add(product)
                db_session.flush()
                audit_changes = {
                    "total_quantity": (None, purchase["quantity"]),
                    "available_quantity": (None, purchase["quantity"]),
                    "purchase_total_price": (None, purchase["total_price"]),
                    "purchase_price_per_item": (None, purchase["price_per_item"]),
                    "unit_of_measure": (None, purchase["unit_of_measure"]),
                    "product_description": (None, purchase["description"]),
                }
                old_category_names = set()
                audit_action = "import_create"
            else:
                old_total_quantity = product.total_quantity or 0
                old_available_quantity = product.available_quantity or 0
                old_purchase_total = Decimal(str(product.purchase_total_price or 0))
                old_purchase_price = Decimal(str(product.purchase_price_per_item or 0))
                old_unit_of_measure = product.unit_of_measure
                old_description = product.product_description
                old_category_names = {category.name for category in product.categories}

                if (
                    purchase["unit_of_measure"]
                    and product.unit_of_measure
                    and product.unit_of_measure != purchase["unit_of_measure"]
                ):
                    raise ValueError(
                        f"Рядок {row_number}: для товару «{product.name}» вже задано "
                        f"одиницю «{product.unit_of_measure}», у файлі — "
                        f"«{purchase['unit_of_measure']}»."
                    )

                product.total_quantity = old_total_quantity + purchase["quantity"]
                product.available_quantity = old_available_quantity + purchase["quantity"]
                product.purchase_total_price = old_purchase_total + purchase["total_price"]
                product.purchase_price_per_item = (
                    product.purchase_total_price / Decimal(product.total_quantity)
                    if product.total_quantity else Decimal("0")
                )
                if supplier and product.supplier is None:
                    product.supplier = supplier
                if purchase["unit_of_measure"] and not product.unit_of_measure:
                    product.unit_of_measure = purchase["unit_of_measure"]
                if purchase["description"] and not product.product_description:
                    product.product_description = purchase["description"]

                audit_changes = {
                    "total_quantity": (old_total_quantity, product.total_quantity),
                    "available_quantity": (old_available_quantity, product.available_quantity),
                    "purchase_total_price": (old_purchase_total, product.purchase_total_price),
                    "purchase_price_per_item": (old_purchase_price, product.purchase_price_per_item),
                    "unit_of_measure": (old_unit_of_measure, product.unit_of_measure),
                    "product_description": (old_description, product.product_description),
                }
                audit_action = "import_purchase"

            existing_category_names = {category.name for category in product.categories}
            for category_name in purchase["categories"]:
                if category_name in existing_category_names:
                    continue
                category = db_session.query(Category).filter_by(
                    name=category_name
                ).one_or_none()
                if category is None:
                    category = Category(name=category_name)
                    db_session.add(category)
                    db_session.flush()
                product.categories.append(category)
                existing_category_names.add(category_name)

            if old_category_names != existing_category_names:
                audit_changes["categories"] = (
                    "; ".join(sorted(old_category_names)),
                    "; ".join(sorted(existing_category_names)),
                )

            purchase_history = PurchaseHistory(
                product_id=product.id,
                purchase_price_per_item=purchase["price_per_item"],
                purchase_total_price=purchase["total_price"],
                supplier_id=supplier.id if supplier else None,
                quantity_purchase=purchase["quantity"],
                purchase_date=purchase["purchase_date"],
            )
            db_session.add(purchase_history)
            db_session.flush()

            db_session.add(ProductImportRow(
                purchase_history_id=purchase_history.id,
                fingerprint=fingerprint,
                occurrence_index=occurrence_index,
            ))

            db_session.add(StockHistory(
                product_id=product.id,
                change_amount=purchase["quantity"],
                change_type="create" if audit_action == "import_create" else "update",
                timestamp=datetime.combine(purchase["purchase_date"], datetime.min.time()),
                quantity_before=(
                    product.available_quantity - purchase["quantity"]
                ),
                quantity_after=product.available_quantity,
                reason="Імпорт закупівлі з CSV",
            ))

            for field_name, (old_value, new_value) in audit_changes.items():
                old_text = str(old_value) if old_value is not None else None
                new_text = str(new_value) if new_value is not None else None
                if old_text != new_text:
                    db_session.add(ProductAuditHistory(
                        product_id=product.id,
                        changed_by_id=None,
                        changed_by_username="Системний імпорт",
                        action=audit_action,
                        field_name=field_name,
                        old_value=old_text,
                        new_value=new_text,
                        reason="Імпорт історичних закупівель з CSV",
                        changed_at=datetime.combine(purchase["purchase_date"], datetime.min.time()),
                    ))

            imported_rows += 1

        db_session.add(ProductImportBatch(
            file_hash=file_hash,
            file_name=os.path.basename(file_path),
            rows_imported=imported_rows,
        ))
        db_session.commit()

        return {
            "status": "imported",
            "file_name": os.path.basename(file_path),
            "rows_imported": imported_rows,
            "duplicate_rows_skipped": duplicate_rows_skipped,
        }
    except Exception:
        db_session.rollback()
        raise


def import_all_product(file_path=None):
    """Імпортує єдиний файл з усією історією закупівель."""
    if file_path is None:
        base_dir = os.path.join(os.path.dirname(__file__), "..", "import_data_csv", "csv_product")
        file_path = os.path.join(base_dir, "zakupivli_vsi.csv")

    result = load_products_from_csv(file_path)
    print(result)
    return result

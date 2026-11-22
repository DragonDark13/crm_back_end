import csv

from sqlalchemy import text

from models import Category


def import_categories_from_csv(csv_filename: str, db_session):
    try:
        with open(csv_filename, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row_number, row in enumerate(reader, start=1):
                if not row or not any(value.strip() for value in row):
                    continue

                if len(row) != 2:
                    raise ValueError(
                        f"Рядок {row_number}: очікується ID та назва категорії."
                    )

                category_id, category_name = row
                category_id = int(category_id.strip())
                category_name = category_name.strip()

                existing_by_id = db_session.query(Category).filter_by(
                    id=category_id
                ).one_or_none()

                if existing_by_id:
                    if existing_by_id.name != category_name:
                        raise ValueError(
                            f"Рядок {row_number}: ID категорії {category_id} "
                            f"вже належить категорії «{existing_by_id.name}», "
                            f"але у CSV вказано «{category_name}»."
                        )
                    continue

                existing_by_name = db_session.query(Category).filter_by(
                    name=category_name
                ).one_or_none()

                if existing_by_name:
                    # Категорія вже існує під іншим ID. Зберігаємо її
                    # поточний ID; товари прив'язуються до категорій за назвою.
                    continue

                db_session.add(Category(id=category_id, name=category_name))

            db_session.flush()
            db_session.execute(text(
                "SELECT setval("
                "pg_get_serial_sequence('categories', 'id'), "
                "COALESCE(MAX(id), 1), MAX(id) IS NOT NULL"
                ") FROM categories"
            ))
            db_session.commit()
    except Exception:
        db_session.rollback()
        raise

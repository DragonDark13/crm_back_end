import csv

from models import Category


def import_categories_from_csv(csv_filename: str, db_session):
    with open(csv_filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            category_id, category_name = row
            category = Category(id=int(category_id), name=category_name)
            db_session.add(category)
        db_session.commit()

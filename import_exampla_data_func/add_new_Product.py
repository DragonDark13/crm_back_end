import os

from sqlalchemy import inspect

# Функція для завантаження продуктів у базу даних

from datetime import datetime

from import_data_func.add_new_Product import load_products_from_csv


def example_import_all_product():
    # Базовий шлях до папки з продуктами
    base_dir = '../example_import_data_csv/csv_product'

    # Список назв файлів і дат
    files_data = [
        ('15.09.2024.csv', "15.09.2024"),
    ]

    for filename, date_str in files_data:
        file_path = os.path.join(base_dir, filename)
        created_date = datetime.strptime(date_str, "%d.%m.%Y")
        load_products_from_csv(file_path, created_date)

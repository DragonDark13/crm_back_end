import os
from datetime import datetime

from import_data_func.add_new_package import import_packaging_materials_from_csv

from postgreSQLConnect import db_session


def example_import_all_packages():
    # Базова папка, яку можна змінити в одному місці
    base_dir = '../example_import_data_csv/csv_package'

    # Список тільки назв файлів і дат (без повного шляху)
    files_data = [
        ('15.01.2025.csv', "15.01.2025"),
    ]

    # Цикл для виклику функції import_packaging_materials_from_csv для кожного файлу
    for filename, date_str in files_data:
        file_path_package = os.path.join(base_dir, filename)
        purchase_date_package = datetime.strptime(date_str, "%d.%m.%Y").date()
        import_packaging_materials_from_csv(file_path_package, purchase_date_package, db_session)



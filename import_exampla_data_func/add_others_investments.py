import os
from datetime import datetime

from import_data_func.add_others_investments import load_other_investments_from_csv


def example_import_all_investment():
    # Базовий шлях до CSV-файлів інвестицій
    base_dir = '../example_import_data_csv/csv_others_investments'

    # Список файлів і відповідних дат
    investment_files_data = [
        ('15.01.2025.csv', "15.01.2025"),
    ]

    for filename, date_str in investment_files_data:
        file_path = os.path.join(base_dir, filename)
        created_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        load_other_investments_from_csv(file_path, created_date)

import os
from datetime import datetime

from sqlalchemy.exc import IntegrityError

import csv

from models import OtherInvestment
from postgreSQLConnect import db_session


def load_other_investments_from_csv(file_path, created_date):
    """
    Завантажує інші витрати з CSV-файлу до бази даних.

    :param file_path: Шлях до CSV-файлу.
    :param created_date: Дата створення запису про витрати (тип datetime.date).
    """
    with open(file_path, mode='r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            # Отримання даних з рядка CSV
            type_name = row['Наименование'].strip()
            raw_supplier = row.get('Поставщик')
            supplier = raw_supplier.strip() if raw_supplier and raw_supplier.strip() else "N/A"

            cost = float(row['Стоимость'].replace(',', '.'))

            try:
                # Додавання нового запису про витрати
                investment = OtherInvestment(
                    type_name=type_name,
                    supplier=supplier,
                    cost=cost,
                    date=created_date
                )
                db_session.add(investment)
                db_session.commit()
                print(f"Інвестиція '{type_name}' успішно додана.")
            except IntegrityError as e:
                db_session.rollback()
                print(f"Помилка додавання інвестиції '{type_name}': {e}")
            except Exception as e:
                db_session.rollback()
                print(f"Несподівана помилка: {e}")


def import_all_investment():
    # Базовий шлях до CSV-файлів інвестицій
    base_dir = 'import_data_csv/csv_others_investments'

    # Список файлів і відповідних дат
    investment_files_data = [
        ('15.02.2023.csv', "15.02.2023"),
        ('15.03.2023.csv', "15.03.2023"),
        ('15.05.2023.csv', "15.04.2023"),  # Ймовірно тут помилка: файл 15.05, дата 15.04
        ('15.04.2023.csv', "15.04.2023"),
        ('15.06.2023.csv', "15.06.2023"),
        ('15.09.2024.csv', "15.09.2024"),
        ('15.01.2025.csv', "15.01.2025"),
    ]

    for filename, date_str in investment_files_data:
        file_path = os.path.join(base_dir, filename)
        created_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        load_other_investments_from_csv(file_path, created_date)

# import_all_investment()

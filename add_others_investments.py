from datetime import datetime

from sqlalchemy.exc import IntegrityError

import csv

from models import OtherInvestment, db_session


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
            supplier = row['Поставщик'].strip()  # Текстове поле
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


# Список з шляхами до CSV-файлів та відповідними датами
investment_files_data = [
    ('csv_others_investments/15.02.2023.csv', "15.02.2023"),
    ('csv_others_investments/15.03.2023.csv', "15.03.2023"),
    ('csv_others_investments/15.05.2023.csv', "15.04.2023"),
    ('csv_others_investments/15.05.2023.csv', "15.05.2023"),
    ('csv_others_investments/15.06.2023.csv', "15.06.2023"),
    ('csv_others_investments/15.09.2023.csv', "15.09.2023"),
]

# Цикл для виклику функції load_other_investments_from_csv для кожного файлу
for file_path, date_str in investment_files_data:
    created_date = datetime.strptime(date_str, "%d.%m.%Y").date()
    load_other_investments_from_csv(file_path, created_date)

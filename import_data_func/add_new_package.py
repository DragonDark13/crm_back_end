import os
from datetime import datetime

import csv
from sqlalchemy.exc import IntegrityError

from models import PackagingMaterial, PackagingMaterialSupplier, PackagingPurchaseHistory, PackagingStockHistory
from postgreSQLConnect import db_session


def import_packaging_materials_from_csv(file_path, purchase_date, db_session):
    """
    Import packaging materials from a CSV file into the database.

    :param file_path: Path to the CSV file.
    :param purchase_date: Date of purchase.
    :param db_session: SQLAlchemy session instance.
    """
    try:
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                name = row.get('Наименование')
                supplier_name = row.get('Поставщик').strip()
                quantity = int(row['Количество'].split()[0])
                total_cost = float(row.get('Стоимость за количество', 0).replace(',', '.'))
                cost_per_unit = float(row.get('Стоимость за 1 шт', 0).replace(',', '.'))

                # Truncate supplier_name to 30 characters and store full name in contact_info
                truncated_supplier_name = supplier_name[:30]
                contact_info = supplier_name

                # Get or create PackagingMaterialSupplier
                supplier = db_session.query(PackagingMaterialSupplier).filter_by(name=truncated_supplier_name).first()
                if not supplier:
                    supplier = PackagingMaterialSupplier(
                        name=truncated_supplier_name,
                        contact_info=contact_info,
                        address=contact_info
                    )
                    db_session.add(supplier)
                    db_session.commit()

                # Check if the packaging material already exists
                material = db_session.query(PackagingMaterial).filter_by(
                    name=name, packaging_material_supplier_id=supplier.id).first()

                if material:
                    # Update existing material
                    material.available_quantity += quantity
                    material.total_quantity += quantity
                    material.purchase_price_per_unit = cost_per_unit
                    material.total_purchase_cost += total_cost
                    material.available_stock_cost += total_cost
                else:
                    # Add new material
                    material = PackagingMaterial(
                        name=name,
                        packaging_material_supplier_id=supplier.id,
                        total_quantity=quantity,
                        available_quantity=quantity,
                        purchase_price_per_unit=cost_per_unit,
                        reorder_level=0,
                        created_date=purchase_date,
                        total_purchase_cost=total_cost,
                        available_stock_cost=quantity * cost_per_unit
                    )
                    db_session.add(material)
                    db_session.flush()  # Забезпечує генерацію material.id

                # Add to purchase history
                purchase_history = PackagingPurchaseHistory(
                    material_id=material.id,
                    supplier_id=supplier.id,
                    quantity_purchased=quantity,
                    purchase_price_per_unit=cost_per_unit,
                    purchase_total_price=total_cost,
                    purchase_date=purchase_date
                )
                db_session.add(purchase_history)

                # Add to stock history
                stock_history = PackagingStockHistory(
                    material_id=material.id,
                    change_amount=quantity,
                    change_type='purchase',
                    timestamp=purchase_date
                )
                db_session.add(stock_history)

            db_session.commit()
            print(f"Successfully imported packaging materials from {file_path}")
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except IntegrityError as e:
        db_session.rollback()
        print(f"Integrity error: {e}")
    except Exception as e:
        db_session.rollback()
        print(f"Error processing file {file_path}: {e}")


def import_all_packages():
    # Базова папка, яку можна змінити в одному місці
    base_dir = 'import_data_csv/csv_package'

    # Список тільки назв файлів і дат (без повного шляху)
    files_data = [
        ('15.02.2023.csv', "15.02.2023"),
        ('15.03.2023.csv', "15.03.2023"),
        ('15.04.2023.csv', "15.04.2023"),
        ('15.05.2023.csv', "15.05.2023"),
        ('15.06.2023.csv', "15.06.2023"),
        ('15.09.2024.csv', "15.09.2024"),
        ('15.01.2025.csv', "15.01.2025"),
    ]

    # Цикл для виклику функції import_packaging_materials_from_csv для кожного файлу
    for filename, date_str in files_data:
        file_path_package = os.path.join(base_dir, filename)
        purchase_date_package = datetime.strptime(date_str, "%d.%m.%Y").date()
        import_packaging_materials_from_csv(file_path_package, purchase_date_package, db_session)


# import_all_packages()

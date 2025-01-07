from datetime import datetime

import csv
from sqlalchemy.exc import IntegrityError

from app import db_session
from models import PackagingMaterial, Supplier, PackagingMaterialSupplier


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
                truncated_supplier_name = supplier_name[:30]  # Limiting to 30 characters
                contact_info = supplier_name  # Storing full name in contact_info

                # Get or create PackagingMaterialSupplier
                supplier = db_session.query(PackagingMaterialSupplier).filter_by(name=truncated_supplier_name).first()
                if not supplier:
                    supplier = PackagingMaterialSupplier(
                        name=truncated_supplier_name,
                        contact_info=contact_info,  # Storing full supplier name in contact_info
                        address=contact_info
                    )
                    db_session.add(supplier)
                    db_session.commit()

                # Check if the packaging material already exists
                material = db_session.query(PackagingMaterial).filter_by(name=name,
                                                                         packaging_material_supplier_id=supplier.id).first()

                if material:
                    # Update existing material
                    material.available_quantity += quantity
                    material.total_quantity += quantity
                    material.purchase_price_per_unit = cost_per_unit  # Update purchase price per unit
                    material.total_purchase_cost += total_cost  # Update total purchase cost
                    material.available_stock_cost += total_cost  # Update available stock cost
                else:
                    # Add new material
                    material = PackagingMaterial(
                        name=name,
                        packaging_material_supplier_id=supplier.id,
                        total_quantity=quantity,
                        available_quantity=quantity,
                        purchase_price_per_unit=cost_per_unit,
                        reorder_level=0,  # Default value
                        created_date=purchase_date,  # If created_date is set to purchase date
                        total_purchase_cost=total_cost,  # Initial total purchase cost
                        available_stock_cost=quantity * cost_per_unit  # Initial available stock cost
                    )
                    db_session.add(material)

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


# Список з шляхами до CSV-файлів та відповідними датами
files_data = [
    ('csv_package/15.02.2023.csv', "15.02.2023"),
    ('csv_package/15.03.2023.csv', "15.03.2023"),
    ('csv_package/15.04.2023.csv', "15.04.2023"),
    ('csv_package/15.05.2023.csv', "15.05.2023"),
    ('csv_package/15.06.2023.csv', "15.06.2023"),
    ('csv_package/15.09.2023.csv', "15.09.2023"),
]

# Цикл для виклику функції import_packaging_materials_from_csv для кожного файлу
for file_path_package, date_str in files_data:
    purchase_date_package = datetime.strptime(date_str, "%d.%m.%Y").date()
    import_packaging_materials_from_csv(file_path_package, purchase_date_package, db_session)

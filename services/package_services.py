from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from models import PackagingMaterial, PackagingPurchaseHistory, PackagingMaterialSupplier, PackagingStockHistory, \
    PackagingSaleHistory

package_bp = Blueprint('packages', __name__)


@package_bp.route('/api/get_all_packaging_materials', methods=['GET'])
def get_packaging_materials():
    from postgreSQLConnect import db_session

    # Отримуємо всі матеріали з бази даних
    materials = db_session.query(PackagingMaterial).all()  # Corrected query

    # Підготовка результату для відповіді
    materials_data = []
    for material in materials:
        materials_data.append(material.to_dict())  # Use the to_dict() method here

    return jsonify({'materials': materials_data})


@package_bp.route('/api/packaging_materials/purchase', methods=['POST'])
def purchase_packaging_material():
    from postgreSQLConnect import db_session

    data = request.json
    name = data.get('name')
    supplier_id = data.get('supplier_id')
    quantity_purchased = data.get('quantity_purchased')
    purchase_price_per_unit = data.get('purchase_price_per_unit')
    total_purchase_cost = data.get('total_purchase_cost')
    

    if not all([name, supplier_id, quantity_purchased, purchase_price_per_unit]):
        return jsonify({'error': 'Missing required fields'}), 400

    # Check if the material already exists
    material = db_session.query(PackagingMaterial).filter_by(name=name).first()
    if not material:
        # Create a new material
        material = PackagingMaterial(
            name=name,
            packaging_material_supplier_id=supplier_id,
            total_quantity=quantity_purchased,
            available_quantity=quantity_purchased,
            purchase_price_per_unit=purchase_price_per_unit,
            total_purchase_cost=total_purchase_cost,  # Set total purchase cost
            available_stock_cost=total_purchase_cost  # Set available stock cost
        )
        db_session.add(material)
    else:
        # Update existing material
        material.total_quantity += quantity_purchased
        material.available_quantity += quantity_purchased
        material.purchase_price_per_unit = purchase_price_per_unit

        # Update total purchase cost
        material.total_purchase_cost += total_purchase_cost

        # Update available stock cost
        material.available_stock_cost += total_purchase_cost

    # Log purchase history
    purchase_history = PackagingPurchaseHistory(
        material_id=material.id,
        supplier_id=supplier_id,
        quantity_purchased=quantity_purchased,
        purchase_price_per_unit=purchase_price_per_unit,
        purchase_total_price=total_purchase_cost
    )
    db_session.add(purchase_history)

    db_session.commit()

    return jsonify(material.to_dict()), 201


@package_bp.route('/api/get_all_packaging_suppliers', methods=['GET'])
def get_all_suppliers():
    from postgreSQLConnect import db_session

    # Fetch all suppliers
    suppliers = db_session.query(PackagingMaterialSupplier).all()
    suppliers_data = [supplier.to_dict() for supplier in suppliers]
    return jsonify(suppliers_data), 200


@package_bp.route('/api/add_new_packaging_suppliers', methods=['POST'])
def add_supplier():
    data = request.json
    name = data.get('name')
    contact_info = data.get('contact_info')
    from postgreSQLConnect import db_session

    if not name:
        return jsonify({"error": "Supplier name is required"}), 400

    new_supplier = PackagingMaterialSupplier(name=name, contact_info=contact_info)
    db_session.add(new_supplier)
    db_session.commit()
    return jsonify(new_supplier.to_dict()), 201


@package_bp.route('/api/purchase_current_packaging', methods=['POST'])
def purchase_current_packaging_material():
    data = request.json
    material_id = data.get('material_id')
    supplier_id = data.get('supplier_id')
    quantity = data.get('quantity')
    purchase_price_per_unit = data.get('purchase_price_per_unit')
    total_purchase_cost = data.get('total_purchase_cost')
    from postgreSQLConnect import db_session

    if not material_id or not quantity or not purchase_price_per_unit:
        return jsonify({'error': 'Required fields are missing'}), 400

    try:
        # Find material by ID
        material = db_session.query(PackagingMaterial).get(material_id)
        if not material:
            return jsonify({'error': 'Packaging material not found'}), 404

        # Update available quantity and total quantity
        material.available_quantity += quantity
        material.total_quantity += quantity

        # Update total purchase cost and available stock cost
        material.total_purchase_cost += total_purchase_cost
        material.available_stock_cost += total_purchase_cost
        material.purchase_price_per_unit = purchase_price_per_unit

        # Create purchase history record
        purchase_total_price = total_purchase_cost
        purchase_history = PackagingPurchaseHistory(
            material_id=material_id,
            supplier_id=supplier_id,
            quantity_purchased=quantity,
            purchase_price_per_unit=purchase_price_per_unit,
            purchase_total_price=purchase_total_price
        )
        db_session.add(purchase_history)
        db_session.commit()

        return jsonify({'message': 'Purchase successful', 'material': material.to_dict()}), 200
    except SQLAlchemyError as e:
        db_session.rollback()
        return jsonify({'error': 'Database error', 'details': str(e)}), 500


@package_bp.route('/api/update_packaging_status', methods=['OPTIONS', 'POST'])
def update_packaging_status():
    if request.method == 'OPTIONS':
        return '', 200  # Повертає статус 200 для запиту OPTIONS
    data = request.json
    material_id = data.get('material_id')
    quantity_used = data.get('quantity_used')
    from postgreSQLConnect import db_session
    

    if not material_id or not quantity_used:
        return jsonify({'error': 'Required fields are missing'}), 400

    try:
        # Знайти матеріал
        material = db_session.query(PackagingMaterial).get(material_id)
        if not material:
            return jsonify({'error': 'Packaging material not found'}), 404

        # Оновити кількість доступного пакування та відзначити як використане
        if material.available_quantity < quantity_used:
            return jsonify({'error': 'Insufficient quantity available'}), 400

        # Віднімаємо використану кількість
        material.available_quantity -= quantity_used
        material.available_stock_cost -= quantity_used * float(material.purchase_price_per_unit or 0)

        # Встановлюємо статус "used"
        if material.available_quantity == quantity_used:
            material.status = 'used'

        db_session.commit()

        return jsonify({'message': 'Packaging material marked as used', 'material': material.to_dict()}), 200

    except SQLAlchemyError as e:
        db_session.rollback()
        return jsonify({'error': 'Database error', 'details': str(e)}), 500


@package_bp.route('/api/materials/<int:packaging_material_id>/history', methods=['GET'])
def get_packaging_material_history(packaging_material_id):
    from postgreSQLConnect import db_session
    

    # Отримуємо всі історії продажів для конкретного пакування
    sales_history = db_session.query(PackagingSaleHistory).filter(
        PackagingSaleHistory.packaging_material_id == packaging_material_id).all()

    # Отримуємо всі історії закупівель для конкретного пакування
    purchase_history = db_session.query(PackagingPurchaseHistory).filter(
        PackagingPurchaseHistory.material_id == packaging_material_id).all()

    # Отримуємо всі зміни на складі для конкретного пакування
    stock_history = db_session.query(PackagingStockHistory).filter(
        PackagingStockHistory.material_id == packaging_material_id).all()

    # Формуємо результат
    result = {
        'packaging_material_id': packaging_material_id,
        'sales_history': [sale.to_dict() for sale in sales_history],
        'purchase_history': [purchase.to_dict() for purchase in purchase_history],
        'stock_history': [stock.to_dict() for stock in stock_history]
    }

    return result


from flask import jsonify


@package_bp.route('/api/delete_all_materials', methods=['DELETE'])
def delete_all_packaging_materials():
    from postgreSQLConnect import db_session
    try:
        # Видалення всіх упаковочних матеріалів разом з пов'язаними даними
        db_session.query(PackagingMaterial).delete(synchronize_session=False)
        db_session.query(PackagingStockHistory).delete(synchronize_session=False)
        db_session.query(PackagingPurchaseHistory).delete(synchronize_session=False)

        # Підтвердження змін
        db_session.commit()
        print("Усі упаковочні матеріали та пов'язані дані були успішно видалені.")

        # Повернення відповіді у разі успіху
        return jsonify({'message': 'Усі упаковочні матеріали та пов’язані дані були успішно видалені.'}), 200
    except Exception as e:
        # Якщо сталася помилка, скасувати зміни
        db_session.rollback()
        print(f"Сталася помилка: {e}")

        # Повернення відповіді у разі помилки
        return jsonify({'error': f'Сталася помилка: {str(e)}'}), 500
    finally:
        # Закрити сесію
        db_session.close()

from flask import Blueprint, jsonify
from database import db_session
from models import PackagingMaterial

package_bp = Blueprint('packages', __name__)


@package_bp.route('/api/get_all_packaging_materials', methods=['GET'])
def get_packaging_materials():
    # Отримуємо всі матеріали з бази даних
    materials = db_session.query(PackagingMaterial).all()  # Corrected query

    # Підготовка результату для відповіді
    materials_data = []
    for material in materials:
        materials_data.append(material.to_dict())  # Use the to_dict() method here

    return jsonify({'materials': materials_data})

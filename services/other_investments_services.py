from flask import Blueprint, request, jsonify

from models import OtherInvestment, db_session
from datetime import datetime

investments_bp = Blueprint('investments', __name__)


# Додати нове вкладення
@investments_bp.route('/api/create_new_investments', methods=['POST'])
def add_investment():
    data = request.json

    try:
        new_investment = OtherInvestment(
            type_name=data['type_name'],
            cost=data['cost'],
            date=datetime.strptime(data['date'], '%Y-%m-%d')
        )
        db_session.add(new_investment)
        db_session.commit()
        return jsonify({"message": "Investment added successfully"}), 201
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db_session.close()


# Отримати всі вкладення
@investments_bp.route('/api/gel_all_investments', methods=['GET'])
def get_investments():
    investments = db_session.query(OtherInvestment).all()
    db_session.close()
    return jsonify([{
        "id": inv.id,
        "type_name": inv.type_name,
        "cost": inv.cost,
        "supplier": inv.supplier,
        "date": inv.date.strftime('%Y-%m-%d')
    } for inv in investments])


# Видалити вкладення
@investments_bp.route('/investments/<int:id>', methods=['DELETE'])
def delete_investment(id):
    investment = db_session.query(OtherInvestment).get(id)

    if not investment:
        return jsonify({"error": "Investment not found"}), 404

    try:
        db_session.delete(investment)
        db_session.commit()
        return jsonify({"message": "Investment deleted successfully"})
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db_session.close()

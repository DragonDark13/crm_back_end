from flask import Blueprint, request, jsonify
from flask_restx import Resource
from sqlalchemy.exc import SQLAlchemyError

from api.investment_api import investments_ns, investment_model
from models import OtherInvestment
from datetime import datetime


investments_bp = Blueprint('investments', __name__)


# Додати нове вкладення
@investments_bp.route('/create_new_investments', methods=['POST'])
def add_investment():
    data = request.json
    from postgreSQLConnect import db_session

    try:
        new_investment = OtherInvestment(
            type_name=data['type_name'],
            supplier=data['supplier'],
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


@investments_ns.route("/get_all_investments")
class InvestmentList(Resource):

    @investments_ns.doc(
        summary="Отримати всі вкладення",
        description="Повертає список усіх інших вкладень"
    )
    @investments_ns.marshal_list_with(investment_model)
    def get(self):
        from postgreSQLConnect import db_session

        investments = db_session.query(OtherInvestment).all()

        return [{
            "id": inv.id,
            "type_name": inv.type_name,
            "cost": float(inv.cost),
            "supplier": inv.supplier,
            "date": inv.date.strftime('%Y-%m-%d')
        } for inv in investments], 200

# Видалити вкладення
@investments_bp.route('/delete_investments/<int:investments_id>', methods=['DELETE'])
def delete_investment(investments_id: int):
    from postgreSQLConnect import db_session
    try:
        investment = db_session.query(OtherInvestment).get(investments_id)

        if not investment:
            print(f"Не знайдено інвестицію з ID {investments_id}")
            return jsonify({"error": "Investment not found"}), 404

        db_session.delete(investment)
        db_session.commit()
        print(f"Інвестиція з ID {investments_id} успішно видалена")
        return jsonify({"message": "Investment deleted successfully"}), 200

    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 400

    finally:
        db_session.close()



@investments_bp.route('/delete_all_investments', methods=['DELETE'])
def delete_all_investments():
    from postgreSQLConnect import db_session

    """
    Видалення всіх записів з таблиці OtherInvestment.
    """
    try:
        # Видалення записів з таблиці
        db_session.query(OtherInvestment).delete(synchronize_session=False)

        # Збереження змін
        db_session.commit()
        return jsonify({"message": "Усі записи з таблиці OtherInvestment успішно видалено."}), 200
    except SQLAlchemyError as e:
        # У разі помилки відкотити транзакцію
        db_session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        # Закриття сесії
        db_session.close()

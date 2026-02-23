from flask_restx import Namespace, fields

investments_ns = Namespace(
    "investments",
    description="Інші вкладення / інвестиції"
)

investment_model = investments_ns.model("Investment", {
    "id": fields.Integer(description="ID вкладення"),
    "type_name": fields.String(description="Тип вкладення"),
    "cost": fields.Float(description="Сума витрат"),
    "supplier": fields.String(description="Постачальник"),
    "date": fields.String(description="Дата вкладення (YYYY-MM-DD)")
})
from flask_restx import Namespace, Resource, fields

categories_ns = Namespace(
    "categories",
    description="Операції з Категоріями"
)
category_model = categories_ns.model("Category", {
    "id": fields.Integer(description="ID категорії"),
    "name": fields.String(description="Назва категорії")
})

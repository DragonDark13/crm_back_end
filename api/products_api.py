from flask_restx import Namespace, Resource
from services.product_service import ProductService

products_ns = Namespace(
    "products",
    description="Операції з товарами"
)

@products_ns.route("/")
class ProductList(Resource):
    def get(self):
        """
        Отримати всі товари
        """
        products, status = ProductService.get_all_products()
        return products, status
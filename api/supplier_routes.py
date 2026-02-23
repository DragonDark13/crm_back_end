from flask_restx import Namespace, Resource, fields
from postgreSQLConnect import db_session

supplier_ns = Namespace(
    "suppliers",
    description="Робота з постачальниками товарів та пакування"
)



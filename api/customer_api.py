from flask_restx import Namespace, Resource, fields
from postgreSQLConnect import db_session
from models.customer import Customer  # шлях підкоригуй

customers_ns = Namespace(
    "customers",
    description="Клієнти"
)

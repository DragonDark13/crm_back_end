from postgreSQLConnect import db_session
from services.product_service import delete_all_products

delete_all_products()

# Закриття сесії
db_session.close()

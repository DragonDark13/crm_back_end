# Виконайте видалення всіх записів
from database import db_session
from models import OtherInvestment

db_session.query(OtherInvestment).delete()

# Збережіть зміни в базі даних
db_session.commit()

# Закрийте сесію
db_session.close()

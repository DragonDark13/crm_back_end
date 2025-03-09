from flask import Flask
from models import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:admin@localhost:5432/shop_crm_post"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


def create_tables():
    with app.app_context():
        db.create_all()
        print("✅ Таблиці створено успішно!")


if __name__ == "__main__":
    create_tables()

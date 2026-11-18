import os
from dotenv import load_dotenv
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from models import db

load_dotenv()

# PostgreSQL connection configuration
DATABASE_URI = os.getenv("DATABASE_URL")
if not DATABASE_URI:
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    if not all([db_name, db_user, db_password]):
        raise RuntimeError("DATABASE_URL or DB_NAME, DB_USER and DB_PASSWORD environment variables are required")
    DATABASE_URI = f"postgresql://{quote_plus(db_user)}:{quote_plus(db_password)}@{db_host}:{db_port}/{db_name}"

engine = create_engine(
    DATABASE_URI,
    echo=False,
    pool_size=25,
    max_overflow=20,
    pool_timeout=30
)


def test_connection():
    try:
        with engine.connect() as connection:
            print("[OK] Зʼєднання з базою даних успішне!")
            return True
    except Exception as e:
        print(f"[ERROR] Помилка підключення до бази: {e}")
        return False


Session = sessionmaker(bind=engine)
db_session = scoped_session(Session)

def remove_session():
    """Release the current request-scoped SQLAlchemy session."""
    db_session.remove()

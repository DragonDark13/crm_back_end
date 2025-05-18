from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base  # Adjust the import if needed

# Define your database URI (update to match your local setup)
DATABASE_URI = 'sqlite:///shop_crm.db'  # SQLite database in the root folder

# Create the engine
engine = create_engine(DATABASE_URI, echo=True, pool_size=25, max_overflow=20, pool_timeout=30)

# Create a configured "Session" class
Session = sessionmaker(bind=engine)

# Scoped session to manage thread-local sessions
db_session = scoped_session(Session)


# Initialize the database (create tables if not exist)
def init_db():
    Base.metadata.create_all(bind=engine)

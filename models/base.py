from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Define your base model
Base = db.Model  # Use SQLAlchemy's model base
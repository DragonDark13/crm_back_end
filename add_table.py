from models import Customer, db

if __name__ == "__main__":
    # Connect to the database
    db.connect()

    # Create tables
    db.drop_tables([Customer])
    db.create_tables([Customer])

    print("Tables added successfully!")

    # Close the database connection
    db.close()

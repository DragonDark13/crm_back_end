from peewee import *
from peewee_migrate import Migrator
from playhouse.migrate import *

# Define your database
db = SqliteDatabase('shop_crm.db')

# Initialize the migrator
migrator = Migrator(db)

# Start a transaction
with db.transaction():
    # Add new fields to the Product table
    migrator.add_fields('product',
        purchase_total_price=DecimalField(max_digits=10, decimal_places=2, default=0.00),
        purchase_price_per_item=DecimalField(max_digits=10, decimal_places=2, default=0.00),
        selling_total_price=DecimalField(max_digits=10, decimal_places=2, default=0.00),
        selling_price_per_item=DecimalField(max_digits=10, decimal_places=2, default=0.00),
    )

# Close the database connection
db.close()

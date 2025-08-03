import os
import sqlite3
from app import create_app, init_db

# Create an app context to use Flask's features
app = create_app()

with app.app_context():
    # Define the paths to your instance folder and database file
    instance_path = app.instance_path
    db_path = os.path.join(instance_path, 'alfurqa_academy.db')

    # Ensure the instance directory exists
    os.makedirs(instance_path, exist_ok=True)

    # Delete old database file if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Old database deleted.")

    # Initialize the database and create all tables from schema.sql
    init_db()

print("Database initialized and 'admin' user created successfully!")

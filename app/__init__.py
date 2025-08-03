# app/__init__.py
import os
import sqlite3
from flask import Flask, g
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

# Helper function to get the database connection
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(os.path.join('instance', 'database.db'))
        db.row_factory = sqlite3.Row # Enable dictionary-like row access
    return db

# Helper function to close the database connection
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    
    # Configure the app
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'database.db')
    )

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize Bcrypt with the app
    bcrypt.init_app(app)

    # Register the database connection teardown function
    app.teardown_appcontext(close_connection)

    from . import models
    with app.app_context():
        models.init_db()

    # Register the blueprint
    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app
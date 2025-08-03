# run.py
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Default users for testing:
    # Admin: username 'admin', password 'admin'
    # Official: username 'official', password 'official'
    app.run(debug=True, host='0.0.0.0')
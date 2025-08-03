# app/models.py
from . import get_db, bcrypt

def init_db():
    db = get_db()
    cursor = db.cursor()

    # Create tables if they don't exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
    if not cursor.fetchone():
        cursor.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            );
        ''')
        # Insert a default admin user
        hashed_admin_password = bcrypt.generate_password_hash("admin").decode('utf-8')
        cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                       ('admin', hashed_admin_password, 'admin'))
        
        # Insert a default official user
        hashed_official_password = bcrypt.generate_password_hash("official").decode('utf-8')
        cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                       ('official', hashed_official_password, 'official'))
                       
        db.commit()
        print("Default 'admin' and 'official' users created.")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='students';")
    if not cursor.fetchone():
        cursor.execute('''
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reg_number TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                class TEXT NOT NULL,
                term TEXT NOT NULL,
                academic_year TEXT NOT NULL
            );
        ''')
        db.commit()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='fees';")
    if not cursor.fetchone():
        cursor.execute('''
            CREATE TABLE fees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                amount REAL,
                due_date TEXT,
                FOREIGN KEY (student_id) REFERENCES students (id)
            );
        ''')
        db.commit()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payments';")
    if not cursor.fetchone():
        cursor.execute('''
            CREATE TABLE payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_reg_number TEXT,
                payment_date TEXT,
                amount_paid REAL,
                term TEXT,
                academic_year TEXT,
                recorded_by TEXT,
                FOREIGN KEY (student_reg_number) REFERENCES students (reg_number)
            );
        ''')
        db.commit()

    print("Database initialized successfully!")
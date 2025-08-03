import sqlite3
import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from . import get_db, bcrypt

# Create a Blueprint for the main routes.
main_bp = Blueprint('main', __name__)

# Context processor to make 'now' available in all templates
@main_bp.context_processor
def inject_now():
    return {'now': datetime.datetime.utcnow()}

def is_admin():
    """Checks if the current user is an admin."""
    return session.get('role') == 'admin'

def is_official():
    """Checks if the current user is an official or an admin."""
    return session.get('role') in ['admin', 'official']

def get_current_user():
    """Retrieves the current logged-in user from the database."""
    if 'user_id' in session:
        db = get_db()
        cursor = db.cursor()
        user = cursor.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        return user
    return None

@main_bp.before_request
def check_user_before_request():
    """
    Checks for the current user before every request.
    This makes the `user` variable available in templates.
    """
    g.user = get_current_user()

@main_bp.route('/', methods=['GET', 'POST'])
def login():
    """Admin and official login page."""
    if get_current_user():
        if is_admin():
            return redirect(url_for('main.dashboard'))
        elif is_official():
            return redirect(url_for('main.official_dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor()
        user = cursor.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user and bcrypt.check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Logged in successfully!', 'success')
            if is_admin():
                return redirect(url_for('main.dashboard'))
            else: # Must be an official
                return redirect(url_for('main.official_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    """Logs the user out by clearing the session."""
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.login'))

@main_bp.route('/dashboard')
def dashboard():
    """
    Admin dashboard. Only accessible by 'admin' role.
    """
    if not is_admin():
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('main.login'))

    db = get_db()
    cursor = db.cursor()

    # --- Fetching Summary Card Data ---
    # Total Students
    total_students_result = cursor.execute('SELECT COUNT(*) FROM students').fetchone()
    total_students = total_students_result[0] if total_students_result else 0

    # Expected Revenue
    total_expected_revenue_result = cursor.execute('SELECT SUM(amount) FROM fees').fetchone()
    total_expected_revenue = total_expected_revenue_result[0] if total_expected_revenue_result[0] is not None else 0
    
    # Received Revenue
    total_received_revenue_result = cursor.execute('SELECT SUM(amount_paid) FROM payments').fetchone()
    total_received_revenue = total_received_revenue_result[0] if total_received_revenue_result[0] is not None else 0

    # Outstanding Revenue
    total_outstanding_revenue = total_expected_revenue - total_received_revenue

    # Fetch financial data per student to determine paid/partially paid/defaulters
    student_financials = cursor.execute('''
        SELECT
            s.reg_number,
            s.name,
            s.class,
            s.term,
            s.academic_year,
            SUM(CASE WHEN f.id IS NOT NULL THEN f.amount ELSE 0 END) as total_fees,
            COALESCE(SUM(p.amount_paid), 0) as total_paid
        FROM students s
        LEFT JOIN fees f ON s.id = f.student_id
        LEFT JOIN payments p ON s.reg_number = p.student_reg_number
        GROUP BY s.reg_number
    ''').fetchall()

    paid_students_count = 0
    defaulters_count = 0
    partially_paid_count = 0
    outstanding_defaulter_students = []
    outstanding_partially_paid_students = []

    for student in student_financials:
        outstanding_amount = student['total_fees'] - student['total_paid']
        
        if outstanding_amount <= 0:
            paid_students_count += 1
        else:
            if student['total_paid'] == 0:
                defaulters_count += 1
                outstanding_defaulter_students.append({
                    'reg_no': student['reg_number'],
                    'name': student['name'],
                    'class': student['class'],
                    'term': student['term'],
                    'academic_year': student['academic_year'],
                    'outstanding_amount': outstanding_amount
                })
            else:
                partially_paid_count += 1
                outstanding_partially_paid_students.append({
                    'reg_no': student['reg_number'],
                    'name': student['name'],
                    'class': student['class'],
                    'term': student['term'],
                    'academic_year': student['academic_year'],
                    'outstanding_amount': outstanding_amount
                })

    # --- Fetching Recent Payments Data ---
    recent_payments = cursor.execute('''
        SELECT p.payment_date, p.term, p.academic_year, p.amount_paid, p.recorded_by, s.name
        FROM payments p
        JOIN students s ON p.student_reg_number = s.reg_number
        ORDER BY p.payment_date DESC
        LIMIT 10
    ''').fetchall()

    return render_template(
        'dashboard.html',
        total_students=total_students,
        paid_students_count=paid_students_count,
        defaulters_count=defaulters_count,
        partially_paid_count=partially_paid_count,
        total_expected_revenue=total_expected_revenue,
        total_received_revenue=total_received_revenue,
        total_outstanding_revenue=total_outstanding_revenue,
        outstanding_defaulter_students=outstanding_defaulter_students,
        outstanding_partially_paid_students=outstanding_partially_paid_students,
        recent_payments=recent_payments
    )

@main_bp.route('/official_dashboard')
def official_dashboard():
    """
    Official's dashboard. Accessible by 'admin' and 'official' roles.
    """
    if not is_official():
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('main.login'))
    
    return render_template('official_dashboard.html')

@main_bp.route('/register_student', methods=['GET', 'POST'])
def register_student():
    """
    Official route to register a new student.
    Accessible by 'admin' and 'official' roles.
    """
    if not is_official():
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        reg_number = request.form['reg_number']
        name = request.form['name']
        class_name = request.form['class']
        term = request.form['term']
        academic_year = request.form['academic_year']

        db = get_db()
        cursor = db.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO students (reg_number, name, class, term, academic_year)
                VALUES (?, ?, ?, ?, ?)
            ''', (reg_number, name, class_name, term, academic_year))
            db.commit()
            flash(f"Student '{name}' registered successfully!", 'success')
            return redirect(url_for('main.register_student'))
        except sqlite3.IntegrityError:
            flash(f"A student with registration number '{reg_number}' already exists.", 'danger')
    
    return render_template('register_student.html')

@main_bp.route('/record_payment', methods=['GET', 'POST'])
def record_payment():
    """
    Official route to record a new student payment.
    Accessible by 'admin' and 'official' roles.
    """
    if not is_official():
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        student_reg_number = request.form['student_reg_number']
        amount_paid = request.form['amount_paid']
        payment_date = request.form['payment_date']
        term = request.form['term']
        academic_year = request.form['academic_year']
        recorded_by = session.get('username')

        db = get_db()
        cursor = db.cursor()
        
        # Check if the student exists
        student = cursor.execute('SELECT id FROM students WHERE reg_number = ?', (student_reg_number,)).fetchone()
        if not student:
            flash(f"Student with registration number '{student_reg_number}' not found.", 'danger')
            return redirect(url_for('main.record_payment'))

        try:
            cursor.execute('''
                INSERT INTO payments (student_reg_number, amount_paid, payment_date, term, academic_year, recorded_by)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (student_reg_number, amount_paid, payment_date, term, academic_year, recorded_by))
            db.commit()
            flash(f"Payment of ₦{amount_paid} recorded for student '{student_reg_number}' successfully!", 'success')
            return redirect(url_for('main.record_payment'))
        except Exception as e:
            flash(f"An error occurred: {str(e)}", 'danger')

    return render_template('record_payment.html')

@main_bp.route('/admin/create_official', methods=['GET', 'POST'])
def create_official():
    """
    Admin route to create a new official (user with 'official' role).
    Only accessible by 'admin' role.
    """
    if not is_admin():
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        db = get_db()
        cursor = db.cursor()
        
        try:
            cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                           (username, hashed_password, 'official'))
            db.commit()
            flash(f"New official '{username}' created successfully!", 'success')
            return redirect(url_for('main.dashboard'))
        except sqlite3.IntegrityError:
            flash(f"Username '{username}' already exists. Please choose a different one.", 'danger')

    return render_template('create_official.html')

@main_bp.route('/students', defaults={'class_name': None})
@main_bp.route('/students/<class_name>')
def students(class_name):
    """Displays a list of all students or students of a specific class. Only accessible by 'admin' role."""
    if not is_admin():
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('main.login'))

    db = get_db()
    cursor = db.cursor()

    # Get a list of all unique class names for the navigation menu
    classes = [row['class'] for row in cursor.execute('SELECT DISTINCT class FROM students ORDER BY class').fetchall()]

    if class_name:
        # Fetch students for a specific class
        students_list = cursor.execute('SELECT * FROM students WHERE class = ? ORDER BY name', (class_name,)).fetchall()
        page_title = f"Students in {class_name}"
    else:
        # If no class is specified, fetch all students
        students_list = cursor.execute('SELECT * FROM students ORDER BY name').fetchall()
        page_title = "All Students"
        
    return render_template('students.html', students=students_list, classes=classes, page_title=page_title)

@main_bp.route('/fees')
def fees():
    """Displays a list of student fees. Only accessible by 'admin' role."""
    if not is_admin():
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('main.login'))

    db = get_db()
    cursor = db.cursor()
    fees_list = cursor.execute('''
        SELECT f.*, s.name as student_name, s.reg_number as student_reg_number
        FROM fees f
        JOIN students s ON f.student_id = s.id
        ORDER BY f.due_date DESC
    ''').fetchall()
    return render_template('fees.html', fees=fees_list)

@main_bp.route('/payments')
def payments():
    """Displays a list of all payments. Only accessible by 'admin' role."""
    if not is_admin():
        flash('You do not have permission to view this page.', 'danger')
        return redirect(url_for('main.login'))

    db = get_db()
    cursor = db.cursor()
    payments_list = cursor.execute('''
        SELECT p.*, s.name as student_name FROM payments p JOIN students s ON p.student_reg_number = s.reg_number ORDER BY p.payment_date DESC
    ''').fetchall()
    return render_template('payments.html', payments=payments_list)

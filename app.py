import os
import secrets
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session, g, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

# Define a simple fee structure for demonstration purposes.
FEE_STRUCTURE = {
    ('Nur. 1', 'First Term'): 50000.00,
    ('Nur. 1', 'Second Term'): 45000.00,
    ('Nur. 1', 'Third Term'): 40000.00,
    ('Nur. 2', 'First Term'): 52000.00,
    ('Nur. 2', 'Second Term'): 47000.00,
    ('Nur. 2', 'Third Term'): 42000.00,
    ('Nur. 3', 'First Term'): 55000.00,
    ('Nur. 3', 'Second Term'): 50000.00,
    ('Nur. 3', 'Third Term'): 45000.00,
    ('Basic 1', 'First Term'): 60000.00,
    ('Basic 1', 'Second Term'): 55000.00,
    ('Basic 1', 'Third Term'): 50000.00,
    ('Basic 2', 'First Term'): 62000.00,
    ('Basic 2', 'Second Term'): 57000.00,
    ('Basic 2', 'Third Term'): 52000.00,
    ('Basic 3', 'First Term'): 65000.00,
    ('Basic 3', 'Second Term'): 60000.00,
    ('Basic 3', 'Third Term'): 55000.00,
    ('JSS 1', 'First Term'): 70000.00,
    ('JSS 1', 'Second Term'): 65000.00,
    ('JSS 1', 'Third Term'): 60000.00,
    ('JSS 2', 'First Term'): 72000.00,
    ('JSS 2', 'Second Term'): 67000.00,
    ('JSS 2', 'Third Term'): 62000.00,
    ('JSS 3', 'First Term'): 75000.00,
    ('JSS 3', 'Second Term'): 70000.00,
    ('JSS 3', 'Third Term'): 65000.00,
    ('SS 1', 'First Term'): 80000.00,
    ('SS 1', 'Second Term'): 75000.00,
    ('SS 1', 'Third Term'): 70000.00,
    ('SS 2', 'First Term'): 82000.00,
    ('SS 2', 'Second Term'): 77000.00,
    ('SS 2', 'Third Term'): 72000.00,
    ('SS 3', 'First Term'): 85000.00,
    ('SS 3', 'Second Term'): 80000.00,
    ('SS 3', 'Third Term'): 75000.00,
}


def get_current_school_period():
    current_year = datetime.now().year
    if datetime.now().month < 8:
        academic_year = f"{current_year - 1}/{current_year}"
    else:
        academic_year = f"{current_year}/{current_year + 1}"
    current_month = datetime.now().month
    if 9 <= current_month <= 12:
        current_term = "First Term"
    elif 1 <= current_month <= 4:
        current_term = "Second Term"
    else:
        current_term = "Third Term"
    return academic_year, current_term


def format_currency_filter(value):
    try:
        return "{:,.2f}".format(float(value))
    except (ValueError, TypeError):
        return value


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20))

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    reg_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    dob = db.Column(db.String(20))
    gender = db.Column(db.String(10))
    address = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    student_class = db.Column(db.String(50))
    term = db.Column(db.String(50))
    academic_year = db.Column(db.String(20))
    admission_date = db.Column(db.String(20))

class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    student_reg_number = db.Column(db.String(50), db.ForeignKey('students.reg_number'), nullable=False)
    term = db.Column(db.String(50))
    academic_year = db.Column(db.String(20))
    amount_paid = db.Column(db.Float)
    payment_date = db.Column(db.String(20))
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)


def get_fee_status(student_reg_number, academic_year_check, term_check):
    student = Student.query.filter_by(reg_number=student_reg_number).first()
    if not student:
        return 'N/A'
    
    expected_fee = FEE_STRUCTURE.get((student.student_class, term_check), 0.0)
    total_paid = db.session.query(db.func.sum(Payment.amount_paid)).filter(
        Payment.student_reg_number == student_reg_number,
        Payment.term == term_check,
        Payment.academic_year == academic_year_check
    ).scalar() or 0.0
    
    if expected_fee > 0:
        if total_paid >= expected_fee:
            return 'Paid'
        else:
            return 'Defaulter'
    else:
        return 'N/A'


def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    app.jinja_env.filters['format_currency'] = format_currency_filter

    @app.route('/create_first_admin')
    def create_first_admin():
        try:
            existing_user = User.query.filter_by(username='admin').first()
            if existing_user:
                flash('Admin user already exists. You can log in.', 'info')
                return redirect(url_for('login'))

            hashed_password = generate_password_hash('admin')
            first_admin = User(username='admin', password=hashed_password, role='admin')
            db.session.add(first_admin)
            db.session.commit()
            
            flash('First admin user created successfully. You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('login'))

    @app.route('/')
    @login_required
    def index():
        students = Student.query.order_by(Student.admission_date.desc()).limit(5).all()
        current_academic_year, current_term = get_current_school_period()
        students_with_status = []
        for student in students:
            student.fee_status = get_fee_status(student.reg_number, current_academic_year, current_term)
            students_with_status.append(student)

        return render_template('index.html', students=students_with_status)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
            
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                login_user(user)
                flash('Login successful!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password.', 'error')
        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('Username already exists. Please choose a different one.', 'error')
            else:
                hashed_password = generate_password_hash(password)
                new_user = User(username=username, password=hashed_password, role='user')
                db.session.add(new_user)
                db.session.commit()
                flash('Registration successful! You can now log in.', 'success')
                return redirect(url_for('login'))
        return render_template('register.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('login'))
        
    @app.route('/register_student', methods=('GET', 'POST'))
    @login_required
    def register_student():
        if current_user.role != 'admin':
            abort(403)
            
        if request.method == 'POST':
            reg_number = request.form['reg_number'].strip()
            name = request.form['name'].strip()
            dob = request.form['dob'].strip()
            gender = request.form['gender'].strip()
            address = request.form['address'].strip()
            phone = request.form['phone'].strip()
            email = request.form['email'].strip()
            student_class = request.form['class'].strip()
            term = request.form['term'].strip()
            academic_year = request.form['academic_year'].strip()
            admission_date = datetime.now().strftime('%Y-%m-%d')
            
            existing_student = Student.query.filter_by(reg_number=reg_number).first()
            if existing_student:
                flash(f'Error: Student with Registration Number {reg_number} already exists.', 'error')
            else:
                try:
                    new_student = Student(
                        reg_number=reg_number,
                        name=name,
                        dob=dob,
                        gender=gender,
                        address=address,
                        phone=phone,
                        email=email,
                        student_class=student_class,
                        term=term,
                        academic_year=academic_year,
                        admission_date=admission_date
                    )
                    db.session.add(new_student)
                    db.session.commit()
                    flash(f'Student {name} registered successfully!', 'success')
                    return redirect(url_for('student_details', reg_number=reg_number))
                except Exception as e:
                    db.session.rollback()
                    flash(f'Database error: {e}', 'error')

        classes = sorted(list(set(item[0] for item in FEE_STRUCTURE.keys())))
        terms = sorted(list(set(item[1] for item in FEE_STRUCTURE.keys())))
        current_year_val = datetime.now().year
        academic_years = [f"{y}/{y+1}" for y in range(current_year_val - 2, current_year_val + 3)]

        return render_template('register_student.html', classes=classes, terms=terms, academic_years=academic_years)
        
    @app.route('/students', defaults={'student_class': None})
    @app.route('/students/<student_class>')
    @login_required
    def student_list(student_class):
        status_filter = request.args.get('status', 'all')
        class_filter = student_class or request.args.get('class', 'all')
        term_filter = request.args.get('term', 'all')
        search_query = request.args.get('search_query', '').strip()

        query = Student.query

        if search_query:
            query = query.filter(db.or_(Student.name.like(f'%{search_query}%'), Student.reg_number.like(f'%{search_query}%')))
        if class_filter != 'all' and class_filter is not None:
            query = query.filter_by(student_class=class_filter)
        if term_filter != 'all':
            query = query.filter_by(term=term_filter)

        students_data = query.order_by(Student.name).all()
        
        current_academic_year, current_term_for_status = get_current_school_period()
        students_with_status = []
        for student in students_data:
            student.fee_status = get_fee_status(student.reg_number, current_academic_year, current_term_for_status)
            students_with_status.append(student)

        if status_filter != 'all':
            students_with_status = [s for s in students_with_status if s.fee_status == status_filter]

        all_classes = sorted(list(set(s.student_class for s in Student.query.all())))
        all_terms = sorted(list(set(s.term for s in Student.query.all())))

        return render_template(
            'student_list.html',
            students=students_with_status,
            status_filter=status_filter,
            class_filter=class_filter,
            term_filter=term_filter,
            search_query=search_query,
            classes=all_classes,
            terms=all_terms
        )

    @app.route('/student/<reg_number>')
    @login_required
    def student_details(reg_number):
        student = Student.query.filter_by(reg_number=reg_number).first()
        if student is None:
            flash('Student not found!', 'error')
            return redirect(url_for('student_list'))

        payments = Payment.query.filter_by(student_reg_number=reg_number).order_by(
            Payment.payment_date.desc(),
            Payment.academic_year.desc(),
            Payment.term.desc()
        ).all()
        current_academic_year, current_term = get_current_school_period()
        student_fee_status = get_fee_status(reg_number, current_academic_year, current_term)
        
        fee_breakdown = {}
        all_years_terms = set()
        
        if student.academic_year and student.term:
            all_years_terms.add((student.academic_year, student.term))
        for p in payments:
            all_years_terms.add((p.academic_year, p.term))
        all_years_terms.add((current_academic_year, current_term))
        
        for year, term in sorted(list(all_years_terms)):
            expected_fee_key = (student.student_class, term)
            expected_amount = FEE_STRUCTURE.get(expected_fee_key, 0.0)

            total_paid_for_period = db.session.query(db.func.sum(Payment.amount_paid)).filter(
                Payment.student_reg_number == reg_number,
                Payment.term == term,
                Payment.academic_year == year
            ).scalar() or 0.0
            
            outstanding_amount = expected_amount - total_paid_for_period

            fee_breakdown[f"{term} {year}"] = {
                'expected': expected_amount,
                'paid': total_paid_for_period,
                'outstanding': outstanding_amount
            }
        
        def sort_key_for_fee_breakdown(item):
            period_str = item[0]
            parts = period_str.split(' ')
            term_name = ' '.join(parts[:-1]) if len(parts) > 1 else parts[0]
            year_part = parts[-1] if len(parts) > 1 else ""
            
            try:
                start_year = int(year_part.split('/')[0])
            except (ValueError, IndexError):
                start_year = 0
            
            term_order = ['First Term', 'Second Term', 'Third Term']
            try:
                term_index = term_order.index(term_name)
            except ValueError:
                term_index = -1
            
            return (start_year, term_index)

        sorted_fee_breakdown = sorted(fee_breakdown.items(), key=sort_key_for_fee_breakdown, reverse=True)
        sorted_fee_breakdown_dict = {k: v for k, v in sorted_fee_breakdown}

        return render_template('student_details.html',
                               student=student,
                               payments=payments,
                               fee_status=student_fee_status,
                               fee_breakdown=sorted_fee_breakdown_dict,
                               current_academic_year=current_academic_year,
                               current_term=current_term
                               )

    @app.route('/make_payment/<reg_number>', methods=['GET', 'POST'])
    @login_required
    def make_payment(reg_number):
        if current_user.role != 'admin':
            abort(403)
            
        student = Student.query.filter_by(reg_number=reg_number).first()
        if student is None:
            flash('Student not found!', 'error')
            return redirect(url_for('student_list'))

        if request.method == 'POST':
            amount_str = request.form['amount_paid'].strip()
            term = request.form['term'].strip()
            academic_year = request.form['academic_year'].strip()
            recorded_by_user = current_user.id
            
            try:
                amount_paid = float(amount_str)
                if amount_paid <= 0:
                    flash('Payment amount must be positive.', 'error')
                else:
                    payment_date = datetime.now().strftime('%Y-%m-%d')
                    new_payment = Payment(
                        student_reg_number=reg_number,
                        term=term,
                        academic_year=academic_year,
                        amount_paid=amount_paid,
                        payment_date=payment_date,
                        recorded_by=recorded_by_user
                    )
                    db.session.add(new_payment)
                    db.session.commit()
                    flash(f'Payment of ₦{amount_paid:,.2f} recorded for {student.name} for {term} {academic_year}.', 'success')
                    return redirect(url_for('student_details', reg_number=reg_number))
            except ValueError:
                flash('Invalid amount. Please enter a valid number.', 'error')
            except Exception as e:
                db.session.rollback()
                flash(f'Database error: {e}', 'error')

        terms = sorted(list(set(item[1] for item in FEE_STRUCTURE.keys())))
        current_year_val = datetime.now().year
        academic_years = [f"{y}/{y+1}" for y in range(current_year_val - 2, current_year_val + 3)]
        
        pre_selected_academic_year, pre_selected_term = get_current_school_period()

        return render_template('make_payment.html',
                               student=student,
                               terms=terms,
                               academic_years=academic_years,
                               pre_selected_term=pre_selected_term,
                               pre_selected_academic_year=pre_selected_academic_year)

    @app.route('/edit_student/<reg_number>', methods=['GET', 'POST'])
    @login_required
    def edit_student(reg_number):
        student = Student.query.filter_by(reg_number=reg_number).first_or_404()
        if current_user.role != 'admin':
            abort(403)
            
        if request.method == 'POST':
            try:
                student.name = request.form['name'].strip()
                student.dob = request.form['dob'].strip()
                student.gender = request.form['gender'].strip()
                student.address = request.form['address'].strip()
                student.phone = request.form['phone'].strip()
                student.email = request.form['email'].strip()
                student.student_class = request.form['class'].strip()
                student.term = request.form['term'].strip()
                student.academic_year = request.form['academic_year'].strip()
                db.session.commit()
                flash(f'Student {student.name} updated successfully!', 'success')
                return redirect(url_for('student_details', reg_number=reg_number))
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating student: {e}', 'error')

        classes = sorted(list(set(item[0] for item in FEE_STRUCTURE.keys())))
        terms = sorted(list(set(item[1] for item in FEE_STRUCTURE.keys())))
        current_year_val = datetime.now().year
        academic_years = [f"{y}/{y+1}" for y in range(current_year_val - 2, current_year_val + 3)]

        return render_template('edit_student.html', student=student, classes=classes, terms=terms, academic_years=academic_years)

    return app

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

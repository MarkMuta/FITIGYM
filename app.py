from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from db_config import get_connection
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import pymysql
from mpesa_api import initiate_stk_push

app = Flask(__name__)

# Load environment variables
load_dotenv()

# MySQL configurations
app.config['MYSQL_HOST'] = os.getenv('DB_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('DB_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASSWORD', '1536Entartic-8292')
app.config['MYSQL_DB'] = os.getenv('DB_NAME', 'fitigym_db')

# Initialize MySQL
mysql = MySQL(app)

# Secret key for session
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Decorators
# Decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'admin':
            logging.debug(f'admin_required: Session user_id: {session.get("user_id")}, user_type: {session.get("user_type")}')
            flash('Access denied. Admins only.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

app.secret_key = 'fitigym_secret_key'  # Replace with something stronger in production

# ---------- Home ----------
@app.route('/')
def home():
    return render_template('home.html')


# ---------- Register ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first = request.form['first_name']
        last = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        password = generate_password_hash(request.form['password'])
        user_type = 'member' # Default to member, remove trainer signup option

        conn = get_connection()
        with conn:
            with conn.cursor() as cursor:
                # Insert user
                # Allow 'admin' user_type only for a specific email or if a secret admin key is provided
                if email == 'admin@example.com': # Replace with your desired admin email
                    user_type = 'admin'
                try:
                    cursor.execute(
                        "INSERT INTO users (first_name, last_name, email, phone, password, user_type) VALUES (%s, %s, %s, %s, %s, %s)",
                        (first, last, email, phone, password, user_type)
                    )
                    conn.commit()
                    flash("Registration successful. Please log in.")
                    return redirect(url_for('login'))
                except pymysql.err.IntegrityError as e:
                    if "Duplicate entry" in str(e) and "phone_UNIQUE" in str(e):
                        flash("Registration failed: Phone number already exists. Please use a different one.", 'danger')
                    else:
                        flash("Registration failed: An unexpected error occurred.", 'danger')
                    conn.rollback()
        return render_template('register.html')
    return render_template('register.html')


# ---------- Login ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_connection()
        with conn:
            with conn.cursor() as cursor:
                # Get user details with role information
                cursor.execute("SELECT id, first_name, password, user_type FROM users WHERE email = %s", (email,))
                user = cursor.fetchone()
                
                if user and check_password_hash(user['password'], password):
                    session['user_id'] = user['id']
                    session['user_name'] = user['first_name']
                    session['user_type'] = user['user_type']
                    
                    flash("Login successful!")
                    
                    if user['user_type'] == 'trainer':
                        # Fetch trainer specific details if needed for the session
                        cursor.execute("SELECT id, specialization, experience_years FROM trainers WHERE user_id = %s", (user['id'],))
                        trainer_details = cursor.fetchone()
                        if trainer_details:
                            session['trainer_id'] = trainer_details['id']
                            session['specialization'] = trainer_details['specialization']
                        return redirect(url_for('trainer_dashboard'))
                    elif user['user_type'] == 'admin':
                        return redirect(url_for('admin_dashboard'))
                    elif user['user_type'] == 'member':
                        return redirect(url_for('dashboard'))
                    else:
                        flash("Invalid user type.")
                        return redirect(url_for('login'))
                else:
                    flash("Invalid email or password.")
    return render_template('login.html')


# ---------- Dashboard ----------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Ensure trainers are redirected to their dashboard
    if session.get('user_type') == 'trainer':
        return redirect(url_for('trainer_dashboard'))
    # Ensure admins are redirected to their dashboard
    if session.get('user_type') == 'admin':
        return redirect(url_for('admin_dashboard'))
    # Ensure only members can access the member dashboard
    if session.get('user_type') != 'member':
        flash('Invalid user type.')
        return redirect(url_for('logout'))

    user_name = session.get('user_name', 'User')
    plan_name = "Premium Monthly"
    start_date = "2025-05-01"
    end_date = "2025-06-01"
    labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    data = [1.5, 2, 1, 2.5, 0, 3]

    return render_template('user_dashboard.html',
                           user_name=user_name,
                           plan_name=plan_name,
                           start_date=start_date,
                           end_date=end_date,
                           labels=labels,
                           data=data)


# ---------- Admin Dashboard ----------
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('user_type') != 'admin':
        flash('Access denied. Admins only.')
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html')

@app.route('/reports')
@admin_required
def reports():
    # This route will display various reports and analytics
    return render_template('reports.html')

@app.route('/manage_users')
def manage_users():
    if 'user_id' not in session or session.get('user_type') != 'admin':
        flash('Access denied. Admins only.')
        return redirect(url_for('login'))
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, first_name, last_name, email, user_type FROM users")
            users = cursor.fetchall()
    return render_template('manage_users.html', users=users)

@app.route('/add_user', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        password = generate_password_hash(request.form['password'])
        user_type = request.form['user_type']

        try:
            conn = get_connection()
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO users (first_name, last_name, email, phone, password, user_type) VALUES (%s, %s, %s, %s, %s, %s)",
                        (first_name, last_name, email, phone, password, user_type)
                    )
                    conn.commit()
                    
                    # If the user is a trainer, create a trainer record
                    if user_type == 'trainer':
                        user_id = cursor.lastrowid
                        cursor.execute(
                            "INSERT INTO trainers (user_id) VALUES (%s)",
                            (user_id,)
                        )
                        conn.commit()
                        
                    flash('User added successfully!', 'success')
                    return redirect(url_for('manage_users'))
        except Exception as e:
            flash(f'Error adding user: {str(e)}', 'error')
            return redirect(url_for('add_user'))
    
    return render_template('add_user.html')

@app.route('/add_trainer', methods=['GET', 'POST'])
@admin_required
def add_trainer():
    if request.method == 'POST':
        # Get form data
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        specialization = request.form['specialization']
        experience_years = request.form['experience_years']
        certifications = request.form.get('certifications', '')
        
        # Create connection
        conn = get_connection()
        try:
            with conn:
                with conn.cursor() as cursor:
                    # First, create user record
                    cursor.execute(
                        "INSERT INTO users (first_name, last_name, email, phone, password, user_type) VALUES (%s, %s, %s, %s, %s, %s)",
                        (first_name, last_name, email, phone, generate_password_hash(password), 'trainer')
                    )
                    user_id = cursor.lastrowid
                    
                    # Then, create trainer record
                    cursor.execute(
                        "INSERT INTO trainers (user_id, specialization, experience_years, certifications) VALUES (%s, %s, %s, %s)",
                        (user_id, specialization, experience_years, certifications)
                    )
                    conn.commit()
                    flash('Trainer added successfully!', 'success')
                    return redirect(url_for('manage_trainers'))
        except Exception as e:
            flash(f'Error adding trainer: {e}', 'danger')
            return redirect(url_for('add_trainer'))
    
    return render_template('add_trainer.html')

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    conn = get_connection()
    
    # Get user data for the form
    if request.method == 'GET':
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, first_name, last_name, email, phone, user_type FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()
                if not user:
                    flash('User not found.', 'danger')
                    return redirect(url_for('manage_users'))
        except Exception as e:
            flash(f'Error fetching user: {e}', 'danger')
            return redirect(url_for('manage_users'))
        finally:
            conn.close()
        return render_template('edit_user.html', user=user)
    
    # Process form submission
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        user_type = request.form['user_type']
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        try:
            with conn.cursor() as cursor:
                # Check if password is being updated
                if new_password:
                    if new_password != confirm_password:
                        flash('Passwords do not match!', 'danger')
                        return redirect(url_for('edit_user', user_id=user_id))
                    
                    # Hash the new password
                    hashed_password = generate_password_hash(new_password)
                    cursor.execute(
                        "UPDATE users SET first_name = %s, last_name = %s, email = %s, phone = %s, user_type = %s, password = %s WHERE id = %s",
                        (first_name, last_name, email, phone, user_type, hashed_password, user_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE users SET first_name = %s, last_name = %s, email = %s, phone = %s, user_type = %s WHERE id = %s",
                        (first_name, last_name, email, phone, user_type, user_id)
                    )
                conn.commit()
                flash('User updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating user: {e}', 'danger')
            conn.rollback()
        finally:
            conn.close()
        return redirect(url_for('manage_users'))

@app.route('/edit_trainer/<int:trainer_id>', methods=['GET', 'POST'])
@admin_required
def edit_trainer(trainer_id):
    logging.debug(f'edit_trainer: Attempting to edit trainer ID: {trainer_id}')
    logging.debug(f'edit_trainer: Session content: {dict(session)}')
    conn = get_connection()
    trainer = None
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT t.*, u.first_name, u.last_name, u.email, u.phone FROM trainers t JOIN users u ON t.user_id = u.id WHERE t.id = %s", (trainer_id,))
            trainer = cursor.fetchone()
            logging.debug(f'edit_trainer: Fetched trainer for ID {trainer_id}: {trainer}')
    except Exception as e:
        logging.error(f"Error fetching trainer {trainer_id}: {e}")
    finally:
        conn.close()

    if trainer is None:
        flash('Trainer not found.', 'danger')
        return redirect(url_for('manage_trainers'))

    if request.method == 'POST':
        # Handle POST request for updating trainer
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        specialization = request.form['specialization']
        experience_years = request.form['experience_years']
        certifications = request.form.get('certifications', '')
        
        # Get password fields
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Check if passwords match (this is also checked client-side)
        if new_password and new_password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return render_template('edit_trainer.html', trainer=trainer)

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                # Update user details
                if new_password:
                    # Hash the new password
                    hashed_password = generate_password_hash(new_password)
                    cursor.execute(
                        "UPDATE users SET first_name=%s, last_name=%s, email=%s, phone=%s, password=%s WHERE id=%s",
                        (first_name, last_name, email, phone, hashed_password, trainer['user_id'])
                    )
                    logging.debug(f'Password updated for user ID: {trainer["user_id"]}') 
                else:
                    cursor.execute(
                        "UPDATE users SET first_name=%s, last_name=%s, email=%s, phone=%s WHERE id=%s",
                        (first_name, last_name, email, phone, trainer['user_id'])
                    )
                
                # Update trainer details
                cursor.execute(
                    "UPDATE trainers SET specialization=%s, experience_years=%s, certifications=%s WHERE id=%s",
                    (specialization, experience_years, certifications, trainer_id)
                )
                conn.commit()
                flash('Trainer updated successfully!', 'success')
                return redirect(url_for('manage_trainers'))
        except Exception as e:
            flash(f'Error updating trainer: {e}', 'danger')
            logging.error(f'Error updating trainer: {e}')
            conn.rollback()
        finally:
            conn.close()

    return render_template('edit_trainer.html', trainer=trainer)

@app.route('/delete_trainer/<int:trainer_id>', methods=['POST'])
@admin_required
def delete_trainer(trainer_id):
    logging.debug(f'delete_trainer: Attempting to delete trainer ID: {trainer_id}')
    logging.debug(f'delete_trainer: Session content: {dict(session)}')
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Get user_id associated with the trainer
            cursor.execute("SELECT user_id FROM trainers WHERE id = %s", (trainer_id,))
            trainer_user_id = cursor.fetchone()

            if trainer_user_id:
                # Delete from trainers table
                cursor.execute("DELETE FROM trainers WHERE id = %s", (trainer_id,))
                # Delete from users table
                cursor.execute("DELETE FROM users WHERE id = %s", (trainer_user_id['user_id'],))
                conn.commit()
                flash('Trainer deleted successfully!', 'success')
            else:
                flash('Trainer not found.', 'danger')
    except Exception as e:
        flash(f'Error deleting trainer: {e}', 'danger')
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('manage_trainers'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    logging.debug(f'delete_user: Attempting to delete user ID: {user_id}')
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Delete the user
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            flash('User deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting user: {e}', 'danger')
        logging.error(f'Error deleting user: {e}')
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('manage_users'))

@app.route('/manage_trainers')
def manage_trainers():
    if 'user_id' not in session or session.get('user_type') != 'admin':
        flash('Access denied. Admins only.')
        return redirect(url_for('login'))
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("""SELECT t.id, u.id AS user_id, u.first_name, u.last_name, u.email, t.specialization, t.experience_years FROM users u JOIN trainers t ON u.id = t.user_id""")
            trainers = cursor.fetchall()
    return render_template('manage_trainers.html', trainers=trainers)

@app.route('/manage-plans')
@login_required
@admin_required
def manage_plans():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # DictCursor returns dicts
    cursor.execute('SELECT * FROM membership_plans')
    plans = cursor.fetchall()
    cursor.close()

    # Format prices nicely (optional)
    for plan in plans:
        try:
            plan['formatted_price'] = f"{float(plan['price']):,.2f}"
        except:
            plan['formatted_price'] = plan['price']  # fallback

    return render_template('manage_plans.html', plans=plans)


@app.route('/add-plan', methods=['GET', 'POST'])
@login_required
@admin_required
def add_plan():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        duration_days = int(request.form['duration_days'])

        cursor = mysql.connection.cursor()
        try:
            cursor.execute(
                'INSERT INTO membership_plans (name, price, description, duration_days) VALUES (%s, %s, %s, %s)',
                (name, price, description, duration_days)
            )
            mysql.connection.commit()
            flash('Plan added successfully!', 'success')
            return redirect(url_for('manage_plans'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error adding plan: {str(e)}', 'error')
        finally:
            cursor.close()

    return render_template('add_plan.html')

@app.route('/edit-plan/<int:plan_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_plan(plan_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # Use DictCursor here

    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        duration_days = int(request.form['duration_days'])

        try:
            cursor.execute(
                'UPDATE membership_plans SET name = %s, price = %s, description = %s, duration_days = %s WHERE id = %s',
                (name, price, description, duration_days, plan_id)
            )
            mysql.connection.commit()
            flash('Plan updated successfully!', 'success')
            return redirect(url_for('manage_plans'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error updating plan: {str(e)}', 'error')

    # Get the current plan details
    cursor.execute('SELECT * FROM membership_plans WHERE id = %s', (plan_id,))
    plan = cursor.fetchone()  # This will now return a dictionary
    cursor.close()

    if plan is None:
        flash('Plan not found!', 'error')
        return redirect(url_for('manage_plans'))

    return render_template('edit_plan.html', plan=plan)

@app.route('/delete_plan/<int:plan_id>', methods=['POST'])
@login_required
@admin_required
def delete_plan(plan_id):
    conn = mysql.connection
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    
    try:
        # Check if the plan is currently used by any members
        cursor.execute("SELECT COUNT(*) FROM members WHERE plan_id = %s", (plan_id,))
        result = cursor.fetchone()
        if result['COUNT(*)'] > 0:
            flash('Cannot delete plan: It is currently assigned to one or more members.', 'error')
            return redirect(url_for('manage_plans'))
        
        # If not used, proceed with deletion
        cursor.execute("DELETE FROM membership_plans WHERE id = %s", (plan_id,))
        conn.commit()
        flash('Membership plan deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting plan: {e}', 'error')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('manage_plans'))


# ---------- Plans ----------
@app.route('/plans')
def plans():
    is_logged_in = 'user_id' in session
    
    # Fetch membership plans from the database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM membership_plans ORDER BY price ASC')
    db_plans = cursor.fetchall()
    cursor.close()
    
    # Convert database plans to the format expected by the template
    plans = {}
    for plan in db_plans:
        # Create a unique key for each plan based on its ID
        plan_key = f"plan_{plan['id']}"
        
        # Parse the description field to extract features
        features = []
        if plan['description']:
            # Split description by newlines or commas to get features
            features = [feature.strip() for feature in plan['description'].replace('\n', ',').split(',') if feature.strip()]
        
        # Format the price with currency
        formatted_price = f"KES {float(plan['price']):,.2f}"
        
        # Add duration if available
        if plan['duration_days'] == 1:
            formatted_price += "/day"
        elif plan['duration_days'] == 30 or plan['duration_days'] == 31:
            formatted_price += "/month"
        elif plan['duration_days'] == 365:
            formatted_price += "/year"
        
        plans[plan_key] = {
            'id': plan['id'],
            'name': plan['name'],
            'price': formatted_price,
            'features': features,
            'duration_days': plan['duration_days']
        }
    
    return render_template('plans.html', is_logged_in=is_logged_in, plans=plans)

@app.route('/choose_plan', methods=['POST'])
def choose_plan():
    if not all(k in request.form for k in ['height_feet', 'height_inches', 'weight', 'age', 'goal', 'experience', 'preferred_time']):
        flash('Please fill in all required fields.')
        return redirect(url_for('plans'))
        
    # Fetch membership plans from the database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM membership_plans ORDER BY price ASC')
    db_plans = cursor.fetchall()
    cursor.close()
    
    # Convert database plans to the format expected by the template
    plans = {}
    for plan in db_plans:
        # Create a unique key for each plan based on its ID
        plan_key = f"plan_{plan['id']}"
        
        # Parse the description field to extract features
        features = []
        if plan['description']:
            # Split description by newlines or commas to get features
            features = [feature.strip() for feature in plan['description'].replace('\n', ',').split(',') if feature.strip()]
        
        # Format the price with currency
        formatted_price = f"KES {float(plan['price']):,.2f}"
        
        # Add duration if available
        if plan['duration_days'] == 1:
            formatted_price += "/day"
        elif plan['duration_days'] == 30 or plan['duration_days'] == 31:
            formatted_price += "/month"
        elif plan['duration_days'] == 365:
            formatted_price += "/year"
        
        plans[plan_key] = {
            'id': plan['id'],
            'name': plan['name'],
            'price': formatted_price,
            'features': features,
            'duration_days': plan['duration_days']
        }

    try:
        # Calculate BMI from feet and inches
        height_feet = float(request.form['height_feet'])
        height_inches = float(request.form['height_inches'])
        total_height_meters = ((height_feet * 12 + height_inches) * 2.54) / 100
        
        weight = float(request.form['weight'])
        age = int(request.form['age'])
        bmi = round(weight / (total_height_meters * total_height_meters), 1)
        
        # Determine BMI category
        if bmi < 18.5:
            bmi_category = "Underweight"
        elif bmi < 25:
            bmi_category = "Normal weight"
        elif bmi < 30:
            bmi_category = "Overweight"
        else:
            bmi_category = "Obese"

        # Get other form data
        goal = request.form['goal']
        experience = request.form['experience']
        preferred_time = request.form['preferred_time']
        health_conditions = request.form.getlist('health_conditions[]')

        # Store user's personalized plan data in session
        session['personalized_plan_data'] = {
            'goal': goal,
            'experience': experience,
            'preferred_time': preferred_time,
            'height_feet': height_feet,
            'height_inches': height_inches,
            'weight': weight,
            'age': age,
            'health_conditions': health_conditions,
            'bmi': bmi,
            'bmi_category': bmi_category
        }

        # Recommend workout focus based on goals and health conditions
        workout_focus = get_workout_focus(goal, bmi_category, health_conditions)

        # Create suggestion object
        suggestion = {
            'bmi': bmi,
            'bmi_category': bmi_category,
            'workout_focus': workout_focus,
            'trainer': 'John Smith',  # This should be dynamic based on user's needs
            'plan': recommend_plan(goal, experience, bmi_category)
        }

        is_logged_in = 'user_id' in session
        return render_template('plans.html', suggestion=suggestion, is_logged_in=is_logged_in, plans=plans)

    except ValueError as e:
        flash('Please enter valid numbers for height, weight, and age.')
        return redirect(url_for('plans'))

    # Match with appropriate trainer based on experience and health conditions
    trainer = match_trainer(goal, experience, health_conditions, preferred_time)

    # Recommend plan based on goals and experience
    recommended_plan = recommend_plan(goal, experience, bmi_category)

    suggestion = {
        'bmi': bmi,
        'bmi_category': bmi_category,
        'plan': recommended_plan,
        'trainer': trainer,
        'workout_focus': workout_focus
    }

    is_logged_in = 'user_id' in session
    # Plans are already fetched from the database at the beginning of the function
    return render_template('plans.html', suggestion=suggestion, is_logged_in=is_logged_in, plans=plans)

def get_workout_focus(goal, bmi_category, health_conditions):
    focus = []
    if 'back_pain' in health_conditions:
        focus.append("Core strengthening and posture improvement")
    if 'joint_issues' in health_conditions:
        focus.append("Low-impact exercises and joint mobility")
    if 'heart_condition' in health_conditions:
        focus.append("Monitored cardio and gradual progression")

    if goal == 'muscle_gain':
        focus.append("Progressive strength training")
    elif goal == 'fat_loss':
        focus.append("High-intensity interval training")
    elif goal == 'endurance':
        focus.append("Cardiovascular endurance training")
    elif goal == 'recovery':
        focus.append("Rehabilitation exercises")
    
    return " with focus on " + " and ".join(focus) if focus else "General fitness program"

def match_trainer(goal, experience, health_conditions, preferred_time):
    # In a real application, this would query the database for available trainers
    # For now, we'll return placeholder recommendations
    trainers = {
        'muscle_gain': {
            'beginner': 'John (Strength Specialist)',
            'intermediate': 'Mike (Advanced Strength Coach)',
            'advanced': 'Sarah (Elite Performance Coach)'
        },
        'fat_loss': {
            'beginner': 'Emma (Weight Loss Specialist)',
            'intermediate': 'Tom (HIIT Expert)',
            'advanced': 'Lisa (Body Transformation Coach)'
        },
        'general_fitness': {
            'beginner': 'David (Fitness Fundamentals)',
            'intermediate': 'Anna (Balanced Fitness Coach)',
            'advanced': 'Mark (Advanced Fitness Trainer)'
        },
        'recovery': {
            'beginner': 'Maria (Rehabilitation Specialist)',
            'intermediate': 'James (Recovery Expert)',
            'advanced': 'Karen (Sports Rehabilitation Coach)'
        }
    }
    
    return trainers.get(goal, {}).get(experience, 'Alex (General Fitness Coach)')

def recommend_plan(goal, experience, bmi_category):
    # Get plans from database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM membership_plans ORDER BY price ASC')
    plans = cursor.fetchall()
    cursor.close()
    
    # If no plans in database, return a default message
    if not plans:
        return 'No plans available'
    
    # Get plan names for recommendation
    plan_names = [plan['name'] for plan in plans]
    
    # Determine which plan to recommend based on user data
    if len(plans) >= 3:
        if experience == 'advanced' or goal in ['muscle_gain', 'recovery']:
            return plan_names[-1]  # Most expensive plan (premium)
        elif experience == 'intermediate' or goal == 'fat_loss':
            return plan_names[len(plan_names) // 2]  # Middle plan (standard)
        else:
            return plan_names[1] if len(plan_names) > 1 else plan_names[0]  # Second cheapest or cheapest
    else:
        # If we have fewer than 3 plans, just return the highest one for advanced users
        # and the lowest one for beginners
        if experience == 'advanced':
            return plan_names[-1]
        else:
            return plan_names[0]


# ---------- Payment Process ----------
@app.route('/payment-process/<int:plan_id>', defaults={'step': 1})
@app.route('/payment-process/<int:plan_id>/<int:step>')
def payment_process_view(plan_id, step):
    print(f"Payment Process - Received plan_id: {plan_id}")
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get user's personalized plan data from session
    user_data = session.get('personalized_plan_data', {
        'goal': request.form.get('goal'),
        'experience': request.form.get('experience'),
        'preferred_time': request.form.get('preferred_time'),
        'height_feet': request.form.get('height_feet'),
        'height_inches': request.form.get('height_inches'),
        'weight': request.form.get('weight'),
        'age': request.form.get('age'),
        'health_conditions': request.form.getlist('health_conditions[]')
    })

    # Define available trainers with their categories and details
    trainers = {
        'strength': [
            {
                'name': 'John Smith',
                'image': 'trainer1.jpg',
                'category': 'strength',
                'experience_level': 'Expert',
                'primary_focus': 'Powerlifting',
                'specialization': 'Strength & Conditioning',
                'years': 8,
                'certifications': ['NASM-CPT', 'CSCS'],
                'availability': ['morning', 'afternoon', 'evening']
            },
            {
                'name': 'Mike Johnson',
                'image': 'trainer2.jpg',
                'category': 'strength',
                'experience_level': 'Advanced',
                'primary_focus': 'Bodybuilding',
                'specialization': 'Muscle Hypertrophy',
                'years': 6,
                'certifications': ['ACE-CPT', 'ISSA-ST'],
                'availability': ['early_morning', 'evening']
            }
        ],
        'cardio': [
            {
                'name': 'Emma Davis',
                'image': 'trainer3.jpg',
                'category': 'cardio',
                'experience_level': 'Expert',
                'primary_focus': 'HIIT',
                'specialization': 'Weight Loss',
                'years': 7,
                'certifications': ['ACE-CPT', 'NASM-WLS'],
                'availability': ['morning', 'afternoon']
            },
            {
                'name': 'Sarah Wilson',
                'image': 'trainer4.jpg',
                'category': 'cardio',
                'experience_level': 'Advanced',
                'primary_focus': 'Endurance',
                'specialization': 'Marathon Training',
                'years': 5,
                'certifications': ['RRCA', 'USATF-L1'],
                'availability': ['early_morning', 'morning']
            }
        ],
        'wellness': [
            {
                'name': 'David Brown',
                'image': 'trainer5.jpg',
                'category': 'wellness',
                'experience_level': 'Expert',
                'primary_focus': 'Yoga',
                'specialization': 'Mind-Body Wellness',
                'years': 10,
                'certifications': ['RYT-500', 'ACE-CHC'],
                'availability': ['morning', 'evening']
            },
            {
                'name': 'Lisa Chen',
                'image': 'trainer6.jpg',
                'category': 'wellness',
                'experience_level': 'Advanced',
                'primary_focus': 'Recovery',
                'specialization': 'Injury Prevention',
                'years': 6,
                'certifications': ['NASM-CES', 'FRC-MS'],
                'availability': ['afternoon', 'evening']
            }
        ]
    }

    # Flatten the trainers list for the template
    all_trainers = []
    for category in trainers.values():
        all_trainers.extend(category)

    # Get plan details from database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM membership_plans WHERE id = %s', (plan_id,))
    plan_data = cursor.fetchone()
    cursor.close()
    
    if not plan_data:
        flash('Invalid plan selected.')
        return redirect(url_for('plans'))
    
    # Parse the description field to extract features
    features = []
    if plan_data['description']:
        # Split description by newlines or commas to get features
        features = [feature.strip() for feature in plan_data['description'].replace('\n', ',').split(',') if feature.strip()]
    
    # Format the price with currency
    formatted_price = f"KES {float(plan_data['price']):,.2f}"
    
    # Add duration if available
    if plan_data['duration_days'] == 1:
        formatted_price += "/day"
    elif plan_data['duration_days'] == 30 or plan_data['duration_days'] == 31:
        formatted_price += "/month"
    elif plan_data['duration_days'] == 365:
        formatted_price += "/year"
    
    # Create the plan dictionary in the format expected by the template
    selected_plan = {
        'id': plan_data['id'],
        'name': plan_data['name'],
        'price': formatted_price,
        'features': features,
        'duration_days': plan_data['duration_days']
        # Removed type field as we're using id directly
    }

    # Placeholder for trainer data (replace with actual trainer selection logic)
    selected_trainer = {
        'name': 'John Smith',
        'image': url_for('static', filename='images/trainer1.jpg'),
        'specialty': 'Strength & Conditioning',
        'description': 'Experienced in powerlifting and muscle hypertrophy.',
        'available_slots': ['9:00 AM', '11:00 AM', '3:00 PM']
    }

    return render_template('payment_process.html', 
                          plan=selected_plan,
                          trainers=all_trainers,
                          step=step,
                          user_data=user_data,
                          trainer=selected_trainer)




# ---------- Logout ----------
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('home'))


# Decorator for trainer-only routes
def trainer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.')
            return redirect(url_for('login'))
        if session.get('user_type') != 'trainer':
            flash('Access denied. This page is for trainers only.')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ---------- Trainer Dashboard ----------
@app.route('/toggle_notifications')
@trainer_required
def toggle_notifications():
    if 'notifications_active' not in session:
        session['notifications_active'] = True
    else:
        session['notifications_active'] = not session['notifications_active']
    return redirect(url_for('trainer_dashboard'))

@app.route('/trainer/dashboard')
@trainer_required
def trainer_dashboard():
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            # Get trainer info
            cursor.execute("""
                SELECT t.*, u.first_name, u.last_name, u.email, u.phone 
                FROM trainers t 
                JOIN users u ON t.user_id = u.id 
                WHERE t.user_id = %s
            """, (session['user_id'],))
            trainer = cursor.fetchone()
            
            # Get trainer's members
            cursor.execute("""
                SELECT u.*, m.plan_type, m.join_date, m.status 
                FROM members m 
                JOIN users u ON m.user_id = u.id 
                WHERE m.trainer_id = %s
            """, (trainer['id'],))
            members = cursor.fetchall()
            
            # Get notifications
            cursor.execute("""
                SELECT * FROM notifications 
                WHERE trainer_id = %s
                ORDER BY created_at DESC
            """, (trainer['id'],))
            notifications = cursor.fetchall()
            
            # Get available trainers for transfer
            cursor.execute("""
                SELECT t.id, u.first_name, u.last_name, t.specialization 
                FROM trainers t 
                JOIN users u ON t.user_id = u.id 
                WHERE t.id != %s
            """, (trainer['id'],))
            available_trainers = cursor.fetchall()
            
            conn.commit()
    
    return render_template('trainer_dashboard.html',
                          trainer=trainer,
                          members=members,
                          notifications=notifications,
                          available_trainers=available_trainers)

@app.route('/trainer/notifications', methods=['GET'])
@trainer_required
def get_notifications():
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT n.*, COUNT(*) OVER() as total_unread
                FROM notifications n
                WHERE n.trainer_id = (SELECT id FROM trainers WHERE user_id = %s)
                ORDER BY n.created_at DESC
                LIMIT 10
            """, (session['user_id'],))
            notifications = cursor.fetchall()
            
            # Get unread count
            cursor.execute("""
                SELECT COUNT(*) as unread_count
                FROM notifications
                WHERE trainer_id = (SELECT id FROM trainers WHERE user_id = %s)
                AND `read` = FALSE
            """, (session['user_id'],))
            unread_count = cursor.fetchone()['unread_count']
    
    return jsonify({
        'notifications': notifications,
        'unread_count': unread_count
    })

@app.route('/trainer/notifications/mark-read', methods=['POST'])
@trainer_required
def mark_notification_read():
    notification_id = request.json.get('notification_id')
    
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE notifications 
                SET `read` = TRUE 
                WHERE id = %s AND trainer_id = (
                    SELECT id FROM trainers WHERE user_id = %s
                )
            """, (notification_id, session['user_id']))
            conn.commit()
            
            # Get updated unread count
            cursor.execute("""
                SELECT COUNT(*) as unread_count
                FROM notifications
                WHERE trainer_id = (SELECT id FROM trainers WHERE user_id = %s)
                AND `read` = FALSE
            """, (session['user_id'],))
            unread_count = cursor.fetchone()['unread_count']
    
    return jsonify({
        'success': True,
        'unread_count': unread_count
    })

@app.route('/trainer/notifications/mark-all-read', methods=['POST'])
@trainer_required
def mark_all_notifications_read():
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE notifications 
                SET `read` = TRUE 
                WHERE trainer_id = (SELECT id FROM trainers WHERE user_id = %s)
                AND `read` = FALSE
            """, (session['user_id'],))
            conn.commit()
    
    return jsonify({'success': True, 'unread_count': 0})

@app.route('/trainer/member/transfer/available')
@trainer_required
def get_available_trainers():
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    t.id,
                    u.first_name,
                    u.last_name,
                    t.specialization,
                    t.experience_years,
                    COUNT(m.id) as current_members,
                    GROUP_CONCAT(DISTINCT t.availability) as availability
                FROM trainers t
                JOIN users u ON t.user_id = u.id
                LEFT JOIN members m ON t.id = m.trainer_id
                WHERE t.id != (SELECT id FROM trainers WHERE user_id = %s)
                GROUP BY t.id
                HAVING current_members < 10  -- Maximum 10 members per trainer
            """, (session['user_id'],))
            trainers = cursor.fetchall()
    
    return jsonify({
        'trainers': [{
            'id': t['id'],
            'name': f"{t['first_name']} {t['last_name']}",
            'specialization': t['specialization'],
            'experience_years': t['experience_years'],
            'current_members': t['current_members'],
            'availability': t['availability'].split(',') if t['availability'] else []
        } for t in trainers]
    })

@app.route('/trainer/member/transfer', methods=['POST'])
@trainer_required
def transfer_member():
    member_id = request.json.get('member_id')
    new_trainer_id = request.json.get('new_trainer_id')
    transfer_reason = request.json.get('reason', 'Not specified')
    
    if not member_id or not new_trainer_id:
        return jsonify({
            'success': False,
            'error': 'Member ID and new trainer ID are required'
        }), 400
    
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            # Verify member belongs to current trainer
            cursor.execute("""
                SELECT m.*, u.first_name, u.last_name
                FROM members m
                JOIN users u ON m.user_id = u.id
                WHERE m.user_id = %s 
                AND m.trainer_id = (SELECT id FROM trainers WHERE user_id = %s)
            """, (member_id, session['user_id']))
            member = cursor.fetchone()
            
            if not member:
                return jsonify({
                    'success': False,
                    'error': 'Member not found or not assigned to you'
                }), 404
            
            # Verify new trainer exists and has capacity
            cursor.execute("""
                SELECT t.*, u.first_name, u.last_name,
                       (SELECT COUNT(*) FROM members WHERE trainer_id = t.id) as member_count
                FROM trainers t
                JOIN users u ON t.user_id = u.id
                WHERE t.id = %s
            """, (new_trainer_id,))
            new_trainer = cursor.fetchone()
            
            if not new_trainer:
                return jsonify({
                    'success': False,
                    'error': 'New trainer not found'
                }), 404
            
            if new_trainer['member_count'] >= 10:
                return jsonify({
                    'success': False,
                    'error': 'New trainer has reached maximum member capacity'
                }), 400
            
            # Update member's trainer
            cursor.execute("""
                UPDATE members 
                SET trainer_id = %s 
                WHERE user_id = %s AND trainer_id = (SELECT id FROM trainers WHERE user_id = %s)
            """, (new_trainer_id, member_id, session['user_id']))
            
            # Create notification for new trainer
            cursor.execute("""
                INSERT INTO notifications (trainer_id, message, created_at) 
                VALUES (%s, %s, %s)
            """, (
                new_trainer_id,
                f"New member {member['first_name']} {member['last_name']} transferred to you from {session.get('user_name')}. Reason: {transfer_reason}",
                datetime.now()
            ))
            
            # Create notification for member
            cursor.execute("""
                INSERT INTO notifications (trainer_id, message, created_at)
                VALUES (
                    (SELECT id FROM trainers WHERE user_id = %s),
                    %s,
                    %s
                )
            """, (
                session['user_id'],
                f"You have been transferred to trainer {new_trainer['first_name']} {new_trainer['last_name']}",
                datetime.now()
            ))
            
            # Log the transfer
            cursor.execute("""
                INSERT INTO trainer_transfers 
                (member_id, from_trainer_id, to_trainer_id, reason, transferred_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                member_id,
                member['trainer_id'],
                new_trainer_id,
                transfer_reason,
                datetime.now()
            ))
            conn.commit()
    
    return jsonify({
        'success': True,
        'message': f"Member successfully transferred to {new_trainer['first_name']} {new_trainer['last_name']}"
    })

@app.route('/trainer/chat/history/<int:member_id>')
@trainer_required
def get_chat_history(member_id):
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            # Get member details
            cursor.execute("""
                SELECT u.first_name, u.last_name, u.email
                FROM users u
                WHERE u.id = %s
            """, (member_id,))
            member = cursor.fetchone()
            
            # Get chat history
            cursor.execute("""
                SELECT 
                    cm.*,
                    CASE 
                        WHEN cm.sender_id = %s THEN 'sent'
                        ELSE 'received'
                    END as message_type,
                    u_sender.first_name as sender_name,
                    u_receiver.first_name as receiver_name
                FROM chat_messages cm
                JOIN users u_sender ON cm.sender_id = u_sender.id
                JOIN users u_receiver ON cm.receiver_id = u_receiver.id
                WHERE (cm.sender_id = %s AND cm.receiver_id = %s) 
                OR (cm.sender_id = %s AND cm.receiver_id = %s) 
                ORDER BY cm.sent_at ASC
                LIMIT 50
            """, (session['user_id'], session['user_id'], member_id, member_id, session['user_id']))
            messages = cursor.fetchall()
    
    return jsonify({
        'messages': messages,
        'member': {
            'id': member_id,
            'name': f"{member['first_name']} {member['last_name']}",
            'email': member['email']
        }
    })

@app.route('/edit_trainer_profile', methods=['GET', 'POST'])
@trainer_required
def edit_trainer_profile():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Get trainer info
            cursor.execute("""
                SELECT t.*, u.first_name, u.last_name, u.email, u.phone 
                FROM trainers t 
                JOIN users u ON t.user_id = u.id 
                WHERE t.user_id = %s
            """, (session['user_id'],))
            trainer = cursor.fetchone()
            
            if request.method == 'POST':
                # Get form data
                first_name = request.form['first_name']
                last_name = request.form['last_name']
                email = request.form['email']
                phone = request.form['phone']
                specialization = request.form['specialization']
                experience_years = request.form['experience_years']
                certifications = request.form.get('certifications', '')
                
                # Update user details
                cursor.execute("""
                    UPDATE users 
                    SET first_name=%s, last_name=%s, email=%s, phone=%s 
                    WHERE id=%s
                """, (first_name, last_name, email, phone, trainer['user_id']))
                
                # Update trainer details
                cursor.execute("""
                    UPDATE trainers 
                    SET specialization=%s, experience_years=%s, certifications=%s 
                    WHERE user_id=%s
                """, (specialization, experience_years, certifications, trainer['user_id']))
                
                conn.commit()
                flash('Profile updated successfully!', 'success')
                return redirect(url_for('trainer_dashboard'))
            
            return render_template('edit_profile.html', trainer=trainer)
            
    except Exception as e:
        flash(f'Error updating profile: {e}', 'danger')
        return redirect(url_for('trainer_dashboard'))
    finally:
        conn.close()

@app.route('/trainer/chat/send', methods=['POST'])
@trainer_required
def send_message():
    member_id = request.json.get('member_id')
    message_text = request.json.get('message')
    
    if not message_text or not message_text.strip():
        return jsonify({
            'success': False,
            'error': 'Message cannot be empty'
        }), 400
    
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            # Send message
            cursor.execute("""
                INSERT INTO chat_messages (sender_id, receiver_id, message, sent_at) 
                VALUES (%s, %s, %s, %s)
            """, (session['user_id'], member_id, message_text, datetime.now()))
            message_id = cursor.lastrowid
            
            # Create notification for member
            cursor.execute("""
                INSERT INTO notifications (trainer_id, message, created_at)
                VALUES (
                    (SELECT id FROM trainers WHERE user_id = %s),
                    %s,
                    %s
                )
            """, (
                session['user_id'],
                f"New message from trainer {session.get('user_name')}",
                datetime.now()
            ))
            
            # Get message details
            cursor.execute("""
                SELECT 
                    cm.*,
                    'sent' as message_type,
                    u_sender.first_name as sender_name,
                    u_receiver.first_name as receiver_name
                FROM chat_messages cm
                JOIN users u_sender ON cm.sender_id = u_sender.id
                JOIN users u_receiver ON cm.receiver_id = u_receiver.id
                WHERE cm.id = %s
            """, (message_id,))
            message = cursor.fetchone()
            conn.commit()
    
    return jsonify({
        'success': True,
        'message': message
    })

@app.route('/trainer/chat/unread/<int:member_id>')
@trainer_required
def get_unread_messages(member_id):
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as unread_count
                FROM chat_messages
                WHERE sender_id = %s 
                AND receiver_id = %s
                AND read_at IS NULL
            """, (member_id, session['user_id']))
            result = cursor.fetchone()
    
    return jsonify({
        'unread_count': result['unread_count']
    })

@app.route('/trainer/member/progress/<int:member_id>', methods=['GET'])
@trainer_required
def get_member_progress(member_id):
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            # Get member details
            cursor.execute("""
                SELECT u.*, m.plan_type, m.join_date
                FROM users u
                JOIN members m ON u.id = m.user_id
                WHERE u.id = %s
            """, (member_id,))
            member = cursor.fetchone()
            
            # Get progress history
            cursor.execute("""
                SELECT mp.*, 
                       u.first_name as trainer_name
                FROM member_progress mp
                JOIN trainers t ON mp.trainer_id = t.id
                JOIN users u ON t.user_id = u.id
                WHERE mp.member_id = %s
                ORDER BY mp.recorded_at DESC
                LIMIT 10
            """, (member_id,))
            progress_history = cursor.fetchall()
            
            # Get latest metrics
            cursor.execute("""
                SELECT metrics
                FROM member_progress
                WHERE member_id = %s
                ORDER BY recorded_at DESC
                LIMIT 1
            """, (member_id,))
            latest_metrics = cursor.fetchone()
    
    return jsonify({
        'member': member,
        'progress_history': progress_history,
        'latest_metrics': latest_metrics['metrics'] if latest_metrics else None
    })

@app.route('/trainer/member/progress', methods=['POST'])
@trainer_required
def update_member_progress():
    member_id = request.json.get('member_id')
    progress_notes = request.json.get('progress_notes')
    metrics = request.json.get('metrics')
    
    if not member_id or not metrics:
        return jsonify({
            'success': False,
            'error': 'Member ID and metrics are required'
        }), 400
    
    # Validate metrics structure
    required_metrics = ['weight', 'body_fat', 'muscle_mass', 'attendance']
    if not all(metric in metrics for metric in required_metrics):
        return jsonify({
            'success': False,
            'error': f'Required metrics: {", ".join(required_metrics)}'
        }), 400
    
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            # Insert progress record
            cursor.execute("""
                INSERT INTO member_progress 
                (member_id, trainer_id, notes, metrics, recorded_at) 
                VALUES (%s, (SELECT id FROM trainers WHERE user_id = %s), %s, %s, %s)
            """, (
                member_id,
                session['user_id'],
                progress_notes,
                json.dumps(metrics),
                datetime.now()
            ))
            progress_id = cursor.lastrowid
            
            # Create notification for member
            cursor.execute("""
                INSERT INTO notifications (trainer_id, message, created_at)
                VALUES (
                    (SELECT id FROM trainers WHERE user_id = %s),
                    %s,
                    %s
                )
            """, (
                session['user_id'],
                f"Progress update from trainer {session.get('user_name')}",
                datetime.now()
            ))
            
            # Get the inserted progress record
            cursor.execute("""
                SELECT mp.*, 
                       u.first_name as trainer_name
                FROM member_progress mp
                JOIN trainers t ON mp.trainer_id = t.id
                JOIN users u ON t.user_id = u.id
                WHERE mp.id = %s
            """, (progress_id,))
            progress = cursor.fetchone()
            conn.commit()
    
    return jsonify({
        'success': True,
        'progress': progress
    })

@app.route('/trainer/member/progress/metrics/<int:member_id>')
@trainer_required
def get_member_metrics(member_id):
    metric_type = request.args.get('type', 'weight')  # Default to weight
    period = request.args.get('period', 'month')  # Default to month
    
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    DATE(recorded_at) as date,
                    JSON_EXTRACT(metrics, CONCAT('$.', %s)) as metric_value
                FROM member_progress
                WHERE member_id = %s
                AND recorded_at >= DATE_SUB(NOW(), INTERVAL 1 %s)
                ORDER BY recorded_at ASC
            """, (metric_type, member_id, period))
            metrics = cursor.fetchall()
    
    return jsonify({
        'metric_type': metric_type,
        'period': period,
        'data': [{
            'date': metric['date'].strftime('%Y-%m-%d'),
            'value': float(metric['metric_value'])
        } for metric in metrics]
    })

@app.route('/trainer/profile/update', methods=['POST'])
@trainer_required
def update_trainer_profile():
    specialization = request.json.get('specialization')
    experience = request.json.get('experience')
    bio = request.json.get('bio')
    
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE trainers 
                SET specialization = %s,
                    experience_years = %s,
                    bio = %s
                WHERE user_id = %s
            """, (specialization, experience, bio, session['user_id']))
            conn.commit()
            
            # Fetch updated trainer info
            cursor.execute("""
                SELECT t.*, u.first_name, u.last_name 
                FROM trainers t 
                JOIN users u ON t.user_id = u.id 
                WHERE t.user_id = %s
            """, (session['user_id'],))
            trainer = cursor.fetchone()
    
    return jsonify({
        'success': True,
        'trainer': {
            'specialization': trainer['specialization'],
            'experience_years': trainer['experience_years'],
            'bio': trainer['bio'],
            'first_name': trainer['first_name'],
            'last_name': trainer['last_name']
        }
    })

@app.route('/mpesa-payment/<int:plan_id>', methods=['GET', 'POST'])
def mpesa_payment(plan_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get plan details from database
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM membership_plans WHERE id = %s", (plan_id,))
            plan_data = cursor.fetchone()
    
    if not plan_data:
        flash('Invalid plan selected.', 'error')
        return redirect(url_for('plans'))
    
    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        if not phone_number:
            flash('Please provide a phone number.', 'error')
            return redirect(url_for('mpesa_payment', plan_id=plan_id))
        
        try:
            # Parse features from description
            features = [feature.strip() for feature in plan_data['description'].replace('\n', ',').split(',') if feature.strip()]
            
            # Format price for display
            formatted_price = f"KES {float(plan_data['price']):,.2f}"
            
            # Initiate STK push with all required parameters
            account_reference = f"FitiGym_plan_{plan_id}_{session['user_id']}"
            transaction_desc = f"Payment for {plan_data['name']}"
            
            # Convert Decimal to float for JSON serialization
            amount = float(plan_data['price'])
            
            response = initiate_stk_push(
                phone_number=phone_number,
                amount=amount,
                account_reference=account_reference,
                transaction_desc=transaction_desc
            )
            
            if response.get('ResponseCode') == '0':
                # Store checkout request ID in session for callback verification
                session['checkout_request_id'] = response.get('CheckoutRequestID')
                session['current_plan_id'] = plan_id
                flash('Payment initiated. Please check your phone to complete the transaction.', 'info')
                return redirect(url_for('payment_status'))
            else:
                flash('Failed to initiate payment. Please try again.', 'error')
                return redirect(url_for('mpesa_payment', plan_id=plan_id))
        except Exception as e:
            flash(f'Error initiating payment: {str(e)}', 'error')
            return redirect(url_for('mpesa_payment', plan_id=plan_id))
    
    # Create the plan dictionary in the format expected by the template
    features = [feature.strip() for feature in plan_data['description'].replace('\n', ',').split(',') if feature.strip()]
    
    # Format the price with currency
    formatted_price = f"KES {float(plan_data['price']):,.2f}"
    
    # Add duration if available
    if plan_data['duration_days'] == 1:
        formatted_price += "/day"
    elif plan_data['duration_days'] == 30 or plan_data['duration_days'] == 31:
        formatted_price += "/month"
    elif plan_data['duration_days'] == 365:
        formatted_price += "/year"
    
    # Create the plan dictionary in the format expected by the template
    selected_plan = {
        'id': plan_data['id'],
        'name': plan_data['name'],
        'price': formatted_price,
        'raw_price': plan_data['price'],
        'features': features,
        'duration_days': plan_data['duration_days']
        # Removed type field as we're using id directly
    }
    
    return render_template('mpesa_payment.html', plan=selected_plan)


@app.route('/payment-status')
def payment_status():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('payment_status.html')


if __name__ == '__main__':
    app.run(debug=True)


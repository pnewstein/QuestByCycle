from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user
from app.models import db, User, Task, Event
from app.forms import AddUserForm, EventForm, TaskForm
from functools import wraps

import traceback


admin_bp = Blueprint('admin', __name__)


ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Decorator to require admin access
def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Access denied: You do not have the necessary permissions.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


# Function to create an admin to start off
def create_admin(app):
    with app.app_context():
        # Load the configuration
        config = current_app.config

        default_admin_password = config['encryption']['DEFAULT_ADMIN_PASSWORD']
        default_admin_username = config['encryption']['DEFAULT_ADMIN_USERNAME']
        default_admin_email = config['encryption']['DEFAULT_ADMIN_EMAIL']

        # Check if admin user already exists
        existing_admin = User.query.filter_by(username=default_admin_username).first()
        if not existing_admin:
            # Create an admin user with default credentials
            admin_user = User(
                username=default_admin_username, 
                email=default_admin_email
            )
            admin_user.set_password(default_admin_password)
            admin_user.is_admin = True  # Set as admin
            # ... set other fields if necessary

            db.session.add(admin_user)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error creating admin user: {e}")


# Function to sign in to the admin dashboard
@admin_bp.route('/admin/admin_dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return redirect(url_for('main.index'))  # Adjust the redirect as appropriate
    return render_template('admin_dashboard.html')


# ADMIN USER MANAGEMENT #
#########################
@admin_bp.route('/user_management', methods=['GET', 'POST'])
@login_required
@require_admin
def user_management():
    users = User.query.all()
    form = AddUserForm()
    if form.validate_on_submit():
        # Add user logic goes here
        pass
    return render_template('user_management.html', users=users, form=form)

# Function to add a admin to the database
@admin_bp.route('/add_user', methods=['POST'])
@login_required
@require_admin
def add_user():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    is_admin = 'is_admin' in request.form

    if not (username and email and password):
        flash('Please enter all the required fields.', 'error')
        return redirect(url_for('admin.user_management'))

    existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
    if existing_user:
        flash('A user with this email or username already exists.', 'error')
    else:
        # Creating a new user
        new_user = User()
        new_user.username = username
        new_user.email = email
        new_user.password = new_user.set_password(password)
        new_user.is_admin = is_admin  # Set additional attributes

        try:
            # Add the new user to the session and commit
            db.session.add(new_user)
            db.session.commit()
            flash('New user added successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            traceback_str = traceback.format_exc()  # This will give you the full traceback as a string.
            current_app.logger.error(traceback_str)  # This will log the full traceback.
            flash(f'An error occurred while creating the user: {e}', 'error')

    return redirect(url_for('admin.user_management'))



from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models import db, User, Game
from app.forms import AddUserForm, CarouselImportForm
from functools import wraps
from werkzeug.utils import secure_filename

import traceback
import os

admin_bp = Blueprint('admin', __name__)


ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Decorator to require admin access
def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_super_admin and not current_user.is_admin:
            flash('Access denied: You do not have the necessary permissions.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


def require_super_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_super_admin:
            flash('Access denied: You do not have the necessary permissions.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


def create_super_admin(app):
    with app.app_context():

        default_super_admin_password = current_app.config['DEFAULT_SUPER_ADMIN_PASSWORD']
        default_super_admin_username = current_app.config['DEFAULT_SUPER_ADMIN_USERNAME']
        default_super_admin_email = current_app.config['DEFAULT_SUPER_ADMIN_EMAIL']

        # Check if a super admin user already exists
        super_admin_user = User.query.filter_by(email=default_super_admin_email).first()
        
        if super_admin_user:
            # Update existing super admin user
            super_admin_user.email_verified = True
            super_admin_user.is_admin = True
            super_admin_user.is_super_admin = True
            super_admin_user.license_agreed = True
            super_admin_user.set_password(default_super_admin_password)
        else:
            # Create a new super admin user
            super_admin_user = User(
                username=default_super_admin_username, 
                email=default_super_admin_email,
                email_verified=True,
                is_admin=True,
                is_super_admin=True,
                license_agreed=True
            )
            super_admin_user.set_password(default_super_admin_password)
            db.session.add(super_admin_user)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating or updating super admin user: {e}")


# Function to sign in to the admin dashboard
@admin_bp.route('/admin_dashboard')
@login_required
@require_admin
def admin_dashboard():
    if not current_user.is_super_admin and not current_user.is_admin:
        return redirect(url_for('main.index'))

    games = Game.query.all()  # Retrieve all games from the database
    form = CarouselImportForm()  # Create an instance of the form

    return render_template('admin_dashboard.html', games=games, form=form)


# ADMIN USER MANAGEMENT #
#########################
@admin_bp.route('/user_management', methods=['GET', 'POST'])
@login_required
@require_super_admin
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
@require_super_admin
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

@admin_bp.route('/update_carousel', methods=['POST'])
@login_required
@require_admin
def update_carousel():
    try:
        for i in range(1, 4):
            file = request.files.get(f'carouselImage{i}')
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                # Update your database or config here with the new filename
                # Example: CarouselImage.query.filter_by(position=i).update({'filename': filename})
                # db.session.commit()
        flash('Carousel updated successfully.', 'success')
    except Exception as e:
        flash(f'Error updating carousel: {e}', 'error')
    return redirect(url_for('admin.admin_dashboard'))

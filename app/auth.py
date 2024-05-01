from cryptography.fernet import Fernet
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required
from app.models import db, User
from app.forms import LoginForm, RegistrationForm
from app.admin import create_admin

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Check if any admin exists
    admin_exists = User.query.filter_by(is_admin=True).first() is not None

    # If no admin exists, create an admin
    if not admin_exists:
        create_admin(current_app._get_current_object())

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data  # Assuming that the LoginForm has an 'email' field
        password = form.password.data
        if not email or not password:
            flash('Please enter both email and password.')
            return redirect(url_for('auth.login'))

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=form.remember_me.data)
            flash('Logged in successfully.')
            next_page = request.args.get('next')
            # Redirect to the admin dashboard if the user is an admin
            if user.is_admin:
                return redirect(next_page or url_for('admin.admin_dashboard'))
            else:
                return redirect(next_page or url_for('main.index'))
        else:
            flash('Invalid email or password.')
    return render_template('login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('auth.login'))


def encrypt_message(message, key):
    f = Fernet(key)
    encrypted_message = f.encrypt(message.encode())
    return encrypted_message.decode()


def decrypt_message(encrypted_message, key):
    cipher = Fernet(key)
    decrypted_message = cipher.decrypt(encrypted_message.encode()).decode()
    return decrypted_message


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if form.validate_on_submit():
        email = form.email.data
        username = email.split('@')[0]  # Derive username from email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please use a different email.', 'warning')
            return redirect(url_for('auth.register'))
        
        user = User(username=username, email=email)
        user.set_password(form.password.data)
        db.session.add(user)
        
        try:
            db.session.commit()
            login_user(user)
            flash('Congratulations, you are now a registered user and logged in!', 'success')
            return redirect(url_for('main.profile'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed due to an unexpected error. Please try again.', 'error')
            current_app.logger.error(f'Failed to register user: {e}')
            
    return render_template('register.html', title='Register', form=form)

@auth_bp.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@auth_bp.route('/terms_of_service')
def terms_of_service():
    return render_template('terms_of_service.html')

@auth_bp.route('/license_agreement')
def license_agreement():
    return render_template('license_agreement.html')
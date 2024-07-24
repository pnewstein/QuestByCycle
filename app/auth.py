from cryptography.fernet import Fernet
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, Sponsor
from app.forms import LoginForm, RegistrationForm, SponsorForm, ForgotPasswordForm, ResetPasswordForm
from app.utils import send_email, generate_tutorial_game
from flask_mail import Mail
from sqlalchemy import or_
from pytz import utc
from datetime import datetime

import bleach

auth_bp = Blueprint('auth', __name__)

ALLOWED_TAGS = [
    'a', 'b', 'i', 'u', 'em', 'strong', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'blockquote', 'code', 'pre', 'br', 'div', 'span', 'ul', 'ol', 'li', 'hr',
    'sub', 'sup', 's', 'strike', 'font', 'img', 'video', 'figure'
]

ALLOWED_ATTRIBUTES = {
    '*': ['class', 'id'],
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'width', 'height'],
    'video': ['src', 'width', 'height', 'controls'],
    'p': ['class'],
    'span': ['class'],
    'div': ['class'],
    'h1': ['class'],
    'h2': ['class'],
    'h3': ['class'],
    'h4': ['class'],
    'h5': ['class'],
    'h6': ['class'],
    'blockquote': ['class'],
    'code': ['class'],
    'pre': ['class'],
    'ul': ['class'],
    'ol': ['class'],
    'li': ['class'],
    'hr': ['class'],
    'sub': ['class'],
    'sup': ['class'],
    's': ['class'],
    'strike': ['class'],
    'font': ['color', 'face', 'size']
}

def sanitize_html(html_content):
    return bleach.clean(html_content, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)

mail = Mail()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        email = sanitize_html(form.email.data)
        password = form.password.data
        if not email or not password:
            flash('Please enter both email and password.')
            return redirect(url_for('auth.login'))

        user = User.query.filter_by(email=email).first()

        if user is None:
            flash('Invalid email or password.')
            return redirect(url_for('auth.login'))

        if not user.email_verified:
            flash('Please verify your email before logging in.', 'warning')
            return render_template('login.html', form=form, show_resend=True, email=email)

        if user and user.check_password(password):
            login_user(user, remember=form.remember_me.data)
            flash('Logged in successfully.')
            next_page = request.args.get('next')
            if user.is_admin:
                return redirect(next_page or url_for('admin.admin_dashboard'))
            else:
                return redirect(next_page or url_for('main.index'))
        else:
            flash('Invalid email or password.')
    return render_template('login.html', form=form)

@auth_bp.route('/resend_verification_email', methods=['POST'])
def resend_verification_email():
    email = request.form.get('email')
    user = User.query.filter_by(email=email).first()
    if user and not user.email_verified:
        token = user.generate_verification_token()
        verify_url = url_for('auth.verify_email', token=token, _external=True)
        html = render_template('verify_email.html', verify_url=verify_url)
        subject = "Please verify your email"
        send_email(user.email, subject, html)
        flash('A new verification email has been sent. Please check your inbox.', 'info')
    else:
        flash('Email not found or already verified.', 'warning')
    return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('main.index'))


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
    form = RegistrationForm()
    if form.validate_on_submit():
        if not form.accept_license.data:
            flash('You must agree to the terms of service, license agreement, and privacy policy.', 'warning')
            return render_template('register.html', form=form)

        email = sanitize_html(form.email.data)
        base_username = email.split('@')[0]
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please use a different email.', 'warning')
            return redirect(url_for('auth.register'))

        counter = 1
        username = base_username
        while User.query.filter(or_(User.username == username, User.email == email)).first():
            username = f"{base_username}{counter}"
            counter += 1

        user = User(
            username=sanitize_html(username),
            email=email,
            license_agreed=form.accept_license.data,
            email_verified=False,
            is_admin=False,
            created_at=datetime.now(utc),
            score=0,
            display_name=None,
            profile_picture=None,
            age_group=None,
            interests=None
        )
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()

            tutorial_game = generate_tutorial_game()
            user.participated_games.append(tutorial_game)
            db.session.commit()

            token = user.generate_verification_token()
            verify_url = url_for('auth.verify_email', token=token, _external=True)
            html = render_template('verify_email.html', verify_url=verify_url)
            subject = "QuestByCycle verify email"
            send_email(user.email, subject, html)

            flash('A verification email has been sent to you. Please check your inbox.', 'info')
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            flash('Registration failed due to an unexpected error. Please try again.', 'error')
            current_app.logger.error(f'Failed to register user or send verification email: {e}')
            return render_template('register.html', title='Register', form=form)

    return render_template('register.html', title='Register', form=form)


@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if user:
            token = user.generate_reset_token()
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            html = render_template('reset_password_email.html', reset_url=reset_url)
            subject = "Password Reset Requested"
            send_email(user.email, subject, html)
            flash('A password reset email has been sent. Please check your inbox.', 'info')
        else:
            flash('No account found with that email.', 'warning')
        return redirect(url_for('auth.login'))
    return render_template('forgot_password.html', form=form)


@auth_bp.route('/verify_email/<token>')
def verify_email(token):
    user = User.verify_verification_token(token)
    if not user:
        flash('The verification link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.login'))
    
    if user.email_verified:
        flash('Your email has already been verified. Please log in.', 'info')
        return redirect(url_for('auth.login'))
    
    user.email_verified = True
    db.session.commit()
    login_user(user)  # Log in the user
    flash('Your email has been verified and you have been logged in.', 'success')
    return redirect(url_for('main.index'))


@auth_bp.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')


@auth_bp.route('/terms_of_service')
def terms_of_service():
    return render_template('terms_of_service.html')


@auth_bp.route('/license_agreement')
def license_agreement():
    return render_template('license_agreement.html')


@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.verify_reset_token(token)
    if not user:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset. Please log in with your new password.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', form=form)
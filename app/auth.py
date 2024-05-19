from cryptography.fernet import Fernet
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, Sponsor
from app.forms import LoginForm, RegistrationForm, SponsorForm
from app.admin import create_admin
from app.utils import send_email
from flask_mail import Message, Mail
from sqlalchemy import or_

from datetime import datetime

auth_bp = Blueprint('auth', __name__)

mail = Mail()

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

        if user is None:  # Check if user exists
            flash('Invalid email or password.')
            return redirect(url_for('auth.login'))
        
        # Temporary code to set email_verified to True for admin users
        #if user.is_admin and not user.email_verified:
        #    user.email_verified = True
        #    db.session.commit()

        if not user.email_verified:  # Now it's safe to check email verification
            flash('Please verify your email before logging in.', 'warning')
            return render_template('login.html', form=form, show_resend=True, email=email)

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

        email = form.email.data
        base_username = email.split('@')[0]
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please use a different email.', 'warning')
            return redirect(url_for('auth.register'))

        # Find similar usernames and generate a unique one
        counter = 1
        username = base_username
        while User.query.filter(or_(User.username == username, User.email == email)).first():
            username = f"{base_username}{counter}"
            counter += 1

        user = User(
            username=username,
            email=email,
            license_agreed=form.accept_license.data,  # Ensure license_agreed is assigned
            email_verified=False,  # Default to not verified
            is_admin=False,  # Default to not admin
            created_at=datetime.now(),
            score=0,  # Default score
            display_name=None,
            profile_picture=None,
            age_group=None,
            interests=None
        )
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()  # Commit the user creation first

            token = user.generate_verification_token()
            verify_url = url_for('auth.verify_email', token=token, _external=True)
            html = render_template('verify_email.html', verify_url=verify_url)
            subject = "QuestByCycle verify email"
            send_email(user.email, subject, html)
            
            flash('A verification email has been sent to you. Please check your inbox.', 'info')
            return redirect(url_for('auth.login'))
        
        except Exception as e:  # Now catch errors in both commit and email sending
            db.session.rollback()
            flash('Registration failed due to an unexpected error. Please try again.', 'error')
            current_app.logger.error(f'Failed to register user or send verification email: {e}')
            return render_template('register.html', title='Register', form=form)  # Stay on registration page with error

    return render_template('register.html', title='Register', form=form)


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


@auth_bp.route('/sponsors', methods=['GET'])
def sponsors():
    sponsors = Sponsor.query.all()
    return render_template('sponsors.html', sponsors=sponsors)

@auth_bp.route('/admin/sponsors', methods=['GET', 'POST'])
@login_required
def manage_sponsors():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('auth.login'))
    
    form = SponsorForm()
    if form.validate_on_submit():
        sponsor = Sponsor(
            name=form.name.data,
            website=form.website.data,
            logo=form.logo.data,
            description=form.description.data,
            tier=form.tier.data,
            game_id=form.game_id.data
        )
        db.session.add(sponsor)
        db.session.commit()
        flash('Sponsor added successfully!', 'success')
        return redirect(url_for('auth.manage_sponsors'))

    sponsors = Sponsor.query.all()
    return render_template('manage_sponsors.html', form=form, sponsors=sponsors)

@auth_bp.route('/admin/sponsors/edit/<int:sponsor_id>', methods=['GET', 'POST'])
@login_required
def edit_sponsor(sponsor_id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('auth.login'))
    
    sponsor = Sponsor.query.get_or_404(sponsor_id)
    form = SponsorForm(obj=sponsor)
    if form.validate_on_submit():
        sponsor.name = form.name.data
        sponsor.website = form.website.data
        sponsor.logo = form.logo.data
        sponsor.description = form.description.data
        sponsor.tier = form.tier.data
        sponsor.game_id = form.game_id.data
        db.session.commit()
        flash('Sponsor updated successfully!', 'success')
        return redirect(url_for('auth.manage_sponsors'))

    return render_template('edit_sponsors.html', form=form)

@auth_bp.route('/admin/sponsors/delete/<int:sponsor_id>', methods=['POST'])
@login_required
def delete_sponsor(sponsor_id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('auth.login'))
    
    sponsor = Sponsor.query.get_or_404(sponsor_id)
    db.session.delete(sponsor)
    db.session.commit()
    flash('Sponsor deleted successfully!', 'success')
    return redirect(url_for('auth.manage_sponsors'))
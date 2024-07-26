from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from app.models import db, User, Game, Sponsor
from app.forms import AddUserForm, CarouselImportForm, ForgotPasswordForm, SponsorForm
from app.utils import send_email
from functools import wraps
from werkzeug.utils import secure_filename

import bleach
import os


admin_bp = Blueprint('admin', __name__)

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
            super_admin_user.is_admin = True  # Set as admin
            super_admin_user.email_verified = True
            super_admin_user.license_agreed = True
            # ... set other fields if necessary
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


@admin_bp.route('/user_management', methods=['GET'])
@login_required
@require_super_admin
def user_management():
    users = User.query.all()
    return render_template('user_management.html', users=users)


@admin_bp.route('/user_details/<int:user_id>', methods=['GET'])
@login_required
@require_super_admin
def user_details(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user_details = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'is_admin': user.is_admin,
        'is_super_admin': user.is_super_admin,
        'created_at': user.created_at,
        'license_agreed': user.license_agreed,
        'score': user.score,
        'display_name': user.display_name,
        'profile_picture': user.profile_picture,
        'age_group': user.age_group,
        'interests': user.interests,
        'email_verified': user.email_verified,
        'participated_games': user.get_participated_games()
    }
    return jsonify(user_details)


@admin_bp.route('/update_user/<int:user_id>', methods=['POST'])
@login_required
@require_super_admin
def update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.user_management'))

    user.username = sanitize_html(request.form.get('username'))
    user.email = sanitize_html(request.form.get('email'))
    user.is_admin = 'is_admin' in request.form
    user.is_super_admin = 'is_super_admin' in request.form
    user.license_agreed = 'license_agreed' in request.form
    user.score = request.form.get('score')
    user.display_name = sanitize_html(request.form.get('display_name'))
    user.profile_picture = request.form.get('profile_picture')
    user.age_group = sanitize_html(request.form.get('age_group'))
    user.interests = sanitize_html(request.form.get('interests'))
    user.email_verified = 'email_verified' in request.form

    try:
        db.session.commit()
        flash('User updated successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user: {e}")
        flash('An error occurred while updating the user.', 'error')
    return redirect(url_for('admin.user_management'))

@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@require_super_admin
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.user_management'))

    try:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user: {e}")
        flash('An error occurred while deleting the user.', 'error')
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


@admin_bp.route('/sponsors/edit/<int:sponsor_id>', methods=['GET', 'POST'])
@login_required
@require_admin
def edit_sponsor(sponsor_id):
    sponsor = Sponsor.query.get_or_404(sponsor_id)

    # Retrieve game_id from sponsor object or fall back to query parameters or form data
    game_id = sponsor.game_id if sponsor.game_id else request.args.get('game_id', type=int)
    if request.method == 'POST':
        game_id = request.form.get('game_id', type=int)

    form = SponsorForm(obj=sponsor)
    if form.validate_on_submit():
        sponsor.name = sanitize_html(form.name.data)
        sponsor.website = sanitize_html(form.website.data)
        sponsor.logo = sanitize_html(form.logo.data)
        sponsor.description = sanitize_html(form.description.data)
        sponsor.tier = sanitize_html(form.tier.data)
        sponsor.game_id = game_id  # Use game_id from form or fallback logic
        db.session.commit()
        flash('Sponsor updated successfully!', 'success')
        return redirect(url_for('admin.manage_sponsors', game_id=game_id))  # Redirect with game_id

    return render_template('edit_sponsors.html', form=form, sponsor=sponsor, game_id=game_id)



@admin_bp.route('/sponsors/delete/<int:sponsor_id>', methods=['POST'])
@login_required
def delete_sponsor(sponsor_id):
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('auth.login'))

    game_id = request.form.get('game_id', type=int)  # Retrieve game_id from the form data

    sponsor = Sponsor.query.get_or_404(sponsor_id)
    db.session.delete(sponsor)
    try:
        db.session.commit()
        flash('Sponsor deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error occurred: {e}', 'danger')
    
    # Redirect to the manage sponsors page with the game_id
    return redirect(url_for('admin.manage_sponsors', game_id=game_id))  



@admin_bp.route('/sponsors', methods=['GET'])
def sponsors():
    game_id = request.args.get('game_id', type=int)
    if game_id:
        sponsors = Sponsor.query.filter_by(game_id=game_id).all()
    else:
        sponsors = Sponsor.query.all()
    return render_template('modal/sponsors_modal.html', sponsors=sponsors, game_id=game_id)


@admin_bp.route('/admin/sponsors', methods=['GET', 'POST'])
@login_required
def manage_sponsors():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('auth.login'))

    game_id = request.args.get('game_id', type=int)
    if request.method == 'POST':
        game_id = request.form.get('game_id', type=int)
    
    print(f"Game ID received (initial): {game_id}")  # Debugging line

    form = SponsorForm(game_id=game_id)

    if form.validate_on_submit():
        print("Form validated successfully.")  # Debugging line
        sponsor = Sponsor(
            name=sanitize_html(form.name.data),
            website=sanitize_html(form.website.data),
            logo=sanitize_html(form.logo.data),
            description=sanitize_html(form.description.data),
            tier=sanitize_html(form.tier.data),
            game_id=game_id
        )
        print(f"Creating sponsor: {sponsor}")  # Debugging line
        db.session.add(sponsor)
        try:
            db.session.commit()
            print("Sponsor added successfully!")  # Debugging line
            flash('Sponsor added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            print(f"Error adding sponsor: {e}")  # Debugging line
            flash('An error occurred while adding the sponsor.', 'error')
        return redirect(url_for('admin.manage_sponsors', game_id=game_id))
    else:
        print("Form validation failed.")  # Debugging line
        print(form.errors)  # Debugging line

    sponsors = Sponsor.query.filter_by(game_id=game_id).all() if game_id else Sponsor.query.all()
    print(f"Sponsors for game ID {game_id}: {sponsors}")  # Debugging line
    return render_template('manage_sponsors.html', form=form, sponsors=sponsors, game_id=game_id)

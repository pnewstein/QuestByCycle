from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from app.models import db, User, Game, Sponsor, user_games, QuestSubmission, UserIP
from app.forms import CarouselImportForm, SponsorForm
from app.utils import save_sponsor_logo
from functools import wraps
from werkzeug.utils import secure_filename

import bleach
import os
import logging

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


@admin_bp.route('/admin_dashboard')
@login_required
@require_admin
def admin_dashboard():
    selected_game_id = request.args.get('selected_game_id', 0)
    # Use selected_game_id as needed, for example:
    selected_game = Game.query.get(selected_game_id) if selected_game_id and int(selected_game_id) > 0 else None
    games = Game.query.all()  # or however you fetch games
    form = CarouselImportForm()
    return render_template('admin_dashboard.html', games=games, form=form,
                           selected_game_id=selected_game_id, selected_game=selected_game)


@admin_bp.route('/user_management', methods=['GET'])
@admin_bp.route('/user_management/game/<int:game_id>', methods=['GET'])
@login_required
@require_super_admin
def user_management(game_id=None):
    games = Game.query.all()  # Fetch all games for the filter dropdown

    # Determine the selected game if a game_id is provided
    selected_game = None
    if game_id:
        selected_game = Game.query.get(game_id)

    # Fetch users based on the selected game filter
    if selected_game:
        # Only get users who have participated in the selected game
        users = User.query.join(User.participated_games).filter(Game.id == game_id).all()
    else:
        # Get all users, including those not in any game
        users = User.query.outerjoin(User.participated_games).all()

    # Calculate the score per game only for the games each user has actually joined
    user_game_scores = {}
    for user in users:
        # Get games the user has participated in
        user_games = user.participated_games
        user_game_scores[user.id] = {
            game.id: user.get_score_for_game(game.id) for game in user_games
        }

    # Pass the necessary context to the template
    return render_template(
        'user_management.html',
        users=users,
        games=games,
        selected_game=selected_game,
        user_game_scores=user_game_scores
    )


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
    return render_template('user_details.html', user=user)


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
@admin_bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@require_super_admin
def edit_user(user_id):
    logging.debug("Entered edit_user function with user_id: %s", user_id)
    
    user = User.query.get(user_id)
    if not user:
        logging.error("User not found with id: %s", user_id)
        flash('User not found', 'error')
        return redirect(url_for('admin.user_management'))
    
    # Ensure user fields that are lists are non-None for template compatibility
    user.riding_preferences = user.riding_preferences or []
    user.participated_games = user.participated_games or []
    user.badges = user.badges or []
    
    if request.method == 'POST':
        logging.debug("Received POST request with form data: %s", request.form)

        try:
            # Update user details from the form
            user.username = request.form.get('username')
            user.email = request.form.get('email')
            user.is_admin = 'is_admin' in request.form
            user.is_super_admin = 'is_super_admin' in request.form
            user.license_agreed = 'license_agreed' in request.form
            user.score = int(request.form.get('score') or 0)
            user.display_name = request.form.get('display_name')
            user.profile_picture = request.form.get('profile_picture')
            user.age_group = request.form.get('age_group')
            user.interests = request.form.get('interests')
            user.email_verified = 'email_verified' in request.form

            # Update new fields for riding preferences and toggles
            riding_preferences = request.form.get('riding_preferences')
            user.riding_preferences = riding_preferences.split(',') if riding_preferences else []
            user.ride_description = request.form.get('ride_description')
            user.bike_picture = request.form.get('bike_picture')
            user.bike_description = request.form.get('bike_description')
            user.upload_to_socials = 'upload_to_socials' in request.form
            user.show_carbon_game = 'show_carbon_game' in request.form
            user.onboarded = 'onboarded' in request.form

            # Update selected_game_id if provided
            selected_game_id = request.form.get('selected_game_id')
            user.selected_game_id = int(selected_game_id) if selected_game_id else None

            logging.debug("Updated user object with new form data: %s", user)

            db.session.commit()
            logging.info("User with id %s updated successfully", user_id)
            flash('User updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            logging.error("Error updating user: %s", e)
            flash(f'Error updating user: {e}', 'error')
            return redirect(url_for('admin.edit_user', user_id=user.id))

        return redirect(url_for('admin.edit_user', user_id=user.id))

    # Safeguard all fetched data to ensure no 'None' values are passed to the template
    try:
        participated_games = user.get_participated_games() or []
        logging.debug("Fetched participated games: %s", participated_games)
    except Exception as e:
        logging.error("Error fetching participated games for user %s: %s", user_id, e)
        participated_games = []

    try:
        user_submissions = QuestSubmission.query.filter_by(user_id=user_id).all() or []
        logging.debug("Fetched user submissions: %s", user_submissions)
    except Exception as e:
        logging.error("Error fetching user submissions for user %s: %s", user_id, e)
        user_submissions = []

    try:
        user_ips = UserIP.query.filter_by(user_id=user_id).all() or []
        logging.debug("Fetched user IP addresses: %s", user_ips)
    except Exception as e:
        logging.error("Error fetching user IPs for user %s: %s", user_id, e)
        user_ips = []

    # Fetch all games for the selected_game_id dropdown, ensuring no 'None' value is passed
    try:
        games = Game.query.all() or []
        logging.debug("Fetched all games for dropdown: %s", games)
    except Exception as e:
        logging.error("Error fetching games for dropdown: %s", e)
        games = []

    return render_template(
        'edit_user.html',
        user=user,
        participated_games=participated_games,
        user_submissions=user_submissions,
        user_ips=user_ips,
        games=games
    )

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
    game_id = sponsor.game_id if sponsor.game_id else request.args.get('game_id', type=int)

    form = SponsorForm(obj=sponsor)
    form.game_id.data = game_id  # Ensure game_id is correctly set on the form

    if form.validate_on_submit():
        # Handle image upload
        if 'logo' in request.files and request.files['logo'].filename:
            image_file = request.files['logo']
            try:
                sponsor.logo = save_sponsor_logo(image_file, old_filename=sponsor.logo)
            except ValueError as e:
                flash(f"Error saving sponsor logo: {e}", 'error')
                return render_template('edit_sponsors.html', form=form, sponsor=sponsor, game_id=game_id)
        
        # Update other sponsor details
        sponsor.name = sanitize_html(form.name.data)
        sponsor.website = sanitize_html(form.website.data)
        sponsor.description = sanitize_html(form.description.data)
        sponsor.tier = sanitize_html(form.tier.data)
        sponsor.game_id = game_id  # Ensure game_id is updated
        db.session.commit()
        flash('Sponsor updated successfully!', 'success')
        return redirect(url_for('admin.manage_sponsors', game_id=game_id))

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

    form = SponsorForm()
    form.game_id.data = game_id  # Set game_id on the form

    if form.validate_on_submit():
        sponsor = Sponsor(
            name=sanitize_html(form.name.data),
            website=sanitize_html(form.website.data),
            description=sanitize_html(form.description.data),
            tier=sanitize_html(form.tier.data),
            game_id=game_id
        )

        # Handle image upload
        if 'logo' in request.files and request.files['logo'].filename:
            image_file = request.files['logo']
            try:
                sponsor.logo = save_sponsor_logo(image_file)
            except ValueError as e:
                flash(f"Error saving sponsor logo: {e}", 'error')
                return render_template('manage_sponsors.html', form=form, sponsors=[], game_id=game_id)

        db.session.add(sponsor)
        try:
            db.session.commit()
            flash('Sponsor added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while adding the sponsor: {e}', 'error')
        return redirect(url_for('admin.manage_sponsors', game_id=game_id))

    sponsors = Sponsor.query.filter_by(game_id=game_id).all() if game_id else Sponsor.query.all()
    return render_template('manage_sponsors.html', form=form, sponsors=sponsors, game_id=game_id)


@admin_bp.route('/user_emails', methods=['GET'])
@login_required
@require_super_admin
def user_emails():
    games = Game.query.all()
    game_email_map = {}

    # Fetch all users grouped by each game
    for game in games:
        users = User.query.join(user_games).filter(user_games.c.game_id == game.id).all()
        game_email_map[game.title] = [user.email for user in users]

    return render_template('user_emails.html', game_email_map=game_email_map, games=games)

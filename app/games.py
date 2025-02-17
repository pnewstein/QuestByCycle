from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, current_app, make_response
from flask_login import login_required, current_user
from app.models import db, Game, Quest, UserQuest, user_games
from app.forms import GameForm
from app.utils import save_leaderboard_image, generate_smoggy_images, allowed_file
from io import BytesIO

import bleach
import os
import qrcode
import base64

games_bp = Blueprint('games', __name__)

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

@games_bp.route('/create_game', methods=['GET', 'POST'])
@login_required
def create_game():
    form = GameForm()
    if form.validate_on_submit():
        game = Game(
            title=sanitize_html(form.title.data),
            description=sanitize_html(form.description.data),
            description2=sanitize_html(form.description2.data),
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            game_goal=form.game_goal.data,
            details=sanitize_html(form.details.data),
            awards=sanitize_html(form.awards.data),
            beyond=sanitize_html(form.beyond.data),
            twitter_username=sanitize_html(form.twitter_username.data),
            twitter_api_key=sanitize_html(form.twitter_api_key.data),
            twitter_api_secret=sanitize_html(form.twitter_api_secret.data),
            twitter_access_token=sanitize_html(form.twitter_access_token.data),
            twitter_access_token_secret=sanitize_html(form.twitter_access_token_secret.data),
            facebook_app_id=sanitize_html(form.facebook_app_id.data),
            facebook_app_secret=sanitize_html(form.facebook_app_secret.data),
            facebook_access_token=sanitize_html(form.facebook_access_token.data),
            facebook_page_id=sanitize_html(form.facebook_page_id.data),
            is_public=form.is_public.data,
            allow_joins=form.allow_joins.data,
            admin_id=current_user.id
        )
        if 'leaderboard_image' in request.files:
            image_file = request.files['leaderboard_image']
            if image_file and allowed_file(image_file.filename):
                try:
                    filename = save_leaderboard_image(image_file)
                    game.leaderboard_image = filename
                except ValueError as e:
                    flash(f'Error saving leaderboard image: {e}', 'error')
                    return render_template('create_game.html', title='Create Game', form=form)
            else:
                flash('Invalid file type for leaderboard image', 'error')
                return render_template('create_game.html', title='Create Game', form=form)

        db.session.add(game)
        try:
            db.session.commit()
            if game.leaderboard_image:
                image_path = os.path.join(current_app.root_path, 'static', game.leaderboard_image)
                generate_smoggy_images(image_path, game.id)
            flash('Game created successfully!', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while creating the game: {e}', 'error')
    return render_template('create_game.html', title='Create Game', form=form)

@games_bp.route('/update_game/<int:game_id>', methods=['GET', 'POST'])
@login_required
def update_game(game_id):
    game = Game.query.get_or_404(game_id)
    form = GameForm(obj=game)
    if form.validate_on_submit():
        game.title = sanitize_html(form.title.data)
        game.description = sanitize_html(form.description.data)
        game.description2 = sanitize_html(form.description2.data)
        game.start_date = form.start_date.data
        game.end_date = form.end_date.data
        game.game_goal = form.game_goal.data
        game.details = sanitize_html(form.details.data)
        game.awards = sanitize_html(form.awards.data)
        game.beyond = sanitize_html(form.beyond.data)
        game.twitter_username = sanitize_html(form.twitter_username.data)
        game.twitter_api_key = sanitize_html(form.twitter_api_key.data)
        game.twitter_api_secret = sanitize_html(form.twitter_api_secret.data)
        game.twitter_access_token = sanitize_html(form.twitter_access_token.data)
        game.twitter_access_token_secret = sanitize_html(form.twitter_access_token_secret.data)
        game.facebook_app_id = sanitize_html(form.facebook_app_id.data)
        game.facebook_app_secret = sanitize_html(form.facebook_app_secret.data)
        game.facebook_access_token = sanitize_html(form.facebook_access_token.data)
        game.facebook_page_id = sanitize_html(form.facebook_page_id.data)
        game.instagram_user_id = sanitize_html(form.instagram_user_id.data)
        game.instagram_access_token = sanitize_html(form.instagram_access_token.data)
        game.is_public = form.is_public.data
        game.allow_joins = form.allow_joins.data

        if 'leaderboard_image' in request.files and request.files['leaderboard_image'].filename:
            image_file = request.files['leaderboard_image']
            if image_file and allowed_file(image_file.filename):
                try:
                    filename = save_leaderboard_image(image_file)
                    game.leaderboard_image = filename

                    image_path = os.path.join(current_app.root_path, 'static', game.leaderboard_image)
                    generate_smoggy_images(image_path, game.id)
                except ValueError as e:
                    flash(f'Error saving leaderboard image: {e}', 'error')
                    return render_template('update_game.html', form=form, game_id=game_id, leaderboard_image=game.leaderboard_image)

        try:
            db.session.commit()
            flash('Game updated successfully!', 'success')
            return redirect(url_for('main.index', game_id=game_id))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating the game: {e}', 'error')
    return render_template('update_game.html', form=form, game_id=game_id, leaderboard_image=game.leaderboard_image)

@games_bp.route('/register_game/<int:game_id>', methods=['POST'])
@login_required
def register_game(game_id):
    try:
        game = Game.query.get_or_404(game_id)
        if game not in current_user.participated_games:
            stmt = user_games.insert().values(user_id=current_user.id, game_id=game_id)
            db.session.execute(stmt)
            db.session.commit()
            flash('You have successfully joined the game.', 'success')
        else:
            flash('You are already registered for this game.', 'info')
        return redirect(url_for('main.index', game_id=game_id))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Failed to register user for game {game_id}: {e}')
        flash('An error occurred. Please try again.', 'error')
    return redirect(url_for('main.index', game_id=game_id))

@games_bp.route('/delete_game/<int:game_id>', methods=['POST'])
@login_required
def delete_game(game_id):
    if not current_user.is_admin:
        flash('Access denied: Only administrators can delete games.', 'danger')
        return redirect(url_for('main.index'))

    game = Game.query.get_or_404(game_id)
    try:
        # Assuming quests are properly cascaded in model definitions
        db.session.delete(game)
        db.session.commit()
        flash('Game deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the game: {e}', 'error')

    return redirect(url_for('admin.admin_dashboard'))


@games_bp.route('/game-info/<int:game_id>')
def game_info(game_id):
    # Fetch game details using the provided game_id
    game_details = Game.query.get(game_id)
    
    # Check if game details are available, otherwise flash an error and redirect
    if not game_details:
        flash("Game details are not available.", "error")
        return redirect(url_for('main.index'))

    # If the request is for a modal version, render the modal template
    if request.args.get('modal'):
        return render_template('modals/game_info_modal.html', game=game_details, game_id=game_id)

    # Otherwise, render the full game info page
    return render_template('game_info.html', game=game_details, game_id=game_id)




@games_bp.route('/get_game_points/<int:game_id>', methods=['GET'])
@login_required
def get_game_points(game_id):
    # Query to get the total points awarded for a specific game
    total_game_points = db.session.query(
        db.func.sum(UserQuest.points_awarded)
    ).join(Quest, UserQuest.quest_id == Quest.id
    ).filter(Quest.game_id == game_id
    ).scalar() or 0

    # Query to get the goal for the specific game
    game = Game.query.get(game_id)
    game_goal = game.game_goal  # Assumes that `game_goal` is a column in your Game model

    return jsonify(total_game_points=total_game_points, game_goal=game_goal)

@games_bp.route('/game/<int:game_id>/details')
@login_required
def game_details(game_id):
    game = Game.query.get_or_404(game_id)
    return render_template('details.html', game=game)

@games_bp.route('/game/<int:game_id>/awards')
@login_required
def game_awards(game_id):
    game = Game.query.get_or_404(game_id)
    return render_template('awards.html', game=game)

@games_bp.route('/game/<int:game_id>/beyond')
@login_required
def game_beyond(game_id):
    game = Game.query.get_or_404(game_id)
    return render_template('beyond.html', game=game)

@games_bp.route('/join_custom_game', methods=['POST'])
@login_required
def join_custom_game():
    game_code = sanitize_html(request.form.get('custom_game_code'))
    if not game_code:
        flash('Game code is required to join a custom game.', 'error')
        return redirect(url_for('main.index'))

    game = Game.query.filter_by(custom_game_code=game_code).first()
    if not game:
        flash('Invalid game code. Please try again.', 'error')
        return redirect(url_for('main.index'))

    if not game.allow_joins:
        flash('This game does not allow new participants.', 'error')
        return redirect(url_for('main.index'))

    if game in current_user.participated_games:
        flash('You are already registered for this game.', 'info')
    else:
        stmt = user_games.insert().values(user_id=current_user.id, game_id=game.id)
        db.session.execute(stmt)
        db.session.commit()
        flash('You have successfully joined the custom game.', 'success')
        return redirect(url_for('main.index', game_id=game.id))

    return redirect(url_for('main.index'))

@games_bp.route('/generate_qr_for_game/<int:game_id>')
@login_required
def generate_qr_for_game(game_id):
    game = Game.query.get_or_404(game_id)
    login_url = url_for('auth.login', game_id=game_id, _external=True)  # Generate the login URL with the game_id
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(login_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="white", back_color="black")
    img_buffer = BytesIO()
    img.save(img_buffer, format="PNG")
    img_data = base64.b64encode(img_buffer.getvalue()).decode('utf-8')

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>QR Code for {game.title}</title>
        <style>
            body {{ text-align: center; padding: 20px; font-family: Arial, sans-serif; }}
            .qrcodeHeader img {{ max-width: 100%; height: auto; }}
            h1, h2 {{ margin: 10px 0; }}
            img {{ margin-top: 20px; }}
            @media print {{
                .no-print {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="qrcodeHeader">
            <img src="{url_for('static', filename='images/welcomeQuestByCycle.webp')}" alt="Welcome">
        </div>
        <h1>Join the Game!</h1>
        <h2>Scan to login or register and automatically join '{game.title}'!</h2>
        <img src="data:image/png;base64,{img_data}" alt="QR Code">
    </body>
    </html>
    """

    response = make_response(html_content)
    response.headers['Content-Type'] = 'text/html'
    return response


@games_bp.route('/get_game/<int:game_id>', methods=['GET'])
@login_required
def get_game(game_id):
    # Retrieve the game from the database or return a 404 error if not found
    game = Game.query.get_or_404(game_id)
    # Return a JSON object with the game name (you can include more details if needed)
    return jsonify(name=game.title)
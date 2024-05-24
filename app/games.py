from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models import db, Game, Task, UserTask, TaskSubmission
from app.forms import GameForm
from app.social import get_facebook_page_access_token
from datetime import datetime, timedelta, timezone

import os

games_bp = Blueprint('games', __name__)

@games_bp.route('/create_game', methods=['GET', 'POST'])
@login_required
def create_game():
    form = GameForm()
    if form.validate_on_submit():
        game = Game(
            title=form.title.data,
            description=form.description.data,
            description2=form.description2.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            game_goal=form.game_goal.data,
            details=form.details.data,
            awards=form.awards.data,
            beyond=form.beyond.data,
            twitter_username=form.twitter_username.data,
            twitter_api_key=form.twitter_api_key.data,
            twitter_api_secret=form.twitter_api_secret.data,
            twitter_access_token=form.twitter_access_token.data,
            twitter_access_token_secret=form.twitter_access_token_secret.data,
            facebook_app_id=form.facebook_app_id.data,
            facebook_app_secret=form.facebook_app_secret.data,
            facebook_access_token=form.facebook_access_token.data,
            facebook_page_id=form.facebook_page_id.data,
            is_public=form.is_public.data,
            allow_joins=form.allow_joins.data,
            admin_id=current_user.id
        )
        db.session.add(game)
        try:
            db.session.commit()
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
        form.populate_obj(game)  # This will automatically update all fields including new ones
        try:
            db.session.commit()
            flash('Game updated successfully!', 'success')
            return redirect(url_for('main.index', game_id=game_id))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating the game: {e}', 'error')
    return render_template('update_game.html', form=form, game_id=game_id)


@games_bp.route('/register_game/<int:game_id>', methods=['POST'])
@login_required
def register_game(game_id):
    try:
        game = Game.query.get_or_404(game_id)
        if game not in current_user.participated_games:
            current_user.participated_games.append(game)
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
        # Assuming tasks are properly cascaded in model definitions
        db.session.delete(game)
        db.session.commit()
        flash('Game deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the game: {e}', 'error')

    return redirect(url_for('admin.admin_dashboard'))

@games_bp.route('/get_game_points/<int:game_id>', methods=['GET'])
@login_required
def get_game_points(game_id):
    # Query to get the total points awarded for a specific game
    total_game_points = db.session.query(
        db.func.sum(UserTask.points_awarded)
    ).join(Task, UserTask.task_id == Task.id
    ).filter(Task.game_id == game_id
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
    game_code = request.form.get('custom_game_code')
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
        current_user.participated_games.append(game)
        db.session.commit()
        flash('You have successfully joined the custom game.', 'success')

    return redirect(url_for('main.index'))
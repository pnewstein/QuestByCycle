from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, current_app
from flask_login import current_user, login_required, logout_user
from app.utils import save_profile_picture, award_badges
from app.models import db, Game, User, Task, UserTask, TaskLike, ShoutBoardMessage, ShoutBoardLike
from app.forms import ProfileForm, ShoutBoardForm
from .config import load_config
from werkzeug.utils import secure_filename
from sqlalchemy import func

import pytz  # Make sure pytz is installed
import os
import logging

main_bp = Blueprint('main', __name__)

config = load_config()

utc = pytz.UTC  # Define UTC timezone

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def get_datetime(activity):
    if hasattr(activity, 'timestamp'):
        return activity.timestamp.replace(tzinfo=utc) if activity.timestamp.tzinfo is None else activity.timestamp
    else:
        return activity.completed_at


@main_bp.route('/')
def index():
    games = Game.query.all()
    tasks = Task.query.all()
    form = ShoutBoardForm()
    messages = ShoutBoardMessage.query.order_by(ShoutBoardMessage.timestamp.desc()).all()
    completed_tasks = UserTask.query.filter(UserTask.completions > 0).order_by(UserTask.completed_at.desc()).all()
    total_points = UserTask.query.filter_by(user_id=current_user.id).with_entities(func.sum(UserTask.points_awarded)).scalar() if current_user.is_authenticated else 0

    # Check if the user is authenticated to safely access participated_games
    if current_user.is_authenticated:
        game_participation = {game.id: game in current_user.participated_games for game in games}
        liked_message_ids = {like.message_id for like in ShoutBoardLike.query.filter_by(user_id=current_user.id)}
        liked_task_ids = {like.task_id for like in TaskLike.query.filter_by(user_id=current_user.id)}
        user_games = current_user.participated_games
    else:
        game_participation = {game.id: False for game in games}
        liked_message_ids = set()
        liked_task_ids = set()
        user_games = []

    for message in messages:
        message.liked_by_user = message.id in liked_message_ids

    for task in tasks:
        task.liked_by_user = task.id in liked_task_ids

    activities = messages + completed_tasks
    activities.sort(key=lambda x: get_datetime(x), reverse=True)

    return render_template('index.html', form=form, games=games, user_games=user_games, activities=activities, tasks=tasks, total_points=total_points, game_participation=game_participation)


@main_bp.route('/shout-board', methods=['POST'])
@login_required
def shout_board():
    form = ShoutBoardForm()
    if form.validate_on_submit():
        shout_message = ShoutBoardMessage(message=form.message.data, user_id=current_user.id)
        db.session.add(shout_message)
        db.session.commit()
        flash('Your message has been posted!', 'success')
        return redirect(url_for('main.index'))
    messages = ShoutBoardMessage.query.order_by(ShoutBoardMessage.timestamp.desc()).all()
    return render_template('shout_board.html', form=form, messages=messages)


@main_bp.route('/like-message/<int:message_id>', methods=['POST'])
@login_required
def like_message(message_id):
    # Retrieve the message by ID
    message = ShoutBoardMessage.query.get_or_404(message_id)
    # Check if the current user already liked this message
    already_liked = ShoutBoardLike.query.filter_by(user_id=current_user.id, message_id=message.id).first() is not None

    if not already_liked:
        # User has not liked this message before, so create a new like
        new_like = ShoutBoardLike(user_id=current_user.id, message_id=message.id)
        db.session.add(new_like)
        db.session.commit()
        success = True
    else:
        # User already liked the message. Optionally, handle "unliking" here
        success = False
    
    # Fetch the new like count for the message
    new_like_count = ShoutBoardMessage.query.get(message_id).likes.count()
    return jsonify(success=success, new_like_count=new_like_count, already_liked=already_liked)


@main_bp.route('/request_custom/<int:user_id>', methods=['GET', 'POST'])
def custom_request(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('request_custom.html', user=user)


@main_bp.route('/leaderboard', methods=['GET'])
@login_required
def leaderboard():
    user_games = current_user.participated_games
    selected_game_id = request.args.get('game_id', type=int)

    if len(user_games) == 1:
        single_game_id = user_games[0].id
        if selected_game_id is None or selected_game_id != single_game_id:
            return redirect(url_for('main.leaderboard', game_id=single_game_id))

    top_users = []
    total_game_points = 0
    game_goal = None  # Initialize game goal as None

    if selected_game_id:
        game = Game.query.get(selected_game_id)
        game_goal = game.game_goal if game else None

        top_users = db.session.query(
            User.id,
            User.username,
            db.func.sum(UserTask.points_awarded).label('total_points')
        ).join(UserTask, UserTask.user_id == User.id
        ).join(Task, Task.id == UserTask.task_id
        ).filter(Task.game_id == selected_game_id
        ).group_by(User.id, User.username
        ).order_by(db.func.sum(UserTask.points_awarded).desc()
        ).all()

        total_game_points = db.session.query(
            db.func.sum(UserTask.points_awarded)
        ).join(Task, UserTask.task_id == Task.id
        ).filter(Task.game_id == selected_game_id
        ).scalar() or 0

    return render_template('leaderboard.html', games=user_games, top_users=top_users, selected_game_id=selected_game_id, total_game_points=total_game_points, game_goal=game_goal)

@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()

    if form.validate_on_submit():
        current_user.display_name = form.display_name.data
        current_user.age_group = form.age_group.data
        current_user.interests = form.interests.data

        # Check if 'profile_picture' is in request.files
        if 'profile_picture' in request.files:
            profile_picture_file = request.files['profile_picture']
            if profile_picture_file.filename != '':
                filename = save_profile_picture(profile_picture_file)  # Using your save_profile_picture function
                current_user.profile_picture = filename  # Save just the filename or relative path
                db.session.commit()
                flash('Profile updated successfully.', 'success')
            else:
                flash('No file selected for upload.', 'error')
        else:
            flash('No file part in the request.', 'error')

        return redirect(url_for('main.profile'))
    elif request.method == 'GET':
        form.display_name.data = current_user.display_name
        form.age_group.data = current_user.age_group
        form.interests.data = current_user.interests
        # Load other fields if necessary

    return render_template('profile.html', form=form)

@main_bp.route('/profile/<int:user_id>')
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    user_tasks = UserTask.query.filter_by(user_id=user.id).all()
    badges = user.badges

    # Debug prints to verify the data being sent to the template
    print(f"Loading profile for user: {user.username}, ID: {user_id}")
    print(f"Tasks loaded: {len(user_tasks)}")
    print(f"Badges loaded: {len(badges)}")
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return only the part of the page needed for the modal
        return render_template('_user_profile_modal_content.html', user=user)
    else:
        # Return the full page
        return render_template('_user_profile.html', user=user, user_tasks=user_tasks, badges=badges)
    

@main_bp.route('/like_task/<int:task_id>', methods=['POST'])
@login_required
def like_task(task_id):
    task = Task.query.get_or_404(task_id)
    # Check if the current user already liked this task
    already_liked = TaskLike.query.filter_by(user_id=current_user.id, task_id=task.id).first() is not None

    if not already_liked:
        # User has not liked this task before, so create a new like
        new_like = TaskLike(user_id=current_user.id, task_id=task.id)
        db.session.add(new_like)
        db.session.commit()
        success = True
    else:
        # User already liked the task. Optionally, handle "unliking" here
        success = False

    # Fetch the new like count for the task
    new_like_count = Task.query.get(task_id).likes.count()
    return jsonify(success=success, new_like_count=new_like_count, already_liked=already_liked)

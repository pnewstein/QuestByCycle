from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, current_app
from flask_login import current_user, login_required, logout_user
from app.utils import save_profile_picture, award_badges
from app.models import db, Game, User, Task, UserTask, TaskSubmission, TaskLike, ShoutBoardMessage, ShoutBoardLike
from app.forms import ProfileForm, ShoutBoardForm
from .config import load_config
from werkzeug.utils import secure_filename
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

import pytz  # Make sure pytz is installed
import os
import logging

main_bp = Blueprint('main', __name__)

config = load_config()


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def get_datetime(activity):
    if hasattr(activity, 'timestamp') and isinstance(activity.timestamp, datetime):
        return activity.timestamp.replace(tzinfo=None) if activity.timestamp.tzinfo is not None else activity.timestamp
    elif hasattr(activity, 'completed_at') and isinstance(activity.completed_at, datetime):
        return activity.completed_at.replace(tzinfo=None)
    else:
        raise ValueError("Activity object does not contain valid timestamp information.")


@main_bp.route('/', defaults={'game_id': None, 'task_id': None, 'user_id': None})
@main_bp.route('/<int:game_id>', defaults={'task_id': None, 'user_id': None})
@main_bp.route('/<int:game_id>/<int:task_id>', defaults={'user_id': None})
@main_bp.route('/<int:game_id>/<int:task_id>/<int:user_id>')
def index(game_id, task_id, user_id):
    user_games = [] 
    profile = None  # Initialize profile here
    user_tasks = []  # Initialize user_tasks here
    badges = []
    total_points = None

    if user_id is None and current_user.is_authenticated:
        user_id = current_user.id

    if game_id is None and current_user.is_authenticated:
        # If user is part of a game, redirect to the latest joined game
        joined_games = current_user.participated_games
        if joined_games:
            game_id = joined_games[-1].id  # Assuming the latest joined game is the last in the list
        else:
            # Automatically join the latest game if not part of any
            latest_game = Game.query.order_by(Game.start_date.desc()).first()
            if latest_game:
                current_user.participated_games.append(latest_game)
                db.session.commit()
                game_id = latest_game.id

    game = Game.query.get(game_id) if game_id else None

    carousel_images_dir = os.path.join(current_app.root_path, 'static', current_app.config['CAROUSEL_IMAGES_DIR'])
    
    if current_user.is_authenticated:
        user_tasks = UserTask.query.filter_by(user_id=current_user.id).all()
        total_points = sum(ut.points_awarded for ut in user_tasks if ut.task.game_id == game_id)

    if not os.path.exists(carousel_images_dir):
        os.makedirs(carousel_images_dir)

    carousel_images = os.listdir(carousel_images_dir)
    carousel_images = [os.path.join(current_app.config['CAROUSEL_IMAGES_DIR'], filename) for filename in carousel_images]

    tasks = Task.query.filter_by(game_id=game.id, enabled=True).all() if game else []
    has_joined = game in current_user.participated_games if game else False
    game_participation = {game.id: has_joined} if game else {}

    form = ShoutBoardForm()
    messages = ShoutBoardMessage.query.order_by(ShoutBoardMessage.timestamp.desc()).all()
    completed_tasks = UserTask.query.filter(UserTask.completions > 0).order_by(UserTask.completed_at.desc()).all()
    activities = messages + completed_tasks
    activities.sort(key=lambda x: get_datetime(x), reverse=True)

    selected_task = Task.query.get(task_id) if task_id else None

    if current_user.is_authenticated:
        liked_message_ids = {like.message_id for like in ShoutBoardLike.query.filter_by(user_id=current_user.id)}
        liked_task_ids = {like.task_id for like in TaskLike.query.filter_by(user_id=current_user.id)}
        user_games = current_user.participated_games
        profile = User.query.get_or_404(user_id)
        user_tasks = UserTask.query.filter_by(user_id=profile.id).all()
        badges = profile.badges

    for task in tasks:
        completions = sum(1 for ut in user_tasks if ut.task_id == task.id and ut.completions > 0)
        task.completions_within_period = completions
        task.can_verify = False
        task.last_completion = None
        task.first_completion_in_period = None
        task.next_eligible_time = None
        task.completion_timestamps = []

        now = datetime.now()
        period_start_map = {
            'daily': timedelta(days=1),
            'weekly': timedelta(weeks=1),
            'monthly': timedelta(days=30)
        }
        period_start = now - period_start_map.get(task.frequency, timedelta(days=1))

        submissions = TaskSubmission.query.filter(
            TaskSubmission.user_id == current_user.id,
            TaskSubmission.task_id == task.id,
            TaskSubmission.timestamp >= period_start
        ).all()

        if submissions:
            task.completions_within_period = len(submissions)
            task.first_completion_in_period = min(submissions, key=lambda x: x.timestamp).timestamp
            task.completion_timestamps = [sub.timestamp for sub in submissions]

        relevant_user_tasks = [ut for ut in user_tasks if ut.task_id == task.id]
        task.total_completions = len(relevant_user_tasks)
        task.last_completion = max((ut.completed_at for ut in relevant_user_tasks), default=None)

        if task.total_completions < task.completion_limit:
            task.can_verify = True
        else:
            last_completion = max(submissions, key=lambda x: x.timestamp, default=None)
            if last_completion:
                increment_map = {
                    'daily': timedelta(days=1),
                    'weekly': timedelta(weeks=1),
                    'monthly': timedelta(days=30)
                }
                task.next_eligible_time = last_completion.timestamp + increment_map.get(task.frequency, timedelta(days=1))

    tasks.sort(key=lambda x: (x.completions_within_period if hasattr(x, 'completions_within_period') else 0), reverse=True)
   
    if current_user.is_authenticated:
        profform = ProfileForm()

        if request.method == 'POST':
            if profform.validate_on_submit():
                current_user.display_name = profform.display_name.data
                current_user.age_group = profform.age_group.data
                current_user.interests = profform.interests.data

                # Handle profile picture
                if 'profile_picture' in request.files:
                    profile_picture_file = request.files['profile_picture']
                    if profile_picture_file.filename != '':
                        filename = save_profile_picture(profile_picture_file)
                        current_user.profile_picture = filename

                db.session.commit()
                flash('Profile updated successfully.', 'success')
                return redirect(url_for('main.profile'))

        elif request.method == 'GET':
            profform.display_name.data = current_user.display_name
            profform.age_group.data = current_user.age_group
            profform.interests.data = current_user.interests


    return render_template('index.html',
                           form=form,
                           games=user_games,
                           game=game,
                           user_games=user_games,
                           activities=activities,
                           tasks=tasks,
                           game_participation=game_participation,
                           selected_task=selected_task,
                           has_joined=has_joined,
                           profile=profile,
                           user_tasks=user_tasks,
                           badges=badges,
                           carousel_images=carousel_images,
                           total_points=total_points)


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


@main_bp.route('/leaderboard_partial')
@login_required
def leaderboard_partial():
    selected_game_id = request.args.get('game_id', type=int)

    if selected_game_id:
        game = Game.query.get(selected_game_id)
        if not game:
            return jsonify({'error': 'Game not found'}), 404

        top_users_query = db.session.query(
            User.id,
            User.username,
            db.func.sum(UserTask.points_awarded).label('total_points')
        ).join(UserTask, UserTask.user_id == User.id
        ).join(Task, Task.id == UserTask.task_id
        ).filter(Task.game_id == selected_game_id
        ).group_by(User.id, User.username
        ).order_by(db.func.sum(UserTask.points_awarded).desc()
        ).all()

        top_users = [{
            'user_id': user_id,
            'username': username,
            'total_points': total_points
        } for user_id, username, total_points in top_users_query]

        total_game_points = db.session.query(
            db.func.sum(UserTask.points_awarded)
        ).join(Task, UserTask.task_id == Task.id
        ).filter(Task.game_id == selected_game_id
        ).scalar() or 0

        return jsonify({
            'top_users': top_users,
            'total_game_points': total_game_points,
            'game_goal': game.game_goal if game.game_goal else None
        })


@main_bp.route('/profile', methods=['GET', 'POST', 'DELETE'])
@login_required
def profile():
    form = ProfileForm()

    if request.method == 'POST':
        if form.validate_on_submit():
            current_user.display_name = form.display_name.data
            current_user.age_group = form.age_group.data
            current_user.interests = form.interests.data

            # Handle profile picture
            if 'profile_picture' in request.files:
                profile_picture_file = request.files['profile_picture']
                if profile_picture_file.filename != '':
                    filename = save_profile_picture(profile_picture_file)
                    current_user.profile_picture = filename

            db.session.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('main.profile'))

    elif request.method == 'DELETE':
        db.session.delete(current_user)
        db.session.commit()
        logout_user()
        flash('Profile deleted successfully.', 'info')
        return redirect(url_for('main.index'))

    elif request.method == 'GET':
        form.display_name.data = current_user.display_name
        form.age_group.data = current_user.age_group
        form.interests.data = current_user.interests

    return render_template('profile.html', form=form)


@main_bp.route('/profile/<int:user_id>')
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    user_tasks = UserTask.query.filter(UserTask.user_id == user.id, UserTask.completions > 0).all()
    badges = user.badges

    # Debug prints to verify the data being sent to the template
    print(f"Loading profile for user: {user.username}, ID: {user_id}")
    print(f"Tasks loaded: {len(user_tasks)}")
    print(f"Badges loaded: {len(badges)}")
    
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
    new_like_count = TaskLike.query.filter_by(task_id=task.id).count()
    return jsonify(success=success, new_like_count=new_like_count, already_liked=already_liked)


@main_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file:
            old_filename = current_user.profile_picture
            current_user.profile_picture = save_profile_picture(file, old_filename)
    
    # Assuming you have a form or JSON data to update other user attributes
    current_user.display_name = request.form.get('display_name', current_user.display_name)
    current_user.age_group = request.form.get('age_group', current_user.age_group)
    current_user.interests = request.form.get('interests', current_user.interests)

    db.session.commit()
    return jsonify(success=True)

@main_bp.route('/game-info')
def game_info():
    game_details = Game.query.first()  # Simplified for example, adjust based on how you want to select the game
    if not game_details:
        flash("Game details are not available.", "error")
        return redirect(url_for('main.index'))
    return render_template('game_info.html', game=game_details)
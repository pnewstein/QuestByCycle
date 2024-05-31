from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, current_app
from flask_login import current_user, login_required, logout_user
from app.utils import save_profile_picture, award_badges
from app.models import db, Game, User, Task, UserTask, TaskSubmission, TaskLike, ShoutBoardMessage, ShoutBoardLike
from app.forms import ProfileForm, ShoutBoardForm, ContactForm
from app.utils import send_email
from .config import load_config
from werkzeug.utils import secure_filename
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from pytz import utc

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
    profile = None
    user_tasks = []
    badges = []
    total_points = None

    if user_id is None and current_user.is_authenticated:
        user_id = current_user.id

    # Auto join the first or earliest game 
    if game_id is None and current_user.is_authenticated:
        joined_games = current_user.participated_games
        if joined_games:
            game_id = joined_games[0].id
        else:
            earliest_game = Game.query.order_by(Game.start_date.asc()).first()
            if earliest_game:
                current_user.participated_games.append(earliest_game)
                db.session.commit()
                game_id = earliest_game.id

    game = Game.query.get(game_id) if game_id else None

    carousel_images_dir = os.path.join(current_app.root_path, 'static', 'images', current_app.config['CAROUSEL_IMAGES_DIR'])

    if not os.path.exists(carousel_images_dir):
        os.makedirs(carousel_images_dir)

    carousel_images = os.listdir(carousel_images_dir)
    carousel_images = [os.path.join('images', current_app.config['CAROUSEL_IMAGES_DIR'], filename) for filename in carousel_images]

    if current_user.is_authenticated:
        user_tasks = UserTask.query.filter_by(user_id=current_user.id).all()
        total_points = sum(ut.points_awarded for ut in user_tasks if ut.task.game_id == game_id)

    tasks = Task.query.filter_by(game_id=game.id, enabled=True).all() if game else []
    has_joined = game in current_user.participated_games if game else False
    game_participation = {game.id: has_joined} if game else {}

    form = ShoutBoardForm()
    pinned_messages = ShoutBoardMessage.query.filter_by(is_pinned=True).order_by(ShoutBoardMessage.timestamp.desc()).all()
    unpinned_messages = ShoutBoardMessage.query.filter_by(is_pinned=False).order_by(ShoutBoardMessage.timestamp.desc()).all()
    completed_tasks = UserTask.query.filter(UserTask.completions > 0).order_by(UserTask.completed_at.desc()).all()

    pinned_activities = pinned_messages
    unpinned_activities = unpinned_messages + completed_tasks
    unpinned_activities.sort(key=lambda x: get_datetime(x), reverse=True)
    activities = pinned_activities + unpinned_activities

    selected_task = Task.query.get(task_id) if task_id else None

    if current_user.is_authenticated:
        liked_message_ids = {like.message_id for like in ShoutBoardLike.query.filter_by(user_id=current_user.id)}
        liked_task_ids = {like.task_id for like in TaskLike.query.filter_by(user_id=current_user.id)}
        user_games = current_user.participated_games
        profile = User.query.get_or_404(user_id)
        user_tasks = UserTask.query.filter_by(user_id=profile.id).all()
        badges = profile.badges

        if not profile.display_name:
            profile.display_name = profile.username

    now = datetime.now(utc)
    period_start_map = {
        'daily': timedelta(days=1),
        'weekly': timedelta(weeks=1),
        'monthly': timedelta(days=30)
    }

    for task in tasks:
        task.total_completions = db.session.query(TaskSubmission).filter(TaskSubmission.task_id == task.id).count()
        task.personal_completions = db.session.query(TaskSubmission).filter(TaskSubmission.task_id == task.id, TaskSubmission.user_id == user_id).count() if user_id else 0
        task.completions_within_period = 0
        task.can_verify = False
        task.last_completion = None
        task.first_completion_in_period = None
        task.next_eligible_time = None
        task.completion_timestamps = []

        if user_id:
            period_start = now - period_start_map.get(task.frequency, timedelta(days=1))
            submissions = TaskSubmission.query.filter(
                TaskSubmission.user_id == user_id,
                TaskSubmission.task_id == task.id,
                TaskSubmission.timestamp >= period_start
            ).all()

            if submissions:
                task.completions_within_period = len(submissions)
                task.first_completion_in_period = min(submissions, key=lambda x: x.timestamp).timestamp
                task.completion_timestamps = [sub.timestamp for sub in submissions]

            relevant_user_tasks = [ut for ut in user_tasks if ut.task_id == task.id]
            task.last_completion = max((ut.completed_at for ut in relevant_user_tasks), default=None)

            if task.personal_completions < task.completion_limit:
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

    tasks.sort(key=lambda x: (-x.is_sponsored, -x.personal_completions, -x.total_completions))

    custom_games = Game.query.filter(Game.custom_game_code.isnot(None), Game.is_public.is_(True)).all()

    if current_user.is_authenticated:
        profform = ProfileForm()

        if request.method == 'POST':
            if profform.validate_on_submit():
                current_user.display_name = profform.display_name.data
                current_user.age_group = profform.age_group.data
                current_user.interests = profform.interests.data

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
                           total_points=total_points,
                           completions=completed_tasks,
                           custom_games=custom_games,
                           selected_game_id=game_id)


@main_bp.route('/shout-board', methods=['POST'])
@login_required
def shout_board():
    form = ShoutBoardForm()
    if form.validate_on_submit():
        is_pinned = 'is_pinned' in request.form  # Check if the pin checkbox was checked
        shout_message = ShoutBoardMessage(message=form.message.data, user_id=current_user.id, is_pinned=is_pinned)
        db.session.add(shout_message)
        db.session.commit()
        flash('Your message has been posted!', 'success')
        return redirect(url_for('main.index'))
    return render_template('shout_board.html', form=form)


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
    new_like_count = db.session.query(ShoutBoardLike).filter_by(message_id=message_id).count()
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
            User.display_name,
            db.func.sum(UserTask.points_awarded).label('total_points')
        ).join(UserTask, UserTask.user_id == User.id
        ).join(Task, Task.id == UserTask.task_id
        ).filter(Task.game_id == selected_game_id
        ).group_by(User.id, User.username, User.display_name
        ).order_by(db.func.sum(UserTask.points_awarded).desc()
        ).all()

        top_users = [{
            'user_id': user_id,
            'username': username,
            'display_name': display_name,
            'total_points': total_points
        } for user_id, username, display_name, total_points in top_users_query]

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


@main_bp.route('/profile/<int:user_id>')
@login_required
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    user_tasks = UserTask.query.filter(UserTask.user_id == user.id, UserTask.completions > 0).all()
    badges = user.badges
    participated_games = user.participated_games
    task_submissions = user.task_submissions

    response_data = {
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'profile_picture': user.profile_picture,
            'display_name': user.display_name,
            'interests': user.interests,
            'age_group': user.age_group,
            'badges': [{'id': badge.id, 'name': badge.name, 'description': badge.description, 'category': badge.category, 'image': badge.image} for badge in badges]
        },
        'user_tasks': [
            {'id': task.id, 'completions': task.completions}
            for task in user_tasks
        ],
        'participated_games': [
            {'id': game.id, 'title': game.title, 'description': game.description, 'start_date': game.start_date.strftime('%B %d, %Y'), 'end_date': game.end_date.strftime('%B %d, %Y')}
            for game in participated_games
        ],
        'task_submissions': [
            {'id': submission.id, 'task': {'title': submission.task.title}, 'comment': submission.comment, 'timestamp': submission.timestamp.strftime('%B %d, %Y %H:%M'), 'image_url': submission.image_url, 'twitter_url': submission.twitter_url, 'fb_url': submission.fb_url}
            for submission in task_submissions
        ]
    }

    return jsonify(response_data)

@main_bp.route('/profile/<int:user_id>/edit', methods=['POST'])
@login_required
def edit_profile(user_id):
    if current_user.id != user_id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    data = request.get_json()
    user = User.query.get_or_404(user_id)
    
    user.display_name = data.get('display_name', user.display_name)
    user.interests = data.get('interests', user.interests)
    user.age_group = data.get('age_group', user.age_group)
    
    try:
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


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


@main_bp.route('/pin_message/<int:message_id>', methods=['POST'])
@login_required
def pin_message(message_id):
    message = ShoutBoardMessage.query.get_or_404(message_id)
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('main.index'))
    
    message.is_pinned = not message.is_pinned  # Toggle the pin status
    db.session.commit()
    flash('Message pin status updated.', 'success')
    return redirect(url_for('main.index'))


@main_bp.route('/contact', methods=['POST'])
@login_required
def contact():    
    form = ContactForm()
    if form.validate_on_submit():
        message = form.message.data
        subject = "New Contact Form Submission"
        recipient = current_app.config['MAIL_DEFAULT_SENDER']  # Replace with the desired recipient email

        user_info = None
        if current_user.is_authenticated:
            user_info = {
                "username": current_user.username,
                "email": current_user.email,
                "is_admin": current_user.is_admin,
                "created_at": current_user.created_at,
                "license_agreed": current_user.license_agreed,
                "display_name": current_user.display_name,
                "age_group": current_user.age_group,
                "interests": current_user.interests,
                "email_verified": current_user.email_verified,
            }

        html = render_template('contact_email.html', message=message, user_info=user_info)
        try:
            send_email(recipient, subject, html)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=True)
            flash('Your message has been sent successfully.', 'success')
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, message="Failed to send your message"), 500
            flash('Failed to send your message. Please try again later.', 'error')
            current_app.logger.error(f'Failed to send contact form message: {e}')
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, message="Validation failed"), 400
        flash('Validation failed. Please ensure all fields are filled correctly.', 'warning')

    return redirect(url_for('main.index'))

from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, session, current_app, send_from_directory
from flask_login import current_user, login_required, logout_user
from flask_wtf.csrf import generate_csrf
from app.models import db, Event, User, Task, UserTask, Badge, ShoutBoardMessage, ShoutBoardLike
from app.forms import SignInForm, ProfileForm, ShoutBoardForm
from .config import load_config
from werkzeug.utils import secure_filename

import os
import logging
import uuid

main_bp = Blueprint('main', __name__)

config = load_config()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@main_bp.route('/')
def index():
    events = Event.query.all()
    form = ShoutBoardForm()
    messages = ShoutBoardMessage.query.order_by(ShoutBoardMessage.timestamp.desc()).all()
    liked_message_ids = {like.message_id for like in ShoutBoardLike.query.filter_by(user_id=current_user.id)} if current_user.is_authenticated else set()
    
    for message in messages:
        message.liked_by_user = message.id in liked_message_ids

    if current_user.is_authenticated:
        user_events = current_user.participated_events  # Directly access the events
    else:
        user_events = []

    return render_template('index.html', form=form, events=events, user_events=user_events, messages=messages)


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


@main_bp.route('/sign-in', methods=['GET', 'POST'])
def sign_in():
    form = SignInForm()

    if form.validate_on_submit():

        flash('Signed in successfully')
        return redirect(url_for('main.index'))

    return render_template('sign_in.html', form=form)


@main_bp.route('/request_custom/<int:user_id>', methods=['GET', 'POST'])
def custom_request(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('request_custom.html', user=user)


@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))

@main_bp.route('/leaderboard', methods=['GET'])
@login_required
def leaderboard():
    # Retrieve events the current user has joined
    user_events = current_user.participated_events
    # Try to get 'event_id' from query parameters
    selected_event_id = request.args.get('event_id', type=int)

    # If the user is part of only one event and 'event_id' is not specified or differs, redirect to that event's leaderboard
    if len(user_events) == 1:
        single_event_id = user_events[0].id
        if selected_event_id is None or selected_event_id != single_event_id:
            return redirect(url_for('main.leaderboard', event_id=single_event_id))

    # Use the selected_event_id if provided, otherwise default to None
    # This will be used to fetch the leaderboard for the specific event
    top_users = []
    if selected_event_id:
        top_users = db.session.query(
            User.id,
            User.username,
            db.func.sum(UserTask.points_awarded).label('total_points')
        ).join(UserTask, UserTask.user_id == User.id
        ).join(Task, Task.id == UserTask.task_id
        ).filter(Task.event_id == selected_event_id
        ).group_by(User.id, User.username
        ).order_by(db.func.sum(UserTask.points_awarded).desc()
        ).all()

    # Render the leaderboard template with the necessary data
    return render_template('leaderboard.html', events=user_events, top_users=top_users, selected_event_id=selected_event_id)


def save_profile_picture(profile_picture_file):
    ext = profile_picture_file.filename.rsplit('.', 1)[-1]
    filename = secure_filename(f"{uuid.uuid4()}.{ext}")
    # Ensure 'uploads' directory exists under 'static'
    uploads_path = os.path.join(current_app.root_path, 'static', current_app.config['main']['UPLOAD_FOLDER'])
    if not os.path.exists(uploads_path):
        os.makedirs(uploads_path)
    # Save file
    profile_picture_file.save(os.path.join(uploads_path, filename))
    return os.path.join(current_app.config['main']['UPLOAD_FOLDER'], filename)


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
@login_required
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    print(f"Accessing profile for user: {user.username}, Admin: {user.is_admin}")  # Debugging print


    user_tasks = UserTask.query.filter_by(user_id=user.id).all()
    badges = user.badges

    return render_template('_user_profile.html', user=user, user_tasks=user_tasks, badges=badges)

def award_badges(user_id):
    user = User.query.get_or_404(user_id)
    for task in user.user_tasks:
        if task.completed and task.task.badge_id:  # Assuming task links to UserTask which links to Task
            badge = Badge.query.get(task.task.badge_id)
            if badge and badge not in user.badges:
                user.badges.append(badge)
    db.session.commit()
    flash('Badges updated based on completed tasks.', 'success')


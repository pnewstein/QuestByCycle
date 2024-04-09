from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from app.forms import EventForm, TaskForm
from .models import db, Task, Badge, UserTask, Event, User, ShoutBoardMessage
from werkzeug.utils import secure_filename

import uuid
import csv
import os

MAX_POINTS_INT = 2**63 - 1


def update_user_score(user_id):
    user = User.query.get(user_id)
    total_points = sum(task.points_awarded for task in user.user_tasks)
    user.score = min(total_points, MAX_POINTS_INT)
    db.session.commit()


def award_badge(user_id):
    user = User.query.get(user_id)
    completed_tasks = UserTask.query.filter_by(user_id=user_id, completions=1).all()

    for user_task in completed_tasks:
        task = Task.query.get(user_task.task_id)
        if task.badge and task.badge not in user.badges:
            user.badges.append(task.badge)
            shout_message = ShoutBoardMessage(message=f"{current_user.username} has just earned the {task.badge.name} badge!", user_id=user_id)
            db.session.add(shout_message)
            db.session.commit()
            flash(f"Badge '{task.badge.name}' awarded for completing task '{task.title}'.")


def award_badges(user_id):
    user = User.query.get_or_404(user_id)
    for task in user.user_tasks:
        if task.completed and task.task.badge_id:  # Assuming task links to UserTask which links to Task
            badge = Badge.query.get(task.task.badge_id)
            if badge and badge not in user.badges:
                user.badges.append(badge)
    db.session.commit()
    flash('Badges updated based on completed tasks.', 'success')



def revoke_badge(user_id):
    user = User.query.get(user_id)

    completed_tasks = UserTask.query.filter_by(user_id=user_id, completions=0).all()
    for user_task in completed_tasks:

        task = Task.query.get(user_task.task_id)
        if task.badge and task.badge in user.badges:
            user.badges.remove(task.badge)
            db.session.commit()
            flash(f"Badge '{task.badge.name}' revoked as the task '{task.title}' is no longer completed.", 'info')


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


def save_badge_image(badge_image_file):
    ext = badge_image_file.filename.rsplit('.', 1)[-1]
    filename = secure_filename(f"{uuid.uuid4()}.{ext}")
    # Specify the upload directory for badge images, which might be different from profile pictures
    uploads_path = os.path.join(current_app.root_path, 'static', 'badge_images')
    
    if not os.path.exists(uploads_path):
        os.makedirs(uploads_path)
    
    # Save the badge image file
    badge_image_file.save(os.path.join(uploads_path, filename))
    
    # Return the relative path to the badge image for storing in the database
    return os.path.join('badge_images', filename)


def save_submission_image(submission_image_file):
    ext = submission_image_file.filename.rsplit('.', 1)[-1]
    filename = secure_filename(f"{uuid.uuid4()}.{ext}")
    uploads_dir = os.path.join(current_app.static_folder, 'images', 'verifications')
    
    # Ensure the upload directory exists
    os.makedirs(uploads_dir, exist_ok=True)
    
    full_path = os.path.join(uploads_dir, filename)
    submission_image_file.save(full_path)
    return os.path.join('images', 'verifications', filename)
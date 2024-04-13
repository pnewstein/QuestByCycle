from flask import flash, current_app, jsonify
from .models import db, Task, Badge, UserTask, User, ShoutBoardMessage, Frequency, TaskSubmission
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
from sqlalchemy import and_, func, distinct


import uuid
import os

MAX_POINTS_INT = 2**63 - 1


def update_user_score(user_id):
    try:
        user = User.query.get(user_id)
        if not user:
            print(f"No user found with ID {user_id}")
            return False

        # Calculate the total points awarded to the user
        total_points = sum(task.points_awarded for task in user.user_tasks if task.points_awarded is not None)

        # Update user score, ensuring it doesn't exceed a predefined maximum
        user.score = min(total_points, MAX_POINTS_INT)

        # Commit changes to the database
        db.session.commit()
        print(f"Updated user score for user ID {user_id} to {user.score}")
        return True
    except Exception as e:
        db.session.rollback()  # Rollback in case of any exception
        print(f"Failed to update score for user ID {user_id}: {e}")
        return False


def award_badge(user_id):
    user = User.query.get(user_id)
    completed_tasks = UserTask.query.filter_by(user_id=user_id, completions=1).all()

    try:
        for user_task in completed_tasks:
            task = Task.query.get(user_task.task_id)
            if task.badge and task.badge not in user.badges:
                user.badges.append(task.badge)
                shout_message = ShoutBoardMessage(message=f"{current_user.username} has just earned the {task.badge.name} badge!", user_id=user_id)
                db.session.add(shout_message)
                db.session.commit()
                flash(f"Badge '{task.badge.name}' awarded for completing task '{task.title}'.")
    except Exception as e:
        db.session.rollback()  # Rollback in case of any exception
        print(f"Failed to update badge for user ID {user_id}: {e}")
        return False

def award_badges(user_id):
    user = User.query.get_or_404(user_id)
    try:
        for task in user.user_tasks:
            if task.completed and task.task.badge_id:  # Assuming task links to UserTask which links to Task
                badge = Badge.query.get(task.task.badge_id)
                if badge and badge not in user.badges:
                    user.badges.append(badge)
        db.session.commit()
        flash('Badges updated based on completed tasks.', 'success')
    except Exception as e:
        db.session.rollback()  # Rollback in case of any exception
        print(f"Failed to update badges for user ID {user_id}: {e}")
        return False


def revoke_badge(user_id):
    user = User.query.get(user_id)
    completed_tasks = UserTask.query.filter_by(user_id=user_id, completions=0).all()

    try:
        for user_task in completed_tasks:

            task = Task.query.get(user_task.task_id)
            if task.badge and task.badge in user.badges:
                user.badges.remove(task.badge)
                db.session.commit()
                flash(f"Badge '{task.badge.name}' revoked as the task '{task.title}' is no longer completed.", 'info')
    except Exception as e:
        db.session.rollback()  # Rollback in case of any exception
        print(f"Failed to revoke badge for user ID {user_id}: {e}")
        return False

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


def can_complete_task(user_id, task_id):
    now = datetime.now(timezone.utc)
    task = Task.query.get(task_id)
    
    if not task:
        print(f"No task found for Task ID: {task_id}")
        return False, None  # Task does not exist
    
    print(f"Current time: {now}")
    print(f"Task found: {task.title} with frequency {task.frequency.name} and completion limit {task.completion_limit}")

    # Determine the start of the relevant period based on frequency
    period_start_map = {
        'daily': timedelta(days=1),
        'weekly': timedelta(minutes=4),
        'monthly': timedelta(days=30)  # Approximation for monthly
    }
    period_start = now - period_start_map.get(task.frequency.name.lower(), timedelta(days=1))
    print(f"Period start calculated as: {period_start}")

    # Count completions in the defined period
    completions_within_period = TaskSubmission.query.filter(
        TaskSubmission.user_id == user_id,
        TaskSubmission.task_id == task_id,
        TaskSubmission.timestamp >= period_start
    ).count()

    print(f"Completions within period for user {user_id} on task {task_id}: {completions_within_period}")

    # Check if the user can verify the task again
    can_verify = completions_within_period < task.completion_limit
    next_eligible_time = None
    if not can_verify:
        first_completion_in_period = TaskSubmission.query.filter(
            TaskSubmission.user_id == user_id,
            TaskSubmission.task_id == task_id,
            TaskSubmission.timestamp >= period_start
        ).order_by(TaskSubmission.timestamp.asc()).first()

        if first_completion_in_period:
            print(f"First Completion in the period found at: {first_completion_in_period.timestamp}")
            # Calculate when the user is eligible next, based on the first completion time
            increment_map = {
                'daily': timedelta(days=1),
                'weekly': timedelta(minutes=4),
                'monthly': timedelta(days=30)
            }
            next_eligible_time = first_completion_in_period.timestamp + increment_map.get(task.frequency.name.lower(), timedelta(days=1))
            print(f"Next eligible time calculated as: {next_eligible_time}")
        else:
            print("No completions found within the period.")
    else:
        print("User can currently verify the task.")

    return can_verify, next_eligible_time

def getLastRelevantCompletionTime(user_id, task_id):
    now = datetime.now(timezone.utc)
    task = Task.query.get(task_id)
    
    if not task:
        return None  # Task does not exist

    # Start of the period calculation must reflect the frequency
    period_start = {
        Frequency.daily: now - timedelta(days=1),
        Frequency.weekly: now - timedelta(minutes=4),
        Frequency.monthly: now - timedelta(days=30)
    }.get(task.frequency, now)  # Default to immediate if frequency is not set

    # Fetch the last completion that affects the current period
    last_relevant_completion = TaskSubmission.query.filter(
        TaskSubmission.user_id == user_id,
        TaskSubmission.task_id == task_id,
        TaskSubmission.timestamp >= period_start
    ).order_by(TaskSubmission.timestamp.desc()).first()

    return last_relevant_completion.timestamp if last_relevant_completion else None

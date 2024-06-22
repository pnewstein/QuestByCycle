from flask import flash, current_app, jsonify
from .models import db, Task, Badge, UserTask, User, ShoutBoardMessage, TaskSubmission
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from flask_mail import Message, Mail
from PIL import Image


import uuid
import os

MAX_POINTS_INT = 2**63 - 1
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_leaderboard_image(image_file):
    if not hasattr(image_file, 'filename'):
        raise ValueError("Invalid file object passed.")
    
    try:
        ext = image_file.filename.rsplit('.', 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError("File extension not allowed.")
        filename = secure_filename(f"{uuid.uuid4()}.{ext}")
        rel_path = os.path.join('images', 'leaderboard', filename)
        abs_path = os.path.join(current_app.root_path, 'static', rel_path)

        leaderboard_images_dir = os.path.join(current_app.root_path, 'static/images/leaderboard')
        if not os.path.exists(leaderboard_images_dir):
            os.makedirs(leaderboard_images_dir)

        print(f"Saving file to {abs_path}")
        image_file.save(abs_path)
        print(f"File saved successfully to {abs_path}")
        return rel_path

    except Exception as e:
        print(f"Error saving leaderboard image: {e}")
        raise ValueError(f"Failed to save image: {str(e)}")

def create_smog_effect(image, smog_level):
    smog_overlay = Image.new('RGBA', image.size, (169, 169, 169, int(255 * smog_level)))
    smog_image = Image.alpha_composite(image.convert('RGBA'), smog_overlay)
    return smog_image

def generate_smoggy_images(image_path, game_id):
    try:
        original_image = Image.open(image_path)

        for i in range(10):
            smog_level = i / 9.0
            smoggy_image = create_smog_effect(original_image, smog_level)
            smoggy_image.save(os.path.join(current_app.root_path, f'static/images/leaderboard/smoggy_skyline_{game_id}_{i}.png'))
            print(f"Smoggy image saved: smoggy_skyline_{game_id}_{i}.png")
    except Exception as e:
        print(f"Error generating smoggy images: {e}")
        raise ValueError(f"Failed to generate smoggy images: {str(e)}")

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


def award_task_badge(user_id, task_id):
    user_task = UserTask.query.filter_by(user_id=user_id, task_id=task_id).first()
    if user_task and user_task.completions >= user_task.task.completion_limit:
        if user_task.task.badge and user_task.task.badge not in user_task.user.badges:
            user_task.user.badges.append(user_task.task.badge)
            db.session.commit()
            flash(f"Badge '{user_task.task.badge.name}' awarded for completing task '{user_task.task.title}' the required number of times.", 'success')


def award_category_badge(user_id):
    user = User.query.get(user_id)
    completed_categories = {ut.task.category for ut in user.user_tasks if ut.completions >= ut.task.completion_limit}
    
    for category in completed_categories:
        category_badges = Badge.query.filter_by(category=category).all()
        category_tasks = Task.query.filter_by(category=category).all()
        completed_tasks = {ut.task for ut in user.user_tasks if ut.completions >= ut.task.completion_limit and ut.task.category == category}
        
        for badge in category_badges:
            if badge not in user.badges and set(category_tasks) == completed_tasks:
                user.badges.append(badge)
                db.session.commit()
                flash(f"Badge '{badge.name}' awarded for completing all tasks in the '{category}' category.", 'success')


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


def save_profile_picture(profile_picture_file, old_filename=None):
    if old_filename:
        old_path = os.path.join(current_app.root_path, 'static', old_filename)
        if os.path.exists(old_path):
            os.remove(old_path)  # Remove the old file

    ext = profile_picture_file.filename.rsplit('.', 1)[-1]
    filename = secure_filename(f"{uuid.uuid4()}.{ext}")
    uploads_path = os.path.join(current_app.root_path, 'static', current_app.config['main']['UPLOAD_FOLDER'])
    if not os.path.exists(uploads_path):
        os.makedirs(uploads_path)
    profile_picture_file.save(os.path.join(uploads_path, filename))
    return os.path.join(current_app.config['main']['UPLOAD_FOLDER'], filename)


def save_badge_image(image_file):
    try:
        # Generate a secure filename
        filename = secure_filename(f"{uuid.uuid4()}.png")
        rel_path = os.path.join('images', 'badge_images', filename)  # No leading slashes
        abs_path = os.path.join(current_app.root_path, current_app.static_folder, rel_path)

        # Save the file
        image_file.save(abs_path)
        return filename  # Return the correct relative path from 'static' directory

    except Exception as e:
        print(f"Error saving badge image: {e}")
        raise ValueError(f"Failed to save image: {str(e)}")


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
    now = datetime.now()
    task = Task.query.get(task_id)
    
    if not task:
        print(f"No task found for Task ID: {task_id}")
        return False, None  # Task does not exist
    
    print(f"Current time: {now}")
    print(f"Task found: {task.title} with frequency {task.frequency} and completion limit {task.completion_limit}")

    # Determine the start of the relevant period based on frequency
    period_start_map = {
        'daily': timedelta(days=1),
        'weekly': timedelta(weeks=1),
        'monthly': timedelta(days=30)  # Approximation for monthly
    }
    period_start = now - period_start_map.get(task.frequency, timedelta(days=1))
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
                'weekly': timedelta(weeks=1),
                'monthly': timedelta(days=30)
            }
            next_eligible_time = first_completion_in_period.timestamp + increment_map.get(task.frequency, timedelta(days=1))
            print(f"Next eligible time calculated as: {next_eligible_time}")
        else:
            print("No completions found within the period.")
    else:
        print("User can currently verify the task.")

    return can_verify, next_eligible_time


def getLastRelevantCompletionTime(user_id, task_id):
    now = datetime.now()
    task = Task.query.get(task_id)
    
    if not task:
        return None  # Task does not exist

    # Start of the period calculation must reflect the frequency
    period_start_map = {
        'daily': now - timedelta(days=1),
        'weekly': now - timedelta(weeks=1),
        'monthly': now - timedelta(days=30)
    }
    
    # Get the period start time based on the task's frequency
    period_start = period_start_map.get(task.frequency, now)  # Default to now if frequency is not recognized


    # Fetch the last completion that affects the current period
    last_relevant_completion = TaskSubmission.query.filter(
        TaskSubmission.user_id == user_id,
        TaskSubmission.task_id == task_id,
        TaskSubmission.timestamp >= period_start
    ).order_by(TaskSubmission.timestamp.desc()).first()

    return last_relevant_completion.timestamp if last_relevant_completion else None


def check_and_award_badges(user_id, task_id):
    print(f"Checking and awarding badges for user_id={user_id}, task_id={task_id}")
    user = User.query.get(user_id)
    task = Task.query.get(task_id)
    user_task = UserTask.query.filter_by(user_id=user_id, task_id=task_id).first()

    if not user_task:
        print("No UserTask found.")
        return

    print(f"UserTask found: completions={user_task.completions}, task completion limit={task.completion_limit}")
    
    if user_task.completions >= task.completion_limit:
        print("Condition met for awarding badge based on task completion limit.")
        if task.badge and task.badge not in user.badges:
            user.badges.append(task.badge)
            db.session.add(ShoutBoardMessage(
                message=f" earned the badge '{task.badge.name}' for task <strong><a href='javascript:void(0);' onclick='openTaskDetailModal({task.id})'>{task.title}</a></strong>.",
                user_id=user_id
            ))
            db.session.commit()
            print(f"Badge '{task.badge.name}' awarded to user '{user.display_name}' for completing task '{task.title}'")
        else:
            print(f"No badge awarded: either no badge assigned for task or user already has the badge")
    else:
        print("Condition not met for awarding badge based on task completion limit.")

    if task.category and task.game_id:
        tasks_in_category = Task.query.filter_by(category=task.category, game_id=task.game_id).all()
        completed_tasks = {ut.task_id for ut in user.user_tasks.join(Task).filter(Task.category == task.category, Task.game_id == task.game_id) if ut.completions >= 1}

        category_task_ids = {t.id for t in tasks_in_category}
        print(f"Tasks in category '{task.category}' for game ID {task.game_id}: {category_task_ids}")
        print(f"Completed tasks in category by user for this game: {completed_tasks}")

        if category_task_ids == completed_tasks:
            print("Condition met for awarding badge based on category completion.")
            category_badges = Badge.query.filter_by(category=task.category).all()
            for badge in category_badges:
                if badge not in user.badges:
                    user.badges.append(badge)
                    db.session.add(ShoutBoardMessage(
                        message=f" earned the badge '{badge.name}' for completing all tasks in category '{task.category}' within game ID {task.game_id}.",
                        user_id=user_id
                    ))
                    db.session.commit()
                    print(f"Badge '{badge.name}' awarded for completing all tasks in category '{task.category}' within game ID {task.game_id}")
                else:
                    print(f"User already has badge '{badge.name}', not awarded again")
        else:
            print("Condition not met for awarding badge based on category completion.")

def check_and_revoke_badges(user_id):
    user = User.query.get(user_id)
    badges_to_remove = []

    for badge in user.badges:
        # Determine the logic to check if the badge should still be held
        # This depends heavily on how badge conditions are defined. Here's a generic example:

        # Check if all tasks required for the badge are still completed as required
        all_tasks_completed = True
        for task in badge.tasks:
            user_task = UserTask.query.filter_by(user_id=user_id, task_id=task.id).first()
            if not user_task or user_task.completions < task.completion_limit:
                all_tasks_completed = False
                break

        if not all_tasks_completed:
            badges_to_remove.append(badge)

    for badge in badges_to_remove:
        user.badges.remove(badge)
        print(f"Badge '{badge.name}' removed from user '{user.username}'")

    db.session.commit()


def send_email(to, subject, template):
    mail = Mail(current_app)
    
    msg = Message(
        subject,
        recipients=[to],
        html=template,
        sender=current_app.config['MAIL_DEFAULT_SENDER']
    )
    mail.send(msg)
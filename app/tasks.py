from flask import Blueprint, send_file, jsonify, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from app.utils import update_user_score, getLastRelevantCompletionTime, check_and_award_badges, revoke_badge, save_badge_image, save_submission_image, can_complete_task
from app.forms import TaskForm, PhotoForm
from .models import db, Game, Task, Badge, UserTask, TaskSubmission, Frequency, ShoutBoardMessage, VerificationType
from .utils import award_badges
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from datetime import datetime, timezone, timedelta

import pytz
import csv
import os
import qrcode

tasks_bp = Blueprint('tasks', __name__, template_folder='templates')


@tasks_bp.route('/<int:game_id>/manage_tasks', methods=['GET', 'POST'])
@login_required
def manage_game_tasks(game_id):
    game = Game.query.get_or_404(game_id)

    if not current_user.is_admin:
        flash('Access denied: Only administrators can manage tasks.', 'danger')
        return redirect(url_for('games.game_detail', game_id=game_id))
    
    form = TaskForm()

    if request.method == 'POST':
        # Process JSON data if content type is application/json
        if request.content_type == 'application/json':
            data = request.get_json()
            frequency_value = data.get('frequency')
        else:
            # For non-JSON requests, this block can be adapted to process form data or other data types
            frequency_value = None

        if form.validate_on_submit():
            task = Task(
                title=form.title.data,
                description=form.description.data,
                game_id=game_id
            )

            # If frequency value is provided and valid, set it here
            if frequency_value:
                try:
                    # Ensure frequency_value is an integer and valid enum before assignment
                    frequency_enum = Frequency(int(frequency_value))
                    task.frequency = frequency_enum
                except (ValueError, TypeError, KeyError):
                    # Handle invalid frequency values (e.g., not an integer, not a valid enum value)
                    flash('Invalid frequency value provided.', 'error')

            db.session.add(task)
            try:
                db.session.commit()
                flash('Task added successfully', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error adding task: {str(e)}', 'error')

            return redirect(url_for('tasks.manage_game_tasks', game_id=game_id))

    # Retrieve tasks each time the page is loaded or reloaded
    tasks = Task.query.filter_by(game_id=game_id).all()
    
    # Pass game_id to the template, alongside the game object, tasks, and form
    return render_template('manage_tasks.html', game=game, tasks=tasks, form=form, game_id=game_id)


@tasks_bp.route('/game/<int:game_id>/add_task', methods=['GET', 'POST'])
@login_required
def add_task(game_id):
    form = TaskForm()
    if form.validate_on_submit():
        badge_id = form.badge_id.data if form.badge_id.data and form.badge_id.data != '0' else None

        if not badge_id and form.badge_name.data:
            # Initialize badge_image_path as None to handle cases where no image is uploaded
            badge_image_path = None
            if 'badge_image_filename' in request.files:
                badge_image_file = request.files['badge_image_filename']
                # Ensure the file exists and has a filename (indicating a file was selected for upload)
                if badge_image_file and badge_image_file.filename != '':
                    badge_image_path = save_badge_image(badge_image_file)
                else:
                    flash('No badge image selected for upload.', 'error')
            
            # Create a new badge with or without an image based on the file upload
            new_badge = Badge(
                name=form.badge_name.data,
                description=form.badge_description.data,
                image=badge_image_path
            )
            db.session.add(new_badge)
            db.session.flush()  # Ensures new_badge gets an ID
            badge_id = new_badge.id

        # Proceed to create the task with or without a new badge
        new_task = Task(
            title=form.title.data,
            description=form.description.data,
            tips=form.tips.data,
            points=form.points.data,
            game_id=game_id,
            completion_limit=form.completion_limit.data,
            frequency=form.frequency.data,
            enabled=form.enabled.data,
            category=form.category.data,
            verification_type=form.verification_type.data,
            badge_id=badge_id
        )
        db.session.add(new_task)
        try:
            db.session.commit()
            flash('Task added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'error')

        return redirect(url_for('tasks.manage_game_tasks', game_id=game_id))

    return render_template('add_task.html', form=form, game_id=game_id)


@tasks_bp.route('/task/<int:task_id>/submit', methods=['POST'])
@login_required
def submit_task(task_id):
    task = Task.query.get_or_404(task_id)
    game = Game.query.get_or_404(task.game_id)
    now = datetime.now()
    game_start = game.start_date.replace(tzinfo=None)
    game_end = game.end_date.replace(tzinfo=None)

    # Check if current time is within the game's active period
    if not (game_start <= now <= game_end):
        return jsonify({'success': False, 'message': 'This task cannot be completed outside of the game dates'}), 403

    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'File part missing'})

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    try:
        image_url = save_submission_image(image_file)
        comment = request.form.get('verificationComment')

        new_submission = TaskSubmission(
            task_id=task_id,
            user_id=current_user.id,
            image_url=url_for('static', filename=image_url),
            comment=request.form.get('verificationComment', ''),
            timestamp=datetime.now(timezone.utc)  # Record the time of submission
        )
        db.session.add(new_submission)

        task = Task.query.get_or_404(task_id)
        user_task = UserTask.query.filter_by(user_id=current_user.id, task_id=task_id).first()

        if not user_task:
            print(f"No existing UserTask entry, creating new for task ID: {task_id}")

            user_task = UserTask(
                user_id=current_user.id,
                task_id=task_id,
                completions=0,
                points_awarded=0,
                completed_at=datetime.now(timezone.utc)
            )
            db.session.add(user_task)

        if user_task.completions is None:
            user_task.completions = 0
        if user_task.points_awarded is None:
            user_task.points_awarded = 0

        # Check against the task's completion limit before incrementing
        user_task.completions += 1
        user_task.points_awarded += task.points
        user_task.completed = True
        print(f"Task {task_id} completed {user_task.completions} times; Total points now {user_task.points_awarded}")

        db.session.commit()

        print("Submission processed, updating user score...")
        update_user_score(current_user.id)  # This function should recalculate and update the user's score
        check_and_award_badges(user_id=current_user.id, task_id=task_id)

        total_points = sum(ut.points_awarded for ut in UserTask.query.filter_by(user_id=current_user.id))
        print(f"Total points after update: {total_points}")

        return jsonify({
            'success': True,
            'new_completion_count': user_task.completions,
            'total_points': total_points,
            'image_url': image_url,
            'comment': comment
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@tasks_bp.route('/task/<int:task_id>/update', methods=['POST'])
@login_required
def update_task(task_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    task = Task.query.get_or_404(task_id)
    data = request.get_json()

    # Update task with new data
    task.title = data.get('title', task.title)
    task.description = data.get('description', task.description)
    task.tips = data.get('tips', task.tips)
    task.points = int(data.get('points', task.points))
    task.completion_limit = int(data.get('completion_limit', task.completion_limit))
    task.enabled = data.get('enabled', task.enabled)
    task.category = data.get('category', task.category)

    # Handling Frequency
    if 'frequency' in data:
        frequency_value = data['frequency'].lower()
        if frequency_value in Frequency.__members__:
            task.frequency = Frequency[frequency_value]

    # Handling Verification Type
    if 'verification_type' in data and data['verification_type'] in VerificationType.__members__:
        task.verification_type = VerificationType[data['verification_type']]
    
    # Handle badge_id conversion and validation
    badge_id = data.get('badge_id')
    if badge_id is not None:
        try:
            task.badge_id = int(badge_id)
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid badge ID'}), 400

    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Task updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
    

@tasks_bp.route('/task/<int:task_id>/delete', methods=['DELETE'])
@login_required
def delete_task(task_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    # Fetch the task to be deleted
    task_to_delete = Task.query.get_or_404(task_id)
    
    # Deleting the task. The cascade options in the relationship should handle deletion of related records.
    db.session.delete(task_to_delete)

    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Task deleted successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Failed to delete task {task_id}: {e}')
        return jsonify({'success': False, 'message': 'Failed to delete task'})


@tasks_bp.route('/game/<int:game_id>/tasks', methods=['GET'])
def get_tasks_for_game(game_id):
    tasks = Task.query.filter_by(game_id=game_id).all()
    tasks_data = [
        {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'tips': task.tips,
            'points': task.points,
            'completion_limit': task.completion_limit,
            'enabled': task.enabled,
            'verification_type': task.verification_type.name if task.verification_type else 'Not Applicable',
            'badge_name': task.badge.name if task.badge else 'None',
            'badge_description': task.badge.description if task.badge else '',
            'frequency': task.frequency.name if task.frequency else 'Not Set',  # Handling Frequency Enum
            'category': task.category if task.category else 'Not Set',  # Handling potentially undefined Category
        }
        for task in tasks
    ]
    return jsonify(tasks=tasks_data)

@tasks_bp.route('/game/<int:game_id>/import_tasks', methods=['POST'])
@login_required
def import_tasks(game_id):
    if 'tasks_csv' not in request.files:
        return jsonify(success=False, message="No file part"), 400
    
    file = request.files['tasks_csv']
    if file.filename == '':
        return jsonify(success=False, message="No selected file"), 400
    
    if file:
        # Ensure the target directory exists
        upload_dir = current_app.config['TASKCSV']
        os.makedirs(upload_dir, exist_ok=True)  # This will create the directory if it doesn't exist
        
        filepath = os.path.join(upload_dir, secure_filename(file.filename))
        file.save(filepath)

        imported_badges = []
        with open(filepath, mode='r', encoding='utf-8') as csv_file:
            tasks_data = csv.DictReader(csv_file)
            for task_info in tasks_data:
                badge = Badge.query.filter_by(name=task_info['badge_name']).first()
                if not badge:
                    badge = Badge(
                        name=task_info['badge_name'],
                        description=task_info['badge_description'],
                    )
                    db.session.add(badge)
                    db.session.flush()  # to get badge.id for new badges
                    imported_badges.append(badge.id)

                new_task = Task(
                    category=task_info['category'],
                    title=task_info['title'],
                    description=task_info['description'],
                    tips=task_info['tips'],
                    points=int(task_info['points'].replace(',', '')),  # Removing commas in numbers
                    completion_limit=int(task_info['completion_limit']),
                    verification_type=task_info['verification_type'],
                    badge_id=badge.id,
                    game_id=game_id
                )
                db.session.add(new_task)
            
            db.session.commit()
            os.remove(filepath)  # Clean up the uploaded file
        
        # Skip adding badge images for now.
        return jsonify(success=True, redirectUrl=url_for('tasks.manage_game_tasks', game_id=game_id))

    return jsonify(success=False, message="Invalid file"), 400


@tasks_bp.route('/task/<int:task_id>/submissions')
def get_task_submissions(task_id):
    submissions = TaskSubmission.query.filter_by(task_id=task_id).all()
    submissions_data = [{
        'image_url': submission.image_url,
        'comment': submission.comment,
        'user_id': submission.user_id
    } for submission in submissions]
    return jsonify(submissions_data)


@tasks_bp.route('/detail/<int:task_id>/user_completion')
@login_required
def task_user_completion(task_id):
    task = Task.query.get_or_404(task_id)
    user_task = UserTask.query.filter_by(user_id=current_user.id, task_id=task_id).first()
    can_verify, next_eligible_time = can_complete_task(current_user.id, task_id)
    last_relevant_completion_time = getLastRelevantCompletionTime(current_user.id, task_id)

    task_details = {
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'tips': task.tips,
        'points': task.points,
        'completion_limit': task.completion_limit,
        'frequency': task.frequency.name if task.frequency else 'Not Set', 
        'enabled': task.enabled,
        'verification_type': task.verification_type.name if task.verification_type else 'Not Applicable',
        'badge_name': task.badge.name if task.badge else 'None',
        'nextEligibleTime': next_eligible_time.isoformat() if next_eligible_time else None

    }

    user_completion_data = {
        'completions': user_task.completions if user_task else 0,
        'lastCompletionTimestamp': user_task.completed_at.isoformat() if user_task and user_task.completed_at else None
    }

    response_data = {
        'task': task_details,
        'userCompletion': user_completion_data,
        'canVerify': can_verify,
        'nextEligibleTime': next_eligible_time.isoformat() if next_eligible_time else None,
        'lastRelevantCompletionTime': last_relevant_completion_time.isoformat() if last_relevant_completion_time else None
    }

    return jsonify(response_data)


@tasks_bp.route('/get_last_relevant_completion_time/<int:task_id>/<int:user_id>')
@login_required
def get_last_relevant_completion_time(task_id, user_id):
    last_time = getLastRelevantCompletionTime(user_id, task_id)
    if last_time:
        return jsonify(success=True, lastRelevantCompletionTime=last_time.isoformat())
    else:
        return jsonify(success=False, message="No relevant completion found")


@tasks_bp.route('/generate_qr/<int:task_id>')
def generate_qr(task_id):
    url = url_for('tasks.submit_photo', task_id=task_id, _external=True)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Ensure the directory exists
    qr_code_dir = os.path.join(current_app.static_folder, 'qr_codes')
    if not os.path.exists(qr_code_dir):
        os.makedirs(qr_code_dir)

    file_path = os.path.join(qr_code_dir, f'qr_task_{task_id}.png')
    img.save(file_path)
    return send_file(file_path, mimetype='image/png')


@tasks_bp.route('/submit_photo/<int:task_id>', methods=['GET', 'POST'])
@login_required
def submit_photo(task_id):
    form = PhotoForm()
    task = Task.query.get_or_404(task_id)
    
    if request.method == 'POST':
        photo = request.files.get('photo')
        if photo:
            filename = secure_filename(photo.filename)
            image_url = save_submission_image(photo)  # Assuming this returns the path

            new_submission = TaskSubmission(
                user_id=current_user.id,
                task_id=task_id,
                image_url=url_for('static', filename=image_url),
                timestamp=datetime.now(timezone.utc)
            )
            db.session.add(new_submission)

            user_task = UserTask.query.filter_by(user_id=current_user.id, task_id=task_id).first()
            if not user_task:
                user_task = UserTask(
                    user_id=current_user.id,
                    task_id=task_id,
                    completions=1,
                    points_awarded=task.points
                )
                db.session.add(user_task)
            else:
                user_task.completions += 1
                user_task.points_awarded += task.points

            db.session.commit()

            update_user_score(current_user.id)  # Recalculate and update user score

            flash('Photo submitted successfully!', 'success')
            return redirect(url_for('games.game_detail', game_id=task.game_id))
        else:
            flash('No photo detected, please try again.', 'error')

    return render_template('submit_photo.html', form=form, task=task)


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@tasks_bp.errorhandler(RequestEntityTooLarge)
def handle_large_file_error(e):
    return "File too large", 413


@tasks_bp.route('/task/<int:task_id>/share')
def task_share(task_id):
    task = Task.query.get_or_404(task_id)
    submission = TaskSubmission.query.filter_by(task_id=task_id).order_by(TaskSubmission.timestamp.desc()).first()
    # Assuming `submission` has attributes like image_url and comment
    return render_template('task_share.html', task=task, submission=submission)


@tasks_bp.route('/get-image-url/<int:taskId>')
@login_required
def get_image_url(taskId):
    task = Task.query.get_or_404(taskId)
    # Assume the image URL is stored in a Task model attribute
    imageUrl = task.image_url if task.image_url else url_for('static', filename='default.jpg')
    return jsonify(success=True, imageUrl=imageUrl)
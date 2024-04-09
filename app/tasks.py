from flask import Blueprint, jsonify, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from app.utils import update_user_score, award_badge, revoke_badge, save_badge_image, save_submission_image
from app.forms import EventForm, TaskForm, TaskImportForm, TaskSubmissionForm
from .models import db, Task, Badge, UserTask, Event, VerificationType, TaskSubmission
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError

import csv
import os

tasks_bp = Blueprint('tasks', __name__, template_folder='templates')

@tasks_bp.route('/event/<int:event_id>/create_task', methods=['GET', 'POST'])
@login_required
def create_task(event_id):
    event = Event.query.get_or_404(event_id)
    form = TaskForm()
    if form.validate_on_submit():
        new_task = Task(
            title=form.title.data,
            description=form.description.data,
            points=form.points.data,
            tips=form.tips.data,
            completion_limit=form.completion_limit.data,
            event_id=event_id,
            # Assume badge handling is done separately or included in the form
        )
        db.session.add(new_task)
        db.session.commit()
        flash('Task created successfully.', 'success')
        return redirect(url_for('tasks.view_tasks', event_id=event_id))
    return render_template('create_task.html', form=form, event_id=event_id)


@tasks_bp.route('/event/<int:event_id>/add_task', methods=['GET', 'POST'])
@login_required
def add_task(event_id):
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
                image=badge_image_path  # Use the saved image path or None if no image was uploaded
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
            event_id=event_id,
            completion_limit=form.completion_limit.data,
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

        return redirect(url_for('events.manage_event_tasks', event_id=event_id))

    return render_template('add_task.html', form=form, event_id=event_id)


@tasks_bp.route('/adjust_completion/<int:task_id>/<action>', methods=['POST'])
@login_required
def adjust_task_completion(task_id, action):
    task = Task.query.get_or_404(task_id)
    user_task = UserTask.query.filter_by(user_id=current_user.id, task_id=task_id).first()
    disable_increment = False
    disable_decrement = False

    if action == "increment":
        # Check against the task's completion limit before incrementing
        if not user_task:
            if task.completion_limit > 0:  # Assuming a completion_limit of 0 means unlimited completions
                user_task = UserTask(
                    user_id=current_user.id, 
                    task_id=task.id, 
                    completions=1, 
                    points_awarded=task.points, 
                    completed=True
                )
                db.session.add(user_task)
        elif user_task.completions < task.completion_limit:
            user_task.completions += 1
            user_task.points_awarded += task.points
            user_task.completed = True
        disable_increment = user_task.completions >= task.completion_limit if user_task else False

    elif action == "decrement" and user_task and user_task.completions > 0:
        user_task.completions -= 1
        user_task.points_awarded = max(0, user_task.points_awarded - task.points)
        if user_task.completions == 0:
            user_task.completed = False
        disable_decrement = user_task.completions <= 0

    try:
        db.session.commit()
        update_user_score(current_user.id)
        if action == "increment":
            award_badge(current_user.id)
        if action == "decrement":
            revoke_badge(current_user.id)

        # Calculate the updated total points
        total_points = sum(ut.points_awarded for ut in UserTask.query.filter_by(user_id=current_user.id).all())

        return jsonify(success=True, new_completions_count=user_task.completions if user_task else 0, total_points=total_points, disable_increment=disable_increment, disable_decrement=disable_decrement)

    except IntegrityError as e:
        db.session.rollback()
        return jsonify(success=False, error=str(e))


@tasks_bp.route('/task/<int:task_id>/submit', methods=['POST'])
@login_required
def submit_task_detail(task_id):
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'File part missing'})
    
    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})

    # Generate unique filename and save the image
    relative_path = save_submission_image(image_file)
    
    # Save submission details
    new_submission = TaskSubmission(
        task_id=task_id,
        user_id=current_user.id,
        image_url=url_for('static', filename=relative_path),
        comment=request.form.get('comment', '')
    )
    db.session.add(new_submission)

    try:
        adjust_completion_result = adjust_task_completion_logic(task_id, "increment")
        if not adjust_completion_result['success']:
            raise Exception(adjust_completion_result['message'])
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Submission saved successfully and task completion incremented.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Failed to save submission or increment task completion: {str(e)}'})

def adjust_task_completion_logic(task_id, action):
    # This function is a simplified version of adjust_task_completion to be used internally
    # It mirrors the logic of the existing adjust_task_completion, without handling request/response directly
    try:
        task = Task.query.get_or_404(task_id)
        user_task = UserTask.query.filter_by(user_id=current_user.id, task_id=task_id).first()

        if action == "increment":
            if not user_task:
                user_task = UserTask(user_id=current_user.id, task_id=task.id, completions=1, points_awarded=task.points, completed=True)
                db.session.add(user_task)
            elif user_task.completions < task.completion_limit:
                user_task.completions += 1
                user_task.points_awarded += task.points
                user_task.completed = True
        
        return {'success': True, 'message': 'Completion adjusted successfully.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


@tasks_bp.route('/<int:event_id>/view_tasks')
@login_required
def view_tasks(event_id):
    event = Event.query.get_or_404(event_id)
    tasks = Task.query.filter_by(event_id=event.id).all()
    all_events = Event.query.all()  # Fetch all events to populate the dropdown
    return render_template('view_tasks.html', event=event, tasks=tasks, events=all_events)


@tasks_bp.route('/tasks/detail/<int:task_id>')
def task_detail(task_id):
    # Assuming Task model has a relationship to a Badge model
    task = Task.query.get_or_404(task_id)
    badge_name = task.badge.name if task.badge else 'None'
    
    total_completions = db.session.query(db.func.sum(UserTask.completions)).filter_by(task_id=task_id).scalar() or 0

    # Prepare the task data, including the badge name
    task_data = {
        'title': task.title,
        'description': task.description,
        'tips': task.tips or 'No tips available',
        'points': task.points,
        'completion_limit': task.completion_limit,
        'enabled': task.enabled,
        'verification_type': task.verification_type.name or 'Not Applicable',
        'badge_name': badge_name,
        'total_completions': total_completions,
    }
    return jsonify(task_data)


@tasks_bp.route('/task/<int:task_id>/edit', methods=['GET'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    # Assuming you return a JSON response with task details
    return jsonify({
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'points': task.points,
        'completion_limit': task.completion_limit,
        'tips': task.tips,
        'badge_id': task.badge_id
    })


@tasks_bp.route('/task/<int:task_id>/update', methods=['POST'])
@login_required
def update_task(task_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    task = Task.query.get_or_404(task_id)
    data = request.get_json()

    try:
        # Update direct task attributes
        task.title = data.get('title', task.title)
        task.description = data.get('description', task.description)
        task.tips = data.get('tips', task.tips)
        task.points = int(data.get('points', task.points))
        task.completion_limit = int(data.get('completion_limit', task.completion_limit))
        
        # Convert the 'enabled' field from string to boolean
        if 'enabled' in data:
            task.enabled = data['enabled'].lower() == 'true'  # Converts 'true' to True and 'false' to False
        
        # Handle 'verification_type' considering 'Not Applicable' as None or a special value
        if 'verification_type' in data and data['verification_type'] != 'NOT_APPLICABLE':
            task.verification_type = VerificationType[data['verification_type']]
        else:
            task.verification_type = None  # or a special enum value for 'Not Applicable'

        # Convert 'badge_id' from string to int, handling empty string as None
        badge_id = data.get('badge_id')
        if badge_id and badge_id.isdigit():
            task.badge_id = int(badge_id)
        else:
            task.badge_id = None  # Handles empty string and non-digit strings

        db.session.commit()
        return jsonify({'success': True, 'message': 'Task updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Failed to update task: {e}'})



@tasks_bp.route('/task/<int:task_id>/delete', methods=['DELETE'])
@login_required
def delete_task(task_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    # Fetch the task to be deleted
    task = Task.query.get_or_404(task_id)
    
    # Delete all UserTask records associated with this task first
    UserTask.query.filter_by(task_id=task_id).delete()

    # Now, it's safe to delete the task itself
    db.session.delete(task)

    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Task deleted successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Failed to delete task {task_id}: {e}')
        return jsonify({'success': False, 'message': 'Failed to delete task'})


@tasks_bp.route('/event/<int:event_id>/tasks', methods=['GET'])
def get_tasks_for_event(event_id):
    tasks = Task.query.filter_by(event_id=event_id).all()
    tasks_data = [
        {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'tips': task.tips,  # Ensure this field is included
            'points': task.points,
            'completion_limit': task.completion_limit,
            'enabled': task.enabled,
            'verification_type': task.verification_type.value if task.verification_type else None,  # Handle Enum, if applicable
            'badge_name': task.badge.name if task.badge else '',
            'badge_description': task.badge.description if task.badge else '',
            # Additional fields can be added here as necessary
        }
        for task in tasks
    ]
    
    return jsonify(tasks=tasks_data)

@tasks_bp.route('/event/<int:event_id>/import_tasks', methods=['POST'])
@login_required
def import_tasks(event_id):
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
                    event_id=event_id
                )
                db.session.add(new_task)
            
            db.session.commit()
            os.remove(filepath)  # Clean up the uploaded file
        
        # Skip adding badge images for now.
        return jsonify(success=True, redirectUrl=url_for('events.manage_event_tasks', event_id=event_id))


    return jsonify(success=False, message="Invalid file"), 400


@tasks_bp.route('/event/<int:event_id>/upload_badge_images', methods=['GET', 'POST'])
@login_required
def upload_badge_images(event_id):
    badge_ids = request.args.get('badge_ids', '')
    if request.method == 'POST':
        for badge_id in badge_ids.split(','):
            file = request.files.get(f'badge_image_{badge_id}', None)
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(current_app.config['TASKCSV'], filename)
                file.save(filepath)
                
                badge = Badge.query.get(badge_id)
                if badge:
                    badge.image = filepath
                    db.session.commit()

        flash('Badge images updated successfully', 'success')
        return redirect(url_for('tasks.view_tasks', event_id=event_id))
    
    badge_ids = [int(id_) for id_ in badge_ids.split(',') if id_.isdigit()]
    badges = Badge.query.filter(Badge.id.in_(badge_ids)).all()
    return render_template('upload_badge_images.html', badges=badges, event_id=event_id)


@tasks_bp.route('/task/<int:task_id>/submissions')
def get_task_submissions(task_id):
    submissions = TaskSubmission.query.filter_by(task_id=task_id).all()
    submissions_data = [{
        'image_url': submission.image_url,
        'comment': submission.comment,
    } for submission in submissions]
    return jsonify(submissions_data)

from flask import Blueprint, jsonify, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from app.utils import update_user_score, award_badge, revoke_badge, save_badge_image
from app.forms import EventForm, TaskForm, TaskImportForm, TaskSubmissionForm
from .models import db, Task, Badge, UserTask, Event, VerificationType
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError

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


@tasks_bp.route('/import_tasks', methods=['GET', 'POST'])
@login_required
def import_tasks():
    form = TaskImportForm()
    if form.validate_on_submit():
        # Implement CSV import logic
        flash('Tasks imported successfully!', 'success')
        return redirect(url_for('tasks.view_tasks'))
    return render_template('import_tasks.html', form=form)


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



@tasks_bp.route('/submit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def submit_task(task_id):
    task = Task.query.get_or_404(task_id)
    form = TaskSubmissionForm()

    if form.validate_on_submit():
        filename = secure_filename(form.evidence.data.filename)
        filepath = os.path.join('uploads', filename)
        form.evidence.data.save(os.path.join(current_app.root_path, 'static', filepath))

        task.evidence_url = filepath
        db.session.commit()

        flash('Task submitted successfully!', 'success')
        return redirect(url_for('events.event_detail', event_id=task.event_id))

    return render_template('submit_task.html', form=form, task_id=task_id)


@tasks_bp.route('/<int:event_id>/view_tasks')
@login_required
def view_tasks(event_id):
    event = Event.query.get_or_404(event_id)
    tasks = Task.query.filter_by(event_id=event.id).all()
    all_events = Event.query.all()  # Fetch all events to populate the dropdown
    return render_template('view_tasks.html', event=event, tasks=tasks, events=all_events)


@tasks_bp.route('/tasks/<int:task_id>', methods=['GET'])
@login_required
def task_detail(task_id):
    task = Task.query.get_or_404(task_id)
    return render_template('task_detail.html', task=task)


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


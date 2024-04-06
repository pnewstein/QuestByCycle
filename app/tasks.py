from flask import Blueprint, jsonify, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from app.utils import update_user_score, award_badge, revoke_badge, save_profile_picture
from app.forms import EventForm, TaskForm, AdvancedTaskForm, TaskImportForm, TaskSubmissionForm
from .models import db, Task, Badge, UserTask, Event
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError

import os

tasks_bp = Blueprint('tasks', __name__, template_folder='templates')

@tasks_bp.route('/create_task', methods=['GET', 'POST'])
@login_required
def create_task():
    form = AdvancedTaskForm()
    if form.validate_on_submit():
        # Implement task creation logic, possibly including linking to badges
        flash('Task created successfully!', 'success')
        return redirect(url_for('tasks_bp.view_tasks'))
    return render_template('create_task.html', form=form)


@tasks_bp.route('/import_tasks', methods=['GET', 'POST'])
@login_required
def import_tasks():
    form = TaskImportForm()
    if form.validate_on_submit():
        # Implement CSV import logic
        flash('Tasks imported successfully!', 'success')
        return redirect(url_for('tasks_bp.view_tasks'))
    return render_template('import_tasks.html', form=form)


# For global task management, you might not need 'event_id'
@tasks_bp.route('/manage_tasks', methods=['GET', 'POST'])
@login_required
def manage_global_tasks():
    tasks = Task.query.filter_by(verified=False).all()
    # If you're using a form here, initialize it
    form = TaskForm()  # Assuming this is needed globally as well
    return render_template('manage_tasks.html', tasks=tasks, form=form, event_id=None)



@tasks_bp.route('/event/<int:event_id>/add_task', methods=['GET', 'POST'])
@login_required
def add_task(event_id):
    form = TaskForm()
    if form.validate_on_submit():
        new_badge = None
        badge_image_path = ''

        if form.default_badge_image.data and form.default_badge_image.data != 'None':
            # Case 2: Default badge image selected
            badge_image_path = os.path.join('images/default_badges', form.default_badge_image.data)
        elif 'badge_image_filename' in request.files and request.files['badge_image_filename'].filename != '':
            # Case: New badge image uploaded
            badge_image_file = request.files['badge_image_filename']
            # Use save_profile_picture function to save the badge image
            badge_image_path = save_profile_picture(badge_image_file)
            # Now badge_image_path contains the path relative to the static folder
            
        if badge_image_path:
            # Only create a badge if an image is selected or uploaded
            new_badge = Badge(name=form.badge_name.data, description=form.badge_description.data, image=badge_image_path)
            db.session.add(new_badge)
            db.session.flush()  # Ensures new_badge gets an ID

        task = Task(
            title=form.title.data,
            description=form.description.data,
            points=form.points.data,
            event_id=event_id,
            completion_limit=form.completion_limit.data,
            badge_id=new_badge.id if new_badge else None
        )
        db.session.add(task)
        try:

            db.session.commit()
            flash('Task added successfully!', 'success')
            return redirect(url_for('main.index'))  # Adjust as needed
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'error')

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


# Rename the function to avoid conflict and more accurately represent its purpose
@tasks_bp.route('/event/<int:event_id>/manage_tasks', methods=['GET', 'POST'])
@login_required
def manage_event_tasks(event_id):
    event = Event.query.get_or_404(event_id)

    if not current_user.is_admin:
        flash('Access denied: Only administrators can manage tasks.', 'danger')
        return redirect(url_for('events.event_detail', event_id=event_id))
    
    tasks = Task.query.filter_by(event_id=event_id, verified=False).all()
    form = TaskForm()

    if request.method == 'POST':
        if form.validate_on_submit():
            task = Task(
                title=form.title.data,
                description=form.description.data,
                event_id=event_id
            )
            db.session.add(task)
            db.session.commit()
            flash('Task added successfully', 'success')
            return redirect(url_for('tasks.manage_event_tasks', event_id=event_id))
    tasks = Task.query.filter_by(event_id=event_id).all()
    # Make sure to pass 'event_id' to the template
    return render_template('manage_tasks.html', event=event, tasks=tasks, form=form, event_id=event_id)


@tasks_bp.route('/event/<int:event_id>/view_tasks')
@login_required
def view_tasks(event_id):
    event = Event.query.get_or_404(event_id)
    tasks = Task.query.filter_by(event_id=event.id).all()
    all_events = Event.query.all()  # Fetch all events to populate the dropdown
    return render_template('view_tasks.html', event=event, tasks=tasks, events=all_events)

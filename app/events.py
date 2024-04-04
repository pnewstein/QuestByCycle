from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from flask_wtf.csrf import generate_csrf
from app.main import save_profile_picture
from app.models import db, User, Event, Task, Badge, UserTask, ShoutBoardMessage
from app.forms import EventForm, TaskForm, TaskSubmissionForm
from werkzeug.utils import secure_filename
from sqlalchemy import select, update, insert, exists, func
from sqlalchemy.exc import IntegrityError

import os

MAX_POINTS_INT = 2**63 - 1

events_bp = Blueprint('events', __name__)

@events_bp.route('/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    form = EventForm()
    if form.validate_on_submit():
        event = Event(
            title=form.title.data,
            description=form.description.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            admin_id=current_user.id
        )
        db.session.add(event)
        try:
            db.session.commit()
            flash('Event created successfully!', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while creating the event: {e}', 'error')
    return render_template('create_event.html', title='Create Event', form=form)


@events_bp.route('/event/<int:event_id>/add_task', methods=['GET', 'POST'])
@login_required
def add_task(event_id):
    form = TaskForm()
    if form.validate_on_submit():
        badge_id = None
        if form.badge_name.data and 'badge_image' in request.files:
            badge_image_file = request.files['badge_image']
            filename = secure_filename(badge_image_file.filename)
            badge_image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            badge_image_file.save(badge_image_path)

            new_badge = Badge(name=form.badge_name.data, description=form.new_badge_description.data, image=filename)
            db.session.add(new_badge)
            db.session.commit()
            badge_id = new_badge.id
        
        task = Task(
            title=form.title.data,
            description=form.description.data,
            points=form.points.data,
            event_id=event_id,
            completion_limit=form.completion_limit.data,
            badge_id=badge_id  # This will be None if no new badge was created
        )
        db.session.add(task)
        db.session.commit()
        flash('Task and optionally a new badge added successfully!', 'success')
        return redirect(url_for('main.index'))  # Redirect as appropriate
    return render_template('add_task.html', form=form, event_id=event_id)


@events_bp.route('/event_detail/<int:event_id>')
@login_required
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)

    # Check if the user has joined the event
    has_joined = event in current_user.participated_events

    # Fetch tasks for this event; this includes all tasks, not just those completed
    tasks = Task.query.filter_by(event_id=event_id).all()

    # For each task, determine if the current user has any completion record
    user_tasks = UserTask.query.join(Task, UserTask.task_id == Task.id).filter(
        UserTask.user_id == current_user.id,
        Task.event_id == event_id
    ).all()

    total_points = sum(ut.points_awarded for ut in user_tasks)

    # Map task IDs to user task records for easy access in the template
    user_tasks_map = {user_task.task_id: user_task for user_task in user_tasks}

    # Calculate total points and completed tasks count if the user has joined
    completed_tasks_count = sum(1 for user_task in user_tasks if user_task.completed)

    csrf_token = generate_csrf()
    return render_template(
        'event_detail.html', 
        event=event, 
        has_joined=has_joined, 
        csrf_token=csrf_token, 
        tasks=tasks, 
        user_tasks_map=user_tasks_map,
        total_points=total_points, 
        completed_tasks_count=completed_tasks_count
    )


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



def revoke_badge(user_id):
    user = User.query.get(user_id)

    completed_tasks = UserTask.query.filter_by(user_id=user_id, completions=0).all()
    for user_task in completed_tasks:

        task = Task.query.get(user_task.task_id)
        if task.badge and task.badge in user.badges:
            user.badges.remove(task.badge)
            db.session.commit()
            flash(f"Badge '{task.badge.name}' revoked as the task '{task.title}' is no longer completed.", 'info')


@events_bp.route('/events/adjust_completion/<int:task_id>/<action>', methods=['POST'])
@login_required
def adjust_task_completion(task_id, action):
    task = Task.query.get_or_404(task_id)
    user_task = UserTask.query.filter_by(user_id=current_user.id, task_id=task.id).first()

    if action == "increment":
        if not user_task:
            user_task = UserTask(
                user_id=current_user.id, 
                task_id=task.id, 
                completions=1, 
                points_awarded=task.points, 
                completed=True
            )
            db.session.add(user_task)
        else:
            user_task.completions += 1
            user_task.points_awarded += task.points
            user_task.completed = True

    elif action == "decrement" and user_task and user_task.completions > 0:
        user_task.completions -= 1
        user_task.points_awarded = max(0, user_task.points_awarded - task.points)
        if user_task.completions == 0:
            user_task.completed = False

    try:
        db.session.commit()
        update_user_score(current_user.id)
        if action == "increment":
            award_badge(current_user.id)
        if action == "decrement":
            revoke_badge(current_user.id)
        flash(f"Task completion successfully {action}ed.", 'success')
    except IntegrityError as e:
        db.session.rollback()
        flash(f"Error updating task completion: {e}", 'error')

    return redirect(url_for('events.event_detail', event_id=task.event_id))


@events_bp.route('/register_event/<int:event_id>', methods=['POST'])
@login_required
def register_event(event_id):
    try:
        event = Event.query.get_or_404(event_id)
        if event not in current_user.participated_events:
            current_user.participated_events.append(event)
            db.session.commit()
            flash('You have successfully joined the event.', 'success')
        else:
            flash('You are already registered for this event.', 'info')
        return redirect(url_for('events.event_detail', event_id=event_id))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Failed to register user for event {event_id}: {e}')
        flash('An error occurred. Please try again.', 'error')
    return redirect(url_for('events.event_detail', event_id=event_id))


@events_bp.route('/submit_task/<int:task_id>', methods=['GET', 'POST'])
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


@events_bp.route('/verify_task/<int:task_id>')
@login_required
def verify_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.verified = True
    db.session.commit()
    # Trigger badge awarding logic
    award_badge(task.user_id)
    flash('Task verified.', 'success')
    return redirect(url_for('events.verify_tasks'))


# Rename the function to avoid conflict and more accurately represent its purpose
@events_bp.route('/event/<int:event_id>/manage_tasks', methods=['GET', 'POST'])
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
            return redirect(url_for('events.manage_event_tasks', event_id=event_id))
    tasks = Task.query.filter_by(event_id=event_id).all()
    # Make sure to pass 'event_id' to the template
    return render_template('manage_tasks.html', event=event, tasks=tasks, form=form, event_id=event_id)


# For global task management, you might not need 'event_id'
@events_bp.route('/manage_tasks', methods=['GET', 'POST'])
@login_required
def manage_global_tasks():
    tasks = Task.query.filter_by(verified=False).all()
    # If you're using a form here, initialize it
    form = TaskForm()  # Assuming this is needed globally as well
    return render_template('manage_tasks.html', tasks=tasks, form=form, event_id=None)


@events_bp.route('/event/<int:event_id>/view_tasks')
@login_required
def view_tasks(event_id):
    event = Event.query.get_or_404(event_id)
    tasks = Task.query.filter_by(event_id=event.id).all()
    all_events = Event.query.all()  # Fetch all events to populate the dropdown
    return render_template('view_tasks.html', event=event, tasks=tasks, events=all_events)

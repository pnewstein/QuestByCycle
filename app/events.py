from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.main import save_profile_picture
from app.models import db, User, Event, Task, Badge, UserTask, ShoutBoardMessage
from app.tasks import adjust_task_completion
from app.forms import EventForm, TaskForm, TaskSubmissionForm
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError

import os


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



@events_bp.route('/event_detail/<int:event_id>')
@login_required
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)

    # Check if the user has joined the event
    has_joined = event in current_user.participated_events

    # Fetch tasks for this event; this includes all tasks, not just those completed
    tasks = Task.query.filter_by(event_id=event_id, enabled=True).all()

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

    return render_template(
        'event_detail.html', 
        event=event, 
        has_joined=has_joined, 
        tasks=tasks, 
        user_tasks_map=user_tasks_map,
        total_points=total_points, 
        completed_tasks_count=completed_tasks_count
    )


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


@events_bp.route('/<int:event_id>/manage_tasks', methods=['GET', 'POST'])
@login_required
def manage_event_tasks(event_id):
    event = Event.query.get_or_404(event_id)

    if not current_user.is_admin:
        flash('Access denied: Only administrators can manage tasks.', 'danger')
        return redirect(url_for('events.event_detail', event_id=event_id))
    
    tasks = Task.query.filter_by(event_id=event_id).all()
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


@events_bp.route('/event/<int:event_id>/view_tasks')
@login_required
def view_tasks(event_id):
    event = Event.query.get_or_404(event_id)
    tasks = Task.query.filter_by(event_id=event.id).all()
    all_events = Event.query.all()  # Fetch all events to populate the dropdown
    return render_template('view_tasks.html', event=event, tasks=tasks, events=all_events)

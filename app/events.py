from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models import db, Event, Task, UserTask, TaskSubmission
from app.forms import EventForm, TaskForm, TaskSubmissionForm
from app.utils import can_complete_task
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone

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
            admin_id=current_user.id,
            event_goal=form.event_goal.data  # Make sure to handle the event_goal
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


@events_bp.route('/update_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def update_event(event_id):
    event = Event.query.get_or_404(event_id)
    form = EventForm(obj=event)
    if form.validate_on_submit():
        event.title = form.title.data
        event.description = form.description.data
        event.start_date = form.start_date.data
        event.end_date = form.end_date.data
        event.event_goal = form.event_goal.data
        db.session.commit()
        flash('Event updated successfully!', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('update_event.html', form=form, event_id=event_id)


@events_bp.route('/event_detail/<int:event_id>')
@login_required
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    has_joined = event in current_user.participated_events
    tasks = Task.query.filter_by(event_id=event_id, enabled=True).all()

    user_tasks = UserTask.query.filter_by(user_id=current_user.id).all()
    total_points = sum(ut.points_awarded for ut in user_tasks if ut.task.event_id == event_id)

    for task in tasks:
        task.completions_within_period = 0
        task.can_verify = False
        task.last_completion = None
        task.first_completion_in_period = None
        task.next_eligible_time = None
        task.completion_timestamps = []

        now = datetime.now(timezone.utc)
        period_start_map = {
            'daily': timedelta(days=1),
            'weekly': timedelta(minutes=4),
            'monthly': timedelta(days=30)
        }
        period_start = now - period_start_map.get(task.frequency.name.lower(), timedelta(days=1))

        submissions = TaskSubmission.query.filter(
            TaskSubmission.user_id == current_user.id,
            TaskSubmission.task_id == task.id,
            TaskSubmission.timestamp >= period_start
        ).all()

        if submissions:
            task.completions_within_period = len(submissions)
            task.first_completion_in_period = min(submissions, key=lambda x: x.timestamp).timestamp
            task.completion_timestamps = [sub.timestamp for sub in submissions]

        relevant_user_tasks = [ut for ut in user_tasks if ut.task_id == task.id]
        task.total_completions = len(relevant_user_tasks)
        task.last_completion = max((ut.completed_at for ut in relevant_user_tasks), default=None)

        if task.total_completions < task.completion_limit:
            task.can_verify = True
        else:
            last_completion = max(submissions, key=lambda x: x.timestamp, default=None)
            if last_completion:
                increment_map = {
                    'daily': timedelta(days=1),
                    'weekly': timedelta(minutes=4),
                    'monthly': timedelta(days=30)
                }
                task.next_eligible_time = last_completion.timestamp + increment_map.get(task.frequency.name.lower(), timedelta(days=1))

    return render_template(
        'event_detail.html',
        event=event,
        has_joined=has_joined,
        tasks=tasks,
        total_points=total_points
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


@events_bp.route('/delete_event/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    if not current_user.is_admin:
        flash('Access denied: Only administrators can delete events.', 'danger')
        return redirect(url_for('main.index'))

    event = Event.query.get_or_404(event_id)
    try:
        # Optional: Delete related data (e.g., tasks) if necessary
        for task in event.tasks:
            db.session.delete(task)
        
        db.session.delete(event)
        db.session.commit()
        flash('Event deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the event: {e}', 'error')
    
    return redirect(url_for('admin.admin_dashboard'))


@events_bp.route('/get_event_points/<int:event_id>', methods=['GET'])
@login_required
def get_event_points(event_id):
    # Query to get the total points awarded for a specific event
    total_event_points = db.session.query(
        db.func.sum(UserTask.points_awarded)
    ).join(Task, UserTask.task_id == Task.id
    ).filter(Task.event_id == event_id
    ).scalar() or 0

    # Query to get the goal for the specific event
    event = Event.query.get(event_id)
    event_goal = event.event_goal  # Assumes that `event_goal` is a column in your Event model

    return jsonify(total_event_points=total_event_points, event_goal=event_goal)
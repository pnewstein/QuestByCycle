from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from flask_wtf.csrf import generate_csrf
from app.models import db, User, Event, Task, Badge, user_tasks, user_badges, user_events, event_participants
from app.forms import EventForm, TaskForm, TaskSubmissionForm
from werkzeug.utils import secure_filename
from sqlalchemy import select, update, insert

import os


events_bp = Blueprint('events', __name__)

@events_bp.route('/events')
@login_required
def events():
    # Fetch all events and user's events
    all_events = Event.query.all()
    user_registered_events = current_user.events
    return render_template('events.html', all_events=all_events, user_registered_events=user_registered_events)


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


@events_bp.route('/view_events', methods=['GET'])
@login_required
def view_events():
    events = Event.query.all()
    return render_template('view_events.html', events=events)


@events_bp.route('/event/<int:event_id>/add_task', methods=['GET', 'POST'])
@login_required
def add_task(event_id):
    form = TaskForm()
    if form.validate_on_submit():
        print(form.points.data) 
        task = Task(title=form.title.data, description=form.description.data, points=form.points.data, event_id=event_id)
        db.session.add(task)
        db.session.commit()
        flash('Task added successfully', 'success')
        return redirect(url_for('events.event_detail', event_id=event_id))
    return render_template('add_task.html', form=form, event_id=event_id)


@events_bp.route('/event_detail/<int:event_id>')
@login_required
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    has_joined = event in current_user.participated_events
    # Assuming each task has points and you want to sum points of completed tasks for the current user
    total_points = db.session.query(db.func.sum(user_tasks.c.points_awarded)).filter(user_tasks.c.user_id == current_user.id, user_tasks.c.completed == True).scalar()
    completed_tasks_count = Task.query.filter_by(user_id=current_user.id, completed=True).count()
    
    csrf_token = generate_csrf()
    
    return render_template('event_detail.html', event=event, has_joined=has_joined, csrf_token=csrf_token, total_points=total_points, completed_tasks_count=completed_tasks_count)


@events_bp.route('/register_event/<int:event_id>', methods=['POST'])
@login_required
def register_event(event_id):
    event = Event.query.get_or_404(event_id)
    if event not in current_user.participated_events:
        current_user.participated_events.append(event)
        db.session.commit()
        flash('You have successfully joined the event.', 'success')
    else:
        flash('You are already registered for this event.', 'info')
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


@events_bp.route('/view_badges')
@login_required
def view_badges():
    user_badges = Badge.query.join(user_badges).join(User).filter(User.id == current_user.id)
    return render_template('badges.html', badges=user_badges)

@events_bp.route('/verify_tasks')
@login_required
def verify_tasks():
    tasks = Task.query.filter_by(verified=False).all()
    return render_template('verify_tasks.html', tasks=tasks)

@events_bp.route('/verify_task/<int:task_id>')
@login_required
def verify_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.verified = True
    db.session.commit()
    # Trigger badge awarding logic
    award_badges(task.user_id)
    flash('Task verified.', 'success')
    return redirect(url_for('events.verify_tasks'))

def award_badges(user_id):
    user = User.query.get(user_id)
    completed_tasks = Task.query.filter_by(user_id=user_id, verified=True).count()
    
    # Example badge logic
    if completed_tasks >= 5:
        badge = Badge.query.filter_by(name='Active Participant').first()
        if badge not in user.badges:
            user.badges.append(badge)
            db.session.commit()
            flash('Congratulations! You have earned a badge for active participation.', 'success')


# Rename the function to avoid conflict and more accurately represent its purpose
@events_bp.route('/event/<int:event_id>/manage_tasks', methods=['GET', 'POST'])
@login_required
def manage_event_tasks(event_id):
    event = Event.query.get_or_404(event_id)
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


@events_bp.route('/complete_task/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    # Query for an existing association between this user and task
    user_task_record = db.session.query(user_tasks).filter(user_tasks.c.user_id == current_user.id, user_tasks.c.task_id == task.id).first()
    
    if user_task_record:
        # Toggle the completion status
        new_status = not user_task_record.completed
        db.session.execute(
            update(user_tasks).
            where(user_tasks.c.user_id == current_user.id, user_tasks.c.task_id == task.id).
            values(completed=new_status)
        )
    else:
        # Insert a new record if it doesn't exist
        new_status = True
        db.session.execute(
            insert(user_tasks).
            values(user_id=current_user.id, task_id=task.id, completed=True, points_awarded=task.points)
        )
    
    # Recalculate the user's total score based on completed tasks
    total_points = db.session.query(db.func.sum(user_tasks.c.points_awarded)).filter(user_tasks.c.user_id == current_user.id, user_tasks.c.completed == True).scalar() or 0
    current_user.score = total_points
    db.session.commit()

    if new_status:
        flash('Task marked as completed. Total points updated.', 'success')
    else:
        flash('Task marked as not completed. Total points updated.', 'info')

    return redirect(url_for('events.event_detail', event_id=task.event_id))

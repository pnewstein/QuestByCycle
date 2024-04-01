from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from flask_wtf.csrf import generate_csrf
from app.models import db, User, Event, Task, Badge, UserTask
from app.forms import EventForm, TaskForm, TaskSubmissionForm
from werkzeug.utils import secure_filename
from sqlalchemy import select, update, insert, exists, func
from sqlalchemy.exc import IntegrityError


import os

MAX_SQLITE_INT = 2**63 - 1

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

    if not current_user.is_admin:
        flash('Access denied: Only administrators can add tasks.', 'danger')
        return redirect(url_for('events.event_detail', event_id=event_id))
    
    if form.validate_on_submit():
        # Ensure points data is valid and within limits before creating a task
        points = min(form.points.data, MAX_SQLITE_INT)
        task = Task(
            title=form.title.data,
            description=form.description.data,
            points=points,
            event_id=event_id,
            tips=form.tips.data,
            completion_limit=form.completion_limit.data
        )
        db.session.add(task)
        db.session.commit()
        flash('Task added successfully', 'success')
        return redirect(url_for('events.event_detail', event_id=event_id))
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
    MAX_SQLITE_INT = 2**63 - 1

    # Calculate total points with overflow check
    total_points = 0
    user_tasks = UserTask.query.filter_by(user_id=user_id).all()
    for task in user_tasks:
        total_points += task.points_awarded
        if total_points > MAX_SQLITE_INT:
            total_points = MAX_SQLITE_INT
            break  # Cap the total points to prevent overflow

    user.score = total_points

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Log the error or notify someone as needed
        print(f"Failed to update user score due to error: {e}")


@events_bp.route('/adjust_completion/<int:task_id>/<action>', methods=['POST'])
@login_required
def adjust_completion(task_id, action):
    task = Task.query.get_or_404(task_id)
    user_task = UserTask.query.filter_by(user_id=current_user.id, task_id=task_id).first()
    MAX_SQLITE_INT = 2**63 - 1  # Define SQLite's max int limit

    if not user_task:
        user_task = UserTask(
            user_id=current_user.id, 
            task_id=task_id, 
            completions=0, 
            points_awarded=0  # Ensure this field is initialized
        )
        db.session.add(user_task)
    else:
        # Ensure points_awarded is not None before incrementing or decrementing
        user_task.points_awarded = user_task.points_awarded or 0

    if action == 'increment' and user_task.completions < task.completion_limit:
        user_task.completions += 1
        # Prevent points_awarded from exceeding SQLite's maximum integer limit
        projected_points = user_task.points_awarded + task.points
        if projected_points > MAX_SQLITE_INT:
            user_task.points_awarded = MAX_SQLITE_INT
            flash('Maximum points limit reached.', 'warning')
        else:
            user_task.points_awarded = projected_points
    elif action == 'decrement' and user_task.completions > 0:
        user_task.completions -= 1
        user_task.points_awarded = max(0, user_task.points_awarded - task.points)  # Prevent negative values

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash('An error occurred. Please try again.', 'error')
        current_app.logger.error(f'Error during adjust_completion: {str(e)}')
    else:
        update_user_score(current_user.id)
        
    return redirect(url_for('events.event_detail', event_id=task.event_id))


@events_bp.route('/events/adjust_completion/<int:task_id>/increment', methods=['POST'])
@login_required
def increment_completion(task_id):
    task = Task.query.get_or_404(task_id)
    user_task = UserTask.query.filter_by(user_id=current_user.id, task_id=task_id).first()

    if user_task:
        projected_points = user_task.points_awarded + task.points
        if projected_points >= MAX_SQLITE_INT:
            flash('Maximum points limit reached.', 'error')
        elif user_task.completions < task.completion_limit:
            try:
                user_task.completions += 1
                user_task.points_awarded = min(projected_points, MAX_SQLITE_INT)
                db.session.commit()
                flash('Task completion incremented.', 'success')
            except IntegrityError:
                db.session.rollback()
                flash('Database error occurred.', 'error')
    else:
        flash('User task does not exist.', 'error')
    
    return redirect(url_for('events.event_detail', event_id=task.event_id))


@events_bp.route('/events/adjust_completion/<int:task_id>/decrement', methods=['POST'])
@login_required
def decrement_completion(task_id):
    user_task = UserTask.query.filter_by(user_id=current_user.id, task_id=task_id).first()
    if not user_task or user_task.completions <= 0:
        flash("Can't decrement. No completions or task hasn't been completed yet.", 'info')
    else:
        task = Task.query.get(task_id)
        user_task.completions -= 1
        new_points = max(user_task.points_awarded - task.points, 0)  # Ensure points don't go negative
        user_task.points_awarded = new_points
        if user_task.completions == 0:
            user_task.completed = False  # Adjust based on your application logic
        db.session.commit()
        flash('Task completion decremented.', 'success')
    return redirect(url_for('events.event_detail', event_id=user_task.task.event_id))



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


@events_bp.route('/complete_task/<int:task_id>', methods=['POST'])
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    user_task = UserTask.query.filter_by(user_id=current_user.id, task_id=task_id).first()

    if user_task and user_task.completions < task.completion_limit:
        user_task.completions += 1
        user_task.completed = True  # Mark as ever completed
        # Recalculate points awarded based on completions and multiplier
        user_task.points_awarded = user_task.completions * task.points * task.point_multiplier
        db.session.commit()
        flash('Task completed again. Points updated.', 'success')
    elif not user_task:
        # First time task completion
        user_task = UserTask(user_id=current_user.id, task_id=task_id, completed=True, completions=1, points_awarded=task.points * task.point_multiplier)
        db.session.add(user_task)
        db.session.commit()
        flash('Task marked as completed. Points awarded.', 'success')
    else:
        flash('Task completion limit reached.', 'info')

    return redirect(url_for('events.event_detail', event_id=task.event_id))

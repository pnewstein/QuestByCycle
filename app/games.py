from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models import db, Game, Task, UserTask, TaskSubmission
from app.forms import GameForm, TaskForm, TaskSubmissionForm
from app.utils import can_complete_task
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone

import os


games_bp = Blueprint('games', __name__)

@games_bp.route('/create_game', methods=['GET', 'POST'])
@login_required
def create_game():
    form = GameForm()
    if form.validate_on_submit():
        game = Game(
            title=form.title.data,
            description=form.description.data,
            description2=form.description2.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            game_goal=form.game_goal.data,
            details=form.details.data,
            awards=form.awards.data,
            beyond=form.beyond.data,
            admin_id=current_user.id
        )
        db.session.add(game)
        try:
            db.session.commit()
            flash('Game created successfully!', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while creating the game: {e}', 'error')
    return render_template('create_game.html', title='Create Game', form=form)


@games_bp.route('/update_game/<int:game_id>', methods=['GET', 'POST'])
@login_required
def update_game(game_id):
    game = Game.query.get_or_404(game_id)
    form = GameForm(obj=game)
    if form.validate_on_submit():
        form.populate_obj(game)  # This will automatically update all fields including new ones
        try:
            db.session.commit()
            flash('Game updated successfully!', 'success')
            return redirect(url_for('games.game_detail', game_id=game_id))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred while updating the game: {e}', 'error')
    return render_template('update_game.html', form=form, game_id=game_id)


@games_bp.route('/game_detail/<int:game_id>/<int:task_id>')
@games_bp.route('/game_detail/<int:game_id>', defaults={'task_id': None})
@login_required
def game_detail(game_id, task_id):
    game = Game.query.get_or_404(game_id)
    has_joined = game in current_user.participated_games
    tasks = Task.query.filter_by(game_id=game_id, enabled=True).all()

    selected_task = None
    if task_id:
        selected_task = Task.query.get_or_404(task_id)

    user_tasks = UserTask.query.filter_by(user_id=current_user.id).all()
    total_points = sum(ut.points_awarded for ut in user_tasks if ut.task.game_id == game_id)

    for task in tasks:
        completions = sum(1 for ut in user_tasks if ut.task_id == task.id and ut.completions > 0)

        task.completions_within_period = completions
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
        period_start = now - period_start_map.get(task.frequency.lower(), timedelta(days=1))

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
                task.next_eligible_time = last_completion.timestamp + increment_map.get(task.frequency.lower(), timedelta(days=1))
    
    tasks.sort(key=lambda x: x.completions_within_period, reverse=True)

    return render_template(
        'game_detail.html',
        game=game,
        has_joined=has_joined,
        tasks=tasks,
        total_points=total_points,
        selected_task=selected_task
    )



@games_bp.route('/register_game/<int:game_id>', methods=['POST'])
@login_required
def register_game(game_id):
    try:
        game = Game.query.get_or_404(game_id)
        if game not in current_user.participated_games:
            current_user.participated_games.append(game)
            db.session.commit()
            flash('You have successfully joined the game.', 'success')
        else:
            flash('You are already registered for this game.', 'info')
        return redirect(url_for('games.game_detail', game_id=game_id))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Failed to register user for game {game_id}: {e}')
        flash('An error occurred. Please try again.', 'error')
    return redirect(url_for('games.game_detail', game_id=game_id))


@games_bp.route('/delete_game/<int:game_id>', methods=['POST'])
@login_required
def delete_game(game_id):
    if not current_user.is_admin:
        flash('Access denied: Only administrators can delete games.', 'danger')
        return redirect(url_for('main.index'))

    game = Game.query.get_or_404(game_id)
    try:
        # Optional: Delete related data (e.g., tasks) if necessary
        for task in game.tasks:
            db.session.delete(task)
        
        db.session.delete(game)
        db.session.commit()
        flash('Game deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the game: {e}', 'error')
    
    return redirect(url_for('admin.admin_dashboard'))


@games_bp.route('/get_game_points/<int:game_id>', methods=['GET'])
@login_required
def get_game_points(game_id):
    # Query to get the total points awarded for a specific game
    total_game_points = db.session.query(
        db.func.sum(UserTask.points_awarded)
    ).join(Task, UserTask.task_id == Task.id
    ).filter(Task.game_id == game_id
    ).scalar() or 0

    # Query to get the goal for the specific game
    game = Game.query.get(game_id)
    game_goal = game.game_goal  # Assumes that `game_goal` is a column in your Game model

    return jsonify(total_game_points=total_game_points, game_goal=game_goal)


@games_bp.route('/game/<int:game_id>/details')
@login_required
def game_details(game_id):
    game = Game.query.get_or_404(game_id)
    return render_template('details.html', game=game)


@games_bp.route('/game/<int:game_id>/awards')
@login_required
def game_awards(game_id):
    game = Game.query.get_or_404(game_id)
    return render_template('awards.html', game=game)


@games_bp.route('/game/<int:game_id>/beyond')
@login_required
def game_beyond(game_id):
    game = Game.query.get_or_404(game_id)
    return render_template('beyond.html', game=game)
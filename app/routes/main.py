from flask import Blueprint, render_template, current_app, flash, redirect, url_for
from flask_login import current_user
from .forms import TaskForm
from app import db
from app.models import Task, User

main = Blueprint('main', __name__)

@app.route('/')
@app.route('/index')
def index():
    tasks = Task.query.all()
    return render_template('index.html', tasks=tasks)

@app.route('/submit_task', methods=['GET', 'POST'])
def submit_task():
    form = TaskForm()
    if form.validate_on_submit():
        task = Task(title=form.title.data, description=form.description.data, author=current_user)
        db.session.add(task)
        db.session.commit()
        flash('Your task has been submitted!', 'success')
        return redirect(url_for('index'))
    return render_template('submit_task.html', title='Submit Task', form=form)

@app.route('/leaderboard')
def leaderboard():
    top_users = User.query.order_by(User.score.desc()).all()
    users = User.query.join(Task).filter(Task.verified==True).group_by(User.id).order_by(db.func.count(Task.id).desc())
    return render_template('leaderboard.html', users=users, top_users=top_users)

# Example snippet from a hypothetical task completion route
@app.route('/complete_task/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    task = Task.query.get(task_id)
    if task and not task.completed:
        task.completed = True
        current_user.score += 10  # Assuming each task completion earns 10 points
        db.session.commit()
        flash('Task completed!', 'success')
    return redirect(url_for('index'))

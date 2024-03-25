# routes/main.py
from flask import render_template
from app import app
from app.models import Task

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

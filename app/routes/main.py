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
    if form

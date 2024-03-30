from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_from_directory
from flask_login import current_user, login_required
from itsdangerous import URLSafeTimedSerializer, BadSignature
from app.models import db, Event, User
from app.forms import SignInForm, SignOutForm, ProfileForm
from .config import load_config
from werkzeug.utils import secure_filename

import os
import logging
import uuid

main_bp = Blueprint('main', __name__)

config = load_config()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def generate_csrf_token(secret_key):
    serializer = URLSafeTimedSerializer(secret_key)
    return serializer.dumps({})  # Empty dict as the payload


def validate_csrf_token(token, secret_key, max_age=3600):
    serializer = URLSafeTimedSerializer(secret_key)
    try:
        serializer.loads(token, max_age=max_age)
        return True
    except BadSignature:
        return False

@main_bp.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        user_events = current_user.participated_events  # Directly access the events
    else:
        user_events = []

    return render_template('index.html', user_events=user_events)


@main_bp.route('/sign-in', methods=['GET', 'POST'])
def sign_in():
    form = SignInForm()

    if form.validate_on_submit():

        flash('Signed in successfully')
        return redirect(url_for('main.index'))

    return render_template('sign_in.html', form=form)



@main_bp.route('/sign-out', methods=['GET', 'POST'])
def sign_out():
    form = SignOutForm()

    if form.validate_on_submit():
        flash('Signed out successfully.')
    else:
        # If neither form submission nor continue button click
        return render_template('sign_out.html', form=form)

    session.pop('l_number', None)
    return redirect(url_for('main.index'))


@main_bp.route('/leaderboard')
@login_required
def leaderboard():
    users = User.query.order_by(User.score.desc()).all()
    return render_template('leaderboard.html', users=users)


@main_bp.route('/debug/events')
def debug_events():
    events = Event.query.all()  # Fetch all events for debugging
    return render_template('debug_events.html', events=events)


@main_bp.route('/steps')
def steps():
    # This page might contain links to all the subsections for an easy navigation
    return render_template('steps.html')

# Route for the "Introduction to Biking" section
@main_bp.route('/introduction-to-biking')
def introduction_to_biking():
    return render_template('introduction_to_biking.html')

# Route for the "Bicycle Types Explained" section
@main_bp.route('/bicycle-types-explained')
def bicycle_types_explained():
    # This could potentially fetch dynamic content if necessary
    return render_template('bicycle_types_explained.html')

# Route for the "Gear Up for Safety" section
@main_bp.route('/gear-up-for-safety')
def gear_up_for_safety():
    return render_template('gear_up_for_safety.html')

# Route for the "Riding Your Bike 101" section
@main_bp.route('/riding-your-bike-101')
def riding_your_bike_101():
    return render_template('riding_your_bike_101.html')

# Route for the "Warm-Up Exercises" section
@main_bp.route('/warm-up-exercises')
def warm_up_exercises():
    return render_template('warm_up_exercises.html')

# Route for the "Basic Bike Maintenance" section
@main_bp.route('/basic-bike-maintenance')
def basic_bike_maintenance():
    return render_template('basic_bike_maintenance.html')

# Route for the "Daily Ride Challenge" section (part of Skill-Building Tasks)
@main_bp.route('/daily-ride-challenge')
def daily_ride_challenge():
    return render_template('daily_ride_challenge.html')

# Route for the "Bike Repair Workshop" section
@main_bp.route('/bike-repair-workshop')
def bike_repair_workshop():
    return render_template('bike_repair_workshop.html')

@main_bp.route('/missions')
def missions():
    # This page might contain links to all the subsections for an easy navigation
    return render_template('missions.html')


def save_profile_picture(profile_picture_file):
    ext = profile_picture_file.filename.rsplit('.', 1)[-1]
    filename = secure_filename(f"{uuid.uuid4()}.{ext}")
    # Ensure 'uploads' directory exists under 'static'
    uploads_path = os.path.join(current_app.root_path, 'static', current_app.config['main']['UPLOAD_FOLDER'])
    if not os.path.exists(uploads_path):
        os.makedirs(uploads_path)
    # Save file
    profile_picture_file.save(os.path.join(uploads_path, filename))
    return os.path.join(current_app.config['main']['UPLOAD_FOLDER'], filename)


@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    if form.validate_on_submit():
        current_user.display_name = form.display_name.data
        current_user.age_group = form.age_group.data
        current_user.interests = form.interests.data

        # Check if 'profile_picture' is in request.files
        if 'profile_picture' in request.files:
            profile_picture_file = request.files['profile_picture']
            if profile_picture_file.filename != '':
                filename = save_profile_picture(profile_picture_file)  # Using your save_profile_picture function
                current_user.profile_picture = filename  # Save just the filename or relative path
                db.session.commit()
                flash('Profile updated successfully.', 'success')
            else:
                flash('No file selected for upload.', 'error')
        else:
            flash('No file part in the request.', 'error')

        return redirect(url_for('main.profile'))
    elif request.method == 'GET':
        form.display_name.data = current_user.display_name
        form.age_group.data = current_user.age_group
        form.interests.data = current_user.interests
        # Load other fields if necessary

    return render_template('profile.html', form=form)


@main_bp.route('/events')
def events():
    events = Event.query.all()
    return render_template('events.html', events=events)
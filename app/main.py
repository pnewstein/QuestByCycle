from flask import Blueprint, jsonify, send_file, render_template, request, redirect, url_for, flash, current_app, Response
from flask_login import current_user, login_required
from app.utils import save_profile_picture, save_bicycle_picture
from app.models import db, Game, User, Quest, Badge, UserQuest, QuestSubmission, QuestLike, ShoutBoardMessage, ShoutBoardLike, ProfileWallMessage, user_games
from app.forms import ProfileForm, ShoutBoardForm, ContactForm, BikeForm, LoginForm, RegistrationForm
from app.utils import send_email, allowed_file, generate_tutorial_game, enhance_badges_with_task_info, get_game_badges
from .config import load_config
from werkzeug.utils import secure_filename
from sqlalchemy import func
from sqlalchemy.orm import aliased
from datetime import datetime, timedelta, timezone
from pytz import utc
from flask_wtf.csrf import generate_csrf
from PIL import Image, ExifTags
from io import BytesIO
from functools import lru_cache

import bleach
import os
import logging
import io
main_bp = Blueprint('main', __name__)

ALLOWED_TAGS = [
    'a', 'b', 'i', 'u', 'em', 'strong', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'blockquote', 'code', 'pre', 'br', 'div', 'span', 'ul', 'ol', 'li', 'hr',
    'sub', 'sup', 's', 'strike', 'font', 'img', 'video', 'figure'
]

ALLOWED_ATTRIBUTES = {
    '*': ['class', 'id'],
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'width', 'height'],
    'video': ['src', 'width', 'height', 'controls'],
    'p': ['class'],
    'span': ['class'],
    'div': ['class'],
    'h1': ['class'],
    'h2': ['class'],
    'h3': ['class'],
    'h4': ['class'],
    'h5': ['class'],
    'h6': ['class'],
    'blockquote': ['class'],
    'code': ['class'],
    'pre': ['class'],
    'ul': ['class'],
    'ol': ['class'],
    'li': ['class'],
    'hr': ['class'],
    'sub': ['class'],
    'sup': ['class'],
    's': ['class'],
    'strike': ['class'],
    'font': ['color', 'face', 'size']
}

def sanitize_html(html_content):
    return bleach.clean(html_content, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)

config = load_config()

#cache_dir = os.path.join(app.instance_path, 'cache')  # Adjust the path as needed
#if not os.path.exists(cache_dir):
#    os.makedirs(cache_dir)

#from app import app

#cache = Cache(config={
#    'CACHE_TYPE': 'filesystem',
#    'CACHE_DIR': '/cache',  # Replace with your desired path
#    'CACHE_DEFAULT_TIMEOUT': 604800  # 7 days in seconds
#})
# Init cache
#cache.init_app(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_datetime(activity):
    if hasattr(activity, 'timestamp') and isinstance(activity.timestamp, datetime):
        return activity.timestamp.replace(tzinfo=None) if activity.timestamp.tzinfo is not None else activity.timestamp
    elif hasattr(activity, 'completed_at') and isinstance(activity.completed_at, datetime):
        return activity.completed_at.replace(tzinfo=None)
    else:
        raise ValueError("Activity object does not contain valid timestamp information.")


@main_bp.route('/', defaults={'game_id': None, 'quest_id': None, 'user_id': None})
@main_bp.route('/<int:game_id>', defaults={'quest_id': None, 'user_id': None})
@main_bp.route('/<int:game_id>/<int:quest_id>', defaults={'user_id': None})
@main_bp.route('/<int:game_id>/<int:quest_id>/<int:user_id>')
def index(game_id, quest_id, user_id):
    print(f"Index function called, game_id: {game_id}") # Log game_id at start

    user_games_list = []
    profile = None
    user_quests = []
    total_points = None
    start_onboarding = False
    login_form = LoginForm()
    register_form = RegistrationForm()
    all_badges = []
    earned_badges = []

    # Check if the user is authenticated and set the user_id
    if user_id is None and current_user.is_authenticated:
        user_id = current_user.id

    # Check if the game_id is None and set it from the joined games if available
    if game_id is None and current_user.is_authenticated:
        if current_user.selected_game_id:
            game_id = current_user.selected_game_id
        else:
            joined_games = current_user.participated_games
            if joined_games:
                game_id = joined_games[0].id

    game = Game.query.get(game_id) if game_id else None

    # Ensure the user has joined the game before proceeding
    if game_id and current_user.is_authenticated:
        if game not in current_user.participated_games:
            return redirect(url_for('main.index'))
        
        # Update the selected_game_id for the user
        if current_user.selected_game_id != game_id:
            current_user.selected_game_id = game_id
            db.session.commit()
            
    # Determine if the user needs onboarding
    #if current_user.is_authenticated and not current_user.onboarded:
    #    start_onboarding = True  # Trigger the onboarding script
    #else:
    #    current_user.onboarded = True
    #    db.session.commit()

    # If the user is authenticated, load user-specific quests and data
    if current_user.is_authenticated:
        user_quests = UserQuest.query.filter_by(user_id=current_user.id).all()
        total_points = sum(ut.points_awarded for ut in user_quests if ut.quest.game_id == game_id)

    quests = Quest.query.filter_by(game_id=game.id, enabled=True).all() if game else []
    has_joined = game in current_user.participated_games if game else False
    game_participation = {game.id: has_joined} if game else {}

    # Load forms and messages for the Shout Board
    form = ShoutBoardForm()
    pinned_messages = ShoutBoardMessage.query.filter_by(is_pinned=True, game_id=game_id).order_by(ShoutBoardMessage.timestamp.desc()).all()
    unpinned_messages = ShoutBoardMessage.query.filter_by(is_pinned=False, game_id=game_id).order_by(ShoutBoardMessage.timestamp.desc()).all()
    completed_quests = UserQuest.query.filter(UserQuest.completions > 0).order_by(UserQuest.completed_at.desc()).all()

    if game:
        pinned_activities = pinned_messages
        unpinned_activities = unpinned_messages + [ut for ut in completed_quests if ut.quest.game_id == game_id]
    else:
        pinned_activities = []
        unpinned_activities = []

    unpinned_activities.sort(key=lambda x: get_datetime(x), reverse=True)
    activities = pinned_activities + unpinned_activities

    selected_quest = Quest.query.get(quest_id) if quest_id else None

    if current_user.is_authenticated:
        liked_message_ids = {like.message_id for like in ShoutBoardLike.query.filter_by(user_id=current_user.id)}
        liked_quest_ids = {like.quest_id for like in QuestLike.query.filter_by(user_id=current_user.id)}
        
        # Fetch games along with joined_at timestamps
        user_games_list = db.session.query(Game, user_games.c.joined_at).join(user_games, user_games.c.game_id == Game.id).filter(user_games.c.user_id == current_user.id).all()
        
        profile = User.query.get_or_404(user_id)
        user_quests = UserQuest.query.filter_by(user_id=profile.id).all()
        
        if game_id:
                all_badges = get_game_badges(game_id) # Fetch game-specific badges using new function
        else:
            all_badges = Badge.query.all() # Fallback to all badges if no game_id
        earned_badges_set = set(profile.badges) # keep as set for efficient check

        # Enhance all_badges with task info - now game-aware
        enhanced_all_badges = enhance_badges_with_task_info(all_badges, game_id) # Use helper function
        all_badges = enhanced_all_badges

        # Enhance earned_badges with task info - now game-aware
        enhanced_earned_badges = enhance_badges_with_task_info(list(earned_badges_set), game_id) # Use helper function, convert set to list
        earned_badges = enhanced_earned_badges

        print(f"Index function: all_badges count: {len(all_badges)}, earned_badges count: {len(earned_badges)}") # Log counts
        
        if not profile.display_name:
            profile.display_name = profile.username

    now = datetime.now(utc)
    period_start_map = {
        'daily': timedelta(days=1),
        'weekly': timedelta(weeks=1),
        'monthly': timedelta(days=30)
    }

    for quest in quests:
        quest.total_completions = db.session.query(QuestSubmission).filter(QuestSubmission.quest_id == quest.id).count()
        quest.personal_completions = db.session.query(QuestSubmission).filter(QuestSubmission.quest_id == quest.id, QuestSubmission.user_id == user_id).count() if user_id else 0
        quest.completions_within_period = 0
        quest.can_verify = False
        quest.last_completion = None
        quest.first_completion_in_period = None
        quest.next_eligible_time = None
        quest.completion_timestamps = []

        if user_id:
            period_start = now - period_start_map.get(quest.frequency, timedelta(days=1))
            submissions = QuestSubmission.query.filter(
                QuestSubmission.user_id == user_id,
                QuestSubmission.quest_id == quest.id,
                QuestSubmission.timestamp >= period_start
            ).all()

            if submissions:
                quest.completions_within_period = len(submissions)
                quest.first_completion_in_period = min(submissions, key=lambda x: x.timestamp).timestamp
                quest.completion_timestamps = [sub.timestamp for sub in submissions]

            relevant_user_quests = [ut for ut in user_quests if ut.quest_id == quest.id]
            quest.last_completion = max((ut.completed_at for ut in relevant_user_quests), default=None)

            if quest.personal_completions < quest.completion_limit:
                quest.can_verify = True
            else:
                last_completion = max(submissions, key=lambda x: x.timestamp, default=None)
                if last_completion:
                    increment_map = {
                        'daily': timedelta(days=1),
                        'weekly': timedelta(weeks=1),
                        'monthly': timedelta(days=30)
                    }
                    quest.next_eligible_time = last_completion.timestamp + increment_map.get(quest.frequency, timedelta(days=1))

    quests.sort(key=lambda x: (-x.is_sponsored, -x.personal_completions, -x.total_completions))

    custom_games = Game.query.filter(Game.custom_game_code.isnot(None), Game.is_public.is_(True)).all()

    carousel_images = []
    if current_user.is_authenticated and game_id:
        quest_submissions = QuestSubmission.query.join(Quest).filter(Quest.game_id == game_id).all()
        for submission in quest_submissions:
            if submission.image_url:
                # Ensure the image_url is relative to 'static/'
                image_url = submission.image_url.lstrip('/').replace('static/', '')
                
                # Ensure the path includes 'images/' if missing
                if not image_url.startswith('images/'):
                    image_url = f'images/{image_url}'
                
                carousel_images.append({
                    'small': image_url,
                    'medium': image_url,
                    'large': image_url,
                    'quest_title': submission.quest.title,
                    'comment': submission.comment
                })

    return render_template('index.html',
                           form=form,
                           badges=earned_badges,
                           all_badges=all_badges,
                           games=user_games_list,
                           game=game,
                           user_games=user_games_list,
                           activities=activities,
                           quests=quests,
                           game_participation=game_participation,
                           selected_quest=selected_quest,
                           has_joined=has_joined,
                           profile=profile,
                           user_quests=user_quests,
                           carousel_images=carousel_images,
                           total_points=total_points,
                           completions=completed_quests,
                           custom_games=custom_games,
                           selected_game_id=game_id or 0,
                           selected_game=game,
                           quest_id=quest_id,
                           start_onboarding=start_onboarding,
                           login_form=login_form,
                           register_form=register_form)

@main_bp.route('/mark-onboarding-complete', methods=['POST'])
@login_required
def mark_onboarding_complete():
    try:
        # Update the onboarded status in the database
        current_user.onboarded = True
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"Error marking onboarding complete: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    

@main_bp.route('/shout-board/<int:game_id>', methods=['POST'])
@login_required
def shout_board(game_id):
    print(f"Game ID received (initial): {game_id}")  # Debugging line
    
    form = ShoutBoardForm()
    
    if not form.game_id.data:
        form.game_id.data = game_id

    if form.validate_on_submit():
        is_pinned = 'is_pinned' in request.form
        message_content = sanitize_html(form.message.data)
        shout_message = ShoutBoardMessage(
            message=message_content,
            user_id=current_user.id,
            game_id=game_id,
            is_pinned=is_pinned
        )
        db.session.add(shout_message)
        db.session.commit()
        flash('Your message has been posted!', 'success')
        return redirect(url_for('main.index', game_id=game_id))
    else:
        print("Form Errors:", form.errors)  # Output form errors to the console
        flash('There was an error with your submission.', 'error')
        return redirect(url_for('main.index', game_id=game_id))


@main_bp.route('/like-message/<int:message_id>', methods=['POST'])
@login_required
def like_message(message_id):
    # Retrieve the message by ID
    message = ShoutBoardMessage.query.get_or_404(message_id)
    # Check if the current user already liked this message
    already_liked = ShoutBoardLike.query.filter_by(user_id=current_user.id, message_id=message.id).first() is not None

    if not already_liked:
        # User has not liked this message before, so create a new like
        new_like = ShoutBoardLike(user_id=current_user.id, message_id=message.id)
        db.session.add(new_like)
        db.session.commit()
        success = True
    else:
        # User already liked the message. Optionally, handle "unliking" here
        success = False

    # Fetch the new like count for the message
    new_like_count = db.session.query(ShoutBoardLike).filter_by(message_id=message_id).count()
    return jsonify(success=success, new_like_count=new_like_count, already_liked=already_liked)


@main_bp.route('/leaderboard_partial')
@login_required
def leaderboard_partial():
    selected_game_id = request.args.get('game_id', type=int)

    if selected_game_id:
        game = Game.query.get(selected_game_id)
        if not game:
            return jsonify({'error': 'Game not found'}), 404

        top_users_query = db.session.query(
            User.id,
            User.username,
            User.display_name,
            db.func.sum(UserQuest.points_awarded).label('total_points')
        ).join(UserQuest, UserQuest.user_id == User.id
        ).join(Quest, Quest.id == UserQuest.quest_id
        ).filter(Quest.game_id == selected_game_id
        ).group_by(User.id, User.username, User.display_name
        ).order_by(db.func.sum(UserQuest.points_awarded).desc()
        ).all()

        top_users = [{
            'user_id': user_id,
            'username': username,
            'display_name': display_name,
            'total_points': total_points
        } for user_id, username, display_name, total_points in top_users_query]

        total_game_points = db.session.query(
            db.func.sum(UserQuest.points_awarded)
        ).join(Quest, UserQuest.quest_id == Quest.id
        ).filter(Quest.game_id == selected_game_id
        ).scalar() or 0

        return jsonify({
            'top_users': top_users,
            'total_game_points': total_game_points,
            'game_goal': game.game_goal if game.game_goal else None
        })


@main_bp.route('/profile/<int:user_id>')
@login_required
def user_profile(user_id):
    user = User.query.get_or_404(user_id)
    user_quests = UserQuest.query.filter(UserQuest.user_id == user.id, UserQuest.completions > 0).all()
    badges = user.badges
    participated_games = user.participated_games
    quest_submissions = user.quest_submissions
    profile_messages = ProfileWallMessage.query.filter_by(user_id=user_id).order_by(ProfileWallMessage.timestamp.desc()).all()

    # Define riding preferences choices here
    riding_preferences_choices = [
        ('new_novice', 'New and novice rider'),
        ('elementary_school', 'In elementary school or younger'),
        ('middle_school', 'In Middle school'),
        ('high_school', 'In High school'),
        ('college', 'College student'),
        ('families', 'Families who ride with their children'),
        ('grandparents', 'Grandparents who ride with their grandchildren'),
        ('seasoned', 'Seasoned riders who ride all over town for their transportation'),
        ('adaptive', 'Adaptive bike users'),
        ('occasional', 'Occasional rider'),
        ('ebike', 'E-bike rider'),
        ('long_distance', 'Long distance rider'),
        ('no_car', 'Don’t own a car'),
        ('commute', 'Commute by bike'),
        ('seasonal', 'Seasonal riders: I don’t like riding in inclement weather'),
        ('environmentally_conscious', 'Environmentally Conscious Riders'),
        ('social', 'Social Riders'),
        ('fitness_focused', 'Fitness-Focused Riders'),
        ('tech_savvy', 'Tech-Savvy Riders'),
        ('local_history', 'Local History or Culture Enthusiasts'),
        ('advocacy_minded', 'Advocacy-Minded Riders'),
        ('bike_collectors', 'Bike Collectors or Bike Equipment Geek'),
        ('freakbike', 'Freakbike rider/maker')
    ]

    response_data = {
        'current_user_id': current_user.id,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'profile_picture': user.profile_picture,
            'display_name': user.display_name,
            'interests': user.interests,
            'age_group': user.age_group,
            'riding_preferences': user.riding_preferences or [],  # Ensure this is a list
            'ride_description': user.ride_description,
            'bike_picture': user.bike_picture,
            'bike_description': user.bike_description,
            'upload_to_socials': user.upload_to_socials,
            'show_carbon_game': user.show_carbon_game,
            'badges': [{'id': badge.id, 'name': badge.name, 'description': badge.description, 'category': badge.category, 'image': badge.image} for badge in badges]
        },
        'user_quests': [
            {'id': quest.id, 'completions': quest.completions}
            for quest in user_quests
        ],
        'profile_messages': [
            {
                'id': message.id,
                'content': message.content,
                'timestamp': message.timestamp.strftime('%B %d, %Y %H:%M'),
                'author_id': message.author_id,
                'author': {
                    'username': message.author.username,
                    'display_name': message.author.display_name
                },
                'parent_id': message.parent_id
            }
            for message in profile_messages
        ],
        'participated_games': [
            {'id': game.id, 'title': game.title, 'description': game.description, 'start_date': game.start_date.strftime('%B %d, %Y'), 'end_date': game.end_date.strftime('%B %d, %Y')}
            for game in participated_games
        ],
        'quest_submissions': [
            {'id': submission.id, 'quest': {'title': submission.quest.title}, 'comment': submission.comment, 'timestamp': submission.timestamp.strftime('%B %d, %Y %H:%M'), 'image_url': submission.image_url, 'twitter_url': submission.twitter_url, 'fb_url': submission.fb_url, 'instagram_url': submission.instagram_url}
            for submission in quest_submissions
        ],
        'riding_preferences_choices': riding_preferences_choices  # Use centralized preferences
    }

    return jsonify(response_data)


@main_bp.route('/profile/<int:user_id>/edit', methods=['POST'])
@login_required
def edit_profile(user_id):
    if user_id != current_user.id:
        print(f'Unauthorized access attempt by user {current_user.id}')
        return jsonify({'error': 'Unauthorized access'}), 403

    profile_form = ProfileForm()

    user = User.query.get_or_404(user_id)

    if profile_form.validate_on_submit():
        print('Profile form validated successfully.')
        try:
            # Handle profile picture upload
            profile_picture = request.files.get('profile_picture')
            if profile_picture and hasattr(profile_picture, 'filename'):
                user.profile_picture = save_profile_picture(profile_picture, user.profile_picture)
                print(f'Updated profile picture: {user.profile_picture}')

            # Update other fields
            user.display_name = profile_form.display_name.data
            user.age_group = profile_form.age_group.data
            user.interests = profile_form.interests.data
            user.riding_preferences = request.form.getlist('riding_preferences')
            user.ride_description = profile_form.ride_description.data
            user.upload_to_socials = profile_form.upload_to_socials.data
            user.show_carbon_game = profile_form.show_carbon_game.data

            db.session.commit()
            print('Profile updated successfully in the database.')
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            print(f'Exception occurred: {str(e)}')
            return jsonify({'error': f'Failed to update profile: {str(e)}'}), 500

    # Debug: Log form validation errors
    for field, errors in profile_form.errors.items():
        for error in errors:
            print(f'Error in the {field} field - {error}')
            
    return jsonify({'error': 'Invalid form submission'}), 400



@main_bp.route('/profile/<int:user_id>/edit-bike', methods=['POST'])
@login_required
def edit_bike(user_id):
    if user_id != current_user.id:
        print(f'Unauthorized access attempt by user {current_user.id}')
        return jsonify({'error': 'Unauthorized access'}), 403

    bike_form = BikeForm()

    user = User.query.get_or_404(user_id)

    if bike_form.validate_on_submit():
        print('Bike form validated successfully.')
        try:
            # Handle bicycle picture upload using get method
            bike_picture = request.files.get('bike_picture', None)

            if bike_picture and bike_picture.filename:
                user.bike_picture = save_bicycle_picture(bike_picture, user.bike_picture)
                print(f'Updated bike picture: {user.bike_picture}')

            user.bike_description = bike_form.bike_description.data

            db.session.commit()
            print('Bike updated successfully in the database.')
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            print(f'Exception occurred: {str(e)}')
            return jsonify({'error': f'Failed to update bike: {str(e)}'}), 500

    # Debug: Log form validation errors
    print('Bike form validation failed.')
    for field, errors in bike_form.errors.items():
        for error in errors:
            print(f'Error in the {field} field - {error}')

    return jsonify({'error': 'Invalid form submission'}), 400


@main_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    if 'profile_picture' in request.files:
        file = request.files['profile_picture']
        if file:
            old_filename = current_user.profile_picture
            current_user.profile_picture = save_profile_picture(file, old_filename)
    
    current_user.display_name = sanitize_html(request.form.get('display_name', current_user.display_name))
    current_user.age_group = sanitize_html(request.form.get('age_group', current_user.age_group))
    current_user.interests = sanitize_html(request.form.get('interests', current_user.interests))

    # Update new fields
    current_user.riding_preferences = request.form.getlist('riding_preferences')
    current_user.ride_description = sanitize_html(request.form.get('ride_description', current_user.ride_description))
    current_user.bike_description = sanitize_html(request.form.get('bike_description', current_user.bike_description))
    current_user.upload_to_socials = 'upload_to_socials' in request.form
    current_user.show_carbon_game = 'show_carbon_game' in request.form

    if 'bike_picture' in request.files:
        bike_picture_file = request.files['bike_picture']
        if bike_picture_file and allowed_file(bike_picture_file.filename):
            bike_filename = save_profile_picture(bike_picture_file)  # Assuming you have a separate method for saving bike images
            current_user.bike_picture = bike_filename

    db.session.commit()
    return jsonify(success=True)


@main_bp.route('/like_quest/<int:quest_id>', methods=['POST'])
@login_required
def like_quest(quest_id):
    quest = Quest.query.get_or_404(quest_id)
    # Check if the current user already liked this quest
    already_liked = QuestLike.query.filter_by(user_id=current_user.id, quest_id=quest.id).first() is not None

    if not already_liked:
        # User has not liked this quest before, so create a new like
        new_like = QuestLike(user_id=current_user.id, quest_id=quest.id)
        db.session.add(new_like)
        db.session.commit()
        success = True
    else:
        # User already liked the quest. Optionally, handle "unliking" here
        success = False

    # Fetch the new like count for the quest
    new_like_count = QuestLike.query.filter_by(quest_id=quest.id).count()
    return jsonify(success=success, new_like_count=new_like_count, already_liked=already_liked)


@main_bp.route('/pin_message/<int:game_id>/<int:message_id>', methods=['POST'])
@login_required
def pin_message(game_id, message_id):
    message = ShoutBoardMessage.query.get_or_404(message_id)
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('main.index'))
    
    message.is_pinned = not message.is_pinned  # Toggle the pin status
    db.session.commit()
    flash('Message pin status updated.', 'success')
    return redirect(url_for('main.index', game_id=game_id))


@main_bp.route('/contact', methods=['POST'])
@login_required
def contact():    
    form = ContactForm()
    if form.validate_on_submit():
        message = sanitize_html(form.message.data)
        subject = "New Contact Form Submission"
        recipient = current_app.config['MAIL_DEFAULT_SENDER']

        user_info = None
        if current_user.is_authenticated:
            user_info = {
                "username": current_user.username,
                "email": current_user.email,
                "is_admin": current_user.is_admin,
                "created_at": current_user.created_at,
                "license_agreed": current_user.license_agreed,
                "display_name": current_user.display_name,
                "age_group": current_user.age_group,
                "interests": current_user.interests,
                "email_verified": current_user.email_verified,
            }

        html = render_template('contact_email.html', message=message, user_info=user_info)
        try:
            send_email(recipient, subject, html)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=True)
            flash('Your message has been sent successfully.', 'success')
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, message="Failed to send your message"), 500
            flash('Failed to send your message. Please try again later.', 'error')
            current_app.logger.error(f'Failed to send contact form message: {e}')
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(success=False, message="Validation failed"), 400
        flash('Validation failed. Please ensure all fields are filled correctly.', 'warning')

    return redirect(url_for('main.index'))


@main_bp.route('/refresh-csrf', methods=['GET'])
def refresh_csrf():
    new_csrf_token = generate_csrf()
    response = jsonify({'csrf_token': new_csrf_token})

    # Setting the cookie with Secure, HttpOnly, and SameSite attributes
    response.set_cookie(
        'csrf_token',
        new_csrf_token,
        secure=True,         # Ensures the cookie is sent only over HTTPS
        httponly=True,       # Prevents JavaScript from accessing the cookie
        samesite='Strict'    # Ensures the cookie is sent only for same-site requests
    )

    return response


@main_bp.route('/resize_image')
#@cache.cached(timeout=604800, query_string=True)  # Cache for 1 day
def resize_image():
    image_path = request.args.get('path')
    width = request.args.get('width', type=int)

    if not image_path or not width:
        return jsonify({'error': "Invalid request: Missing 'path' or 'width'"}), 400

    try:
        # Combine the static folder and the image path
        full_image_path = os.path.abspath(os.path.join(current_app.static_folder, image_path))

        # Ensure that the resolved path is within the static folder to prevent path traversal
        if not full_image_path.startswith(os.path.abspath(current_app.static_folder)):
            current_app.logger.error(f"Attempted path traversal detected: {image_path}")
            return jsonify({'error': 'Invalid file path'}), 400

        if not os.path.exists(full_image_path):
            current_app.logger.error(f"File not found: {full_image_path}")
            return jsonify({'error': 'File not found'}), 404

        # Open the image
        with Image.open(full_image_path) as img:
            # Correct orientation based on EXIF data
            try:
                for orientation in ExifTags.TAGS.keys():
                    if ExifTags.TAGS[orientation] == 'Orientation':
                        break

                exif = img._getexif()
                if exif is not None:
                    orientation_value = exif.get(orientation)

                    if orientation_value == 3:
                        img = img.rotate(180, expand=True)
                    elif orientation_value == 6:
                        img = img.rotate(-90, expand=True)
                    elif orientation_value == 8:
                        img = img.rotate(90, expand=True)
            except (AttributeError, KeyError, IndexError):
                # No EXIF orientation data, proceed without altering the image
                pass

            # Calculate the height to maintain aspect ratio
            ratio = width / float(img.width)
            height = int(img.height * ratio)

            # Resize the image using LANCZOS resampling
            img_resized = img.resize((width, height), Image.Resampling.LANCZOS)

            img_io = io.BytesIO()

            # Save the image with appropriate compression settings
            if img_resized.mode in ('RGBA', 'LA') or (img_resized.mode == 'P' and 'transparency' in img_resized.info):
                # For images with transparency, convert to RGBA
                img_resized = img_resized.convert('RGBA')
                img_resized.save(img_io, 'WEBP')
            else:
                # For images without transparency
                img_resized = img_resized.convert('RGB')
                img_resized.save(img_io, 'WEBP')

            img_io.seek(0)

            return send_file(img_io, mimetype='image/webp')
        
    except Exception as e:
        current_app.logger.error(f"Exception occurred during image processing: {e}")
        return jsonify({'error': 'Internal server error'}), 500
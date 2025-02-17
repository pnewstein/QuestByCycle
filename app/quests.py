from flask import Blueprint, make_response, jsonify, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from app.utils import update_user_score, getLastRelevantCompletionTime, check_and_award_badges, check_and_revoke_badges, save_badge_image, save_submission_image, can_complete_quest
from app.forms import QuestForm, PhotoForm
from app.social import post_to_social_media
from .models import db, Game, Quest, Badge, UserQuest, QuestSubmission, User
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from datetime import datetime, timezone, timedelta
from io import BytesIO
from flask_socketio import emit

import base64
import csv
import os
import qrcode
import bleach

quests_bp = Blueprint('quests', __name__, template_folder='templates')

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


def emit_status(message, sid):
    print(f'Emitting status: {message} to SID: {sid}')  # Debugging
    from app import socketio
    socketio.emit('loading_status', {'status': message}, room=sid)


@quests_bp.route('/<int:game_id>/manage_quests', methods=['GET'])
@login_required
def manage_game_quests(game_id):
    game = Game.query.get_or_404(game_id)

    if not current_user.is_admin:
        flash('Access denied: Only administrators can manage quests.', 'danger')
        return redirect(url_for('main.index', game_id=game_id))
    
    form = QuestForm()
    quests = Quest.query.filter_by(game_id=game_id).all()
    return render_template('manage_quests.html', game=game, quests=quests, form=form, game_id=game_id)


@quests_bp.route('/game/<int:game_id>/add_quest', methods=['GET', 'POST'])
@login_required
def add_quest(game_id):
    form = QuestForm()
    form.game_id.data = game_id  # Set the game_id field in the form

    if form.validate_on_submit():
        badge_id = form.badge_id.data if form.badge_id.data and form.badge_id.data != '0' else None

        if not badge_id and form.badge_name.data:
            badge_image_file = None
            if 'badge_image_filename' in request.files:
                badge_image_file = request.files['badge_image_filename']
                if badge_image_file and badge_image_file.filename != '':
                    badge_image_file = save_badge_image(badge_image_file)
                else:
                    flash('No badge image selected for upload.', 'error')

            new_badge = Badge(
                name=sanitize_html(form.badge_name.data),
                description=sanitize_html(form.badge_description.data),
                image=badge_image_file
            )
            db.session.add(new_badge)
            db.session.flush()
            badge_id = new_badge.id

        new_quest = Quest(
            title=sanitize_html(form.title.data),
            description=sanitize_html(form.description.data),
            tips=sanitize_html(form.tips.data),
            points=form.points.data,
            game_id=game_id,
            completion_limit=form.completion_limit.data,
            badge_awarded=form.badge_awarded.data,
            frequency=sanitize_html(form.frequency.data),
            enabled=form.enabled.data,
            is_sponsored=form.is_sponsored.data,
            category=sanitize_html(form.category.data),
            verification_type=sanitize_html(form.verification_type.data),
            badge_id=badge_id
        )
        db.session.add(new_quest)
        try:
            db.session.commit()
            flash('Quest added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {e}', 'error')

        return redirect(url_for('quests.manage_game_quests', game_id=game_id))

    return render_template('add_quest.html', form=form, game_id=game_id)


@quests_bp.route('/quest/<int:quest_id>/submit', methods=['POST'])
@login_required
def submit_quest(quest_id):
    quest = Quest.query.get_or_404(quest_id)
    game = Game.query.get_or_404(quest.game_id)
    now = datetime.now()

    if not (game.start_date <= now <= game.end_date):
        return jsonify({'success': False, 'message': 'This quest cannot be completed outside of the game dates'}), 403

    # Check if the user can verify the quest
    can_verify, next_eligible_time = can_complete_quest(current_user.id, quest_id)
    if not can_verify:
        return jsonify({'success': False, 'message': f'You cannot submit this quest again until {next_eligible_time}'}), 403

    sid = request.form.get('sid')
    if not sid:
        print("No session ID provided.")
        return jsonify({'success': False, 'message': 'No session ID provided'}), 400

    verification_type = quest.verification_type
    image_file = request.files.get('image')
    comment = sanitize_html(request.form.get('verificationComment', ''))

    if verification_type == 'qr_code':
        return jsonify({'success': True, 'message': 'QR Code verification does not require any submission'}), 200
    if verification_type == 'photo' and (not image_file or image_file.filename == ''):
        return jsonify({'success': False, 'message': 'No file selected for photo verification'}), 400
    if verification_type == 'comment' and not comment:
        return jsonify({'success': False, 'message': 'Comment required for verification'}), 400
    if verification_type == 'photo_comment' and (not image_file or image_file.filename == ''):
        return jsonify({'success': False, 'message': 'Both photo and comment are required for verification'}), 400
    if quest.verification_type == 'Pause':
        return jsonify({'success': False, 'message': 'This quest is currently paused'}), 403

    emit_status('Initializing submission process...', sid)

    try:
        image_url = None
        if image_file and image_file.filename:
            emit_status('Saving submission image...', sid)
            image_url = save_submission_image(image_file)
            image_path = os.path.join(current_app.static_folder, image_url)

        display_name = current_user.display_name or current_user.username
        status = f"{display_name} completed '{quest.title}'! #QuestByCycle"

        twitter_url, fb_url, instagram_url = None, None, None
        if image_url and current_user.upload_to_socials:
            emit_status('Posting to social media...', sid)
            twitter_url, fb_url, instagram_url = post_to_social_media(image_url, image_path, status, game, sid)

        emit_status('Saving submission details...', sid)
        new_submission = QuestSubmission(
            quest_id=quest_id,
            user_id=current_user.id,
            image_url=url_for('static', filename=image_url) if image_url else url_for('static', filename='images/commentPlaceholder.png'),
            comment=comment,
            twitter_url=twitter_url,
            fb_url=fb_url,
            instagram_url=instagram_url,
            timestamp=datetime.now(),
        )
        db.session.add(new_submission)

        user_quest = UserQuest.query.filter_by(user_id=current_user.id, quest_id=quest_id).first()
        if not user_quest:
            user_quest = UserQuest(
                user_id=current_user.id,
                quest_id=quest_id,
                completions=0,
                points_awarded=0,
                completed_at=datetime.now()
            )
            db.session.add(user_quest)

        user_quest.completions = (user_quest.completions or 0) + 1
        user_quest.points_awarded = (user_quest.points_awarded or 0) + quest.points
        user_quest.completed_at = datetime.now()

        emit_status('Finalizing submission...', sid)

        db.session.commit()

        update_user_score(current_user.id)
        check_and_award_badges(current_user.id, quest_id, quest.game_id)

        total_points = sum(ut.points_awarded for ut in UserQuest.query.filter_by(user_id=current_user.id))

        emit_status('Submission complete!', sid)
        
        from app import socketio
        socketio.emit('submission_complete', {'status': "Submission Complete"}, room=sid)

        return jsonify({
            'success': True,
            'new_completion_count': user_quest.completions,
            'total_points': total_points,
            'image_url': image_url,
            'comment': comment,
            'twitter_url': twitter_url,
            'fb_url': fb_url,
            'instagram_url': instagram_url
        })
    except Exception as e:
        db.session.rollback()
        emit_status('Submission failed.', sid)  # Emit failure status
        return jsonify({'success': False, 'message': str(e)})


@quests_bp.route('/quest/<int:quest_id>/update', methods=['POST'])
@login_required
def update_quest(quest_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    quest = Quest.query.get_or_404(quest_id)
    data = request.get_json()

    quest.title = sanitize_html(data.get('title', quest.title))
    quest.description = sanitize_html(data.get('description', quest.description))
    quest.tips = sanitize_html(data.get('tips', quest.tips))
    quest.points = data.get('points', quest.points)
    quest.completion_limit = data.get('completion_limit', quest.completion_limit)
    quest.badge_awarded = data.get('badge_awarded', quest.badge_awarded)
    quest.enabled = data.get('enabled', quest.enabled)
    quest.is_sponsored = data.get('is_sponsored', quest.is_sponsored)
    quest.category = sanitize_html(data.get('category', quest.category))
    quest.verification_type = sanitize_html(data.get('verification_type', quest.verification_type))
    quest.frequency = sanitize_html(data.get('frequency', quest.frequency))

    badge_id = data.get('badge_id')
    if badge_id is not None:
        try:
            quest.badge_id = int(badge_id)
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid badge ID'}), 400

    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Quest updated successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
    

@quests_bp.route('/quest/<int:quest_id>/delete', methods=['DELETE'])
@login_required
def delete_quest(quest_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    # Fetch the quest to be deleted
    quest_to_delete = Quest.query.get_or_404(quest_id)
    
    # Deleting the quest. The cascade options in the relationship should handle deletion of related records.
    db.session.delete(quest_to_delete)

    try:
        db.session.commit()
        return jsonify({'success': True, 'message': 'Quest deleted successfully'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Failed to delete quest {quest_id}: {e}')
        return jsonify({'success': False, 'message': 'Failed to delete quest'})


@quests_bp.route('/game/<int:game_id>/quests', methods=['GET'])
def get_quests_for_game(game_id):
    quests = Quest.query.filter_by(game_id=game_id).all()
    quests_data = [
        {
            'id': quest.id,
            'title': quest.title,
            'description': quest.description,
            'tips': quest.tips,
            'points': quest.points,
            'completion_limit': quest.completion_limit,
            'enabled': quest.enabled,
            'is_sponsored': quest.is_sponsored,
            'verification_type': quest.verification_type,
            'badge_name': quest.badge.name if quest.badge else 'None',
            'badge_description': quest.badge.description if quest.badge else '',
            'badge_awarded': quest.badge_awarded if quest.badge_id else '',
            'frequency': quest.frequency,  # Handling Frequency Enum
            'category': quest.category if quest.category else 'Not Set',  # Handling potentially undefined Category
        }
        for quest in quests
    ]
    return jsonify(quests=quests_data)


@quests_bp.route('/game/<int:game_id>/import_quests', methods=['POST'])
@login_required
def import_quests(game_id):
    if 'quests_csv' not in request.files:
        return jsonify(success=False, message="No file part"), 400
    
    file = request.files['quests_csv']
    if file.filename == '':
        return jsonify(success=False, message="No selected file"), 400
    
    if file:
        upload_dir = current_app.config['TASKCSV']
        os.makedirs(upload_dir, exist_ok=True)
        
        filepath = os.path.join(upload_dir, secure_filename(file.filename))
        file.save(filepath)

        imported_badges = []
        with open(filepath, mode='r', encoding='utf-8') as csv_file:
            quests_data = csv.DictReader(csv_file)
            for quest_info in quests_data:
                badge = Badge.query.filter_by(name=sanitize_html(quest_info['badge_name'])).first()
                if not badge:
                    badge = Badge(
                        name=sanitize_html(quest_info['badge_name']),
                        description=sanitize_html(quest_info['badge_description']),
                    )
                    db.session.add(badge)
                    db.session.flush()
                    imported_badges.append(badge.id)

                new_quest = Quest(
                    category=sanitize_html(quest_info['category']),
                    title=sanitize_html(quest_info['title']),
                    description=sanitize_html(quest_info['description']),
                    tips=sanitize_html(quest_info['tips']),
                    points=quest_info['points'].replace(',', ''),
                    completion_limit=quest_info['completion_limit'],
                    frequency=sanitize_html(quest_info['frequency']),
                    verification_type=sanitize_html(quest_info['verification_type']),
                    badge_id=badge.id,
                    badge_awarded=quest_info['badge_awarded'],
                    game_id=game_id
                )
                db.session.add(new_quest)
            
            db.session.commit()
            os.remove(filepath)
        
        return jsonify(success=True, redirectUrl=url_for('quests.manage_game_quests', game_id=game_id))

    return jsonify(success=False, message="Invalid file"), 400


@quests_bp.route('/quest/<int:quest_id>/submissions')
def get_quest_submissions(quest_id):
    submissions = QuestSubmission.query.filter_by(quest_id=quest_id).all()
    submissions_data = [{
        'id': sub.id,
        'image_url': sub.image_url,
        'comment': sub.comment,
        'timestamp': sub.timestamp.strftime('%Y-%m-%d %H:%M'),
        'user_id': sub.user_id,
        'twitter_url': sub.twitter_url,
        'fb_url': sub.fb_url,
        'instagram_url': sub.instagram_url
    } for sub in submissions]
    return jsonify(submissions_data)


@quests_bp.route('/detail/<int:quest_id>/user_completion')
@login_required
def quest_user_completion(quest_id):
    quest = Quest.query.get_or_404(quest_id)
    badge = Badge.query.get(quest.badge_id) if quest.badge_id else None
    user_quest = UserQuest.query.filter_by(user_id=current_user.id, quest_id=quest_id).first()
    can_verify, next_eligible_time = can_complete_quest(current_user.id, quest_id)
    last_relevant_completion_time = getLastRelevantCompletionTime(current_user.id, quest_id)

    badge_info = {
        'id': badge.id,
        'name': badge.name,
        'description': badge.description,
        'image': badge.image
    } if badge else {'name': 'Default', 'image': 'default_badge.png'}

    quest_details = {
        'id': quest.id,
        'title': quest.title,
        'description': quest.description,
        'tips': quest.tips,
        'points': quest.points,
        'completion_limit': quest.completion_limit,
        'badge_awarded': quest.badge_awarded,
        'category': quest.category,
        'frequency': quest.frequency, 
        'enabled': quest.enabled,
        'is_sponsored': quest.is_sponsored,
        'verification_type': quest.verification_type,
        'badge': badge_info,
        'nextEligibleTime': next_eligible_time.isoformat() if next_eligible_time else None
    }

    user_completion_data = {
        'completions': user_quest.completions if user_quest else 0,
        'lastCompletionTimestamp': user_quest.completed_at.isoformat() if user_quest and user_quest.completed_at else None
    }

    response_data = {
        'quest': quest_details,
        'userCompletion': user_completion_data,
        'canVerify': can_verify,
        'nextEligibleTime': next_eligible_time.isoformat() if next_eligible_time else None,
        'lastRelevantCompletionTime': last_relevant_completion_time.isoformat() if last_relevant_completion_time else None
    }

    return jsonify(response_data)


@quests_bp.route('/get_last_relevant_completion_time/<int:quest_id>/<int:user_id>')
@login_required
def get_last_relevant_completion_time(quest_id, user_id):
    last_time = getLastRelevantCompletionTime(user_id, quest_id)
    if last_time:
        return jsonify(success=True, lastRelevantCompletionTime=last_time.isoformat())
    else:
        return jsonify(success=False, message="No relevant completion found")


@quests_bp.route('/generate_qr/<int:quest_id>')
def generate_qr(quest_id):
    quest = Quest.query.get_or_404(quest_id)
    url = url_for('quests.submit_photo', quest_id=quest_id, _external=True)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="white", back_color="black")
    img_buffer = BytesIO()
    img.save(img_buffer, format="PNG")
    img_data = base64.b64encode(img_buffer.getvalue()).decode('utf-8')

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>QR Code - {quest.title}</title>
        <style>
            body {{ text-align: center; padding: 20px; font-family: Arial, sans-serif; }}
            .qrcodeHeader img {{ max-width: 100%; height: auto; }}
            h1, h2 {{ margin: 10px 0; }}
            img {{ margin-top: 20px; }}
            @media print {{
                .no-print {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="qrcodeHeader">
            <img src="{url_for('static', filename='images/welcomeQuestByCycle.webp')}" alt="Welcome">
        </div>
        <h1>Congratulations!</h1>
        <h2>Scan to complete '{quest.title}' and gain {quest.points} points!</h2>
        <img src="data:image/png;base64,{img_data}" alt="QR Code">
        <h2>Quest By Cycle is a free eco-adventure game where players pedal their way to sustainability, earn rewards, and transform communities—all while having fun!</h2>
    </body>
    </html>
    """

    response = make_response(html_content)
    response.headers['Content-Type'] = 'text/html'
    return response


@quests_bp.route('/submit_photo/<int:quest_id>', methods=['GET', 'POST'])
@login_required
def submit_photo(quest_id):
    form = PhotoForm()
    quest = Quest.query.get_or_404(quest_id)
    game = Game.query.get_or_404(quest.game_id)
    game_start = game.start_date
    game_end = game.end_date
    now = datetime.now()

    if not quest.enabled:
        message = 'This quest is not enabled.'
        if request.method == 'POST':
            return jsonify({'success': False, 'message': message}), 400
        flash(message, 'error')
        return redirect(url_for('main.index'))  # Redirect to main index or another page

    if not (game_start <= now <= game_end):
        message = 'This quest cannot be completed outside of the game dates. Join a new game in the game dropdown menu.'
        flash(message, 'error')
        return redirect(url_for('main.index'))  # Redirect to main index or another page

    if request.method == 'POST':
        can_verify, next_eligible_time = can_complete_quest(current_user.id, quest_id)
        if not can_verify:
            message = f'You cannot submit this quest again until {next_eligible_time}.'
            return jsonify({'success': False, 'message': message}), 400

        sid = request.form.get('sid')
        if not sid:
            return jsonify({'success': False, 'message': 'No session ID provided'}), 400

        emit_status('Initializing submission process...', sid)

        photo = request.files.get('photo')
        if photo:
            emit_status('Saving submission image...', sid)
            image_url = save_submission_image(photo)
            image_path = os.path.join(current_app.static_folder, image_url)
            display_name = current_user.display_name or current_user.username
            status = f"{display_name} completed '{quest.title}'! #QuestByCycle"

            twitter_url, fb_url, instagram_url = None, None, None
            if image_url and current_user.upload_to_socials:
                emit_status('Posting to social media...', sid)
                twitter_url, fb_url, instagram_url = post_to_social_media(image_url, image_path, status, game, sid)

            emit_status('Saving submission details...', sid)
            new_submission = QuestSubmission(
                quest_id=quest_id,
                user_id=current_user.id,
                image_url=url_for('static', filename=image_url) if image_url else url_for('static', filename='images/commentPlaceholder.png'),
                twitter_url=twitter_url,
                fb_url=fb_url,
                instagram_url=instagram_url,
                timestamp=datetime.now(),
            )
            db.session.add(new_submission)

            user_quest = UserQuest.query.filter_by(user_id=current_user.id, quest_id=quest_id).first()
            if not user_quest:
                user_quest = UserQuest(
                    user_id=current_user.id,
                    quest_id=quest_id,
                    completions=1,
                    points_awarded=quest.points
                )
                db.session.add(user_quest)
            else:
                user_quest.completions += 1
                user_quest.points_awarded += quest.points

            emit_status('Finalizing submission...', sid)
            db.session.commit()

            update_user_score(current_user.id)
            check_and_award_badges(current_user.id, quest_id, quest.game_id)

            emit_status('Submission complete!', sid)
            try:
                from app import socketio
                socketio.emit('submission_complete', {'status': "Submission Complete"}, room=sid)
            except Exception as e:
                return jsonify({'success': False, 'message': f'Issue submitting verification: {e}'}), 500

            message = 'Photo submitted successfully!'
            return jsonify({'success': True, 'message': message, 'redirect_url': url_for('main.index', game_id=game.id, quest_id=quest_id)}), 200

        else:
            return jsonify({'success': False, 'message': 'No photo detected, please try again.'}), 400

    return render_template('submit_photo.html', form=form, quest=quest, quest_id=quest_id)



def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@quests_bp.errorhandler(RequestEntityTooLarge)
def handle_large_file_error(e):
    return "File too large", 413


@quests_bp.route('/quest/my_submissions', methods=['GET'])
def get_user_submissions():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        submissions = QuestSubmission.query.filter_by(user_id=current_user.id).all()
        submissions_data = [{
            'id': submission.id,
            'image_url': submission.image_url,
            'comment': submission.comment,
            'user_id': submission.user_id,
            'quest_id': submission.quest_id,
            'twitter_url': submission.twitter_url,  # Assume twitter_url is an attribute
            'timestamp': submission.timestamp.isoformat()  # Adjusted to string format for JSON serialization
        } for submission in submissions]
        return jsonify(submissions_data)
    except Exception as e:
        print(f"Error fetching submissions: {e}")
        return jsonify({'error': 'Failed to fetch submissions'}), 500
    

@quests_bp.route('/quest/delete_submission/<int:submission_id>', methods=['DELETE'])
@login_required
def delete_submission(submission_id):
    submission = QuestSubmission.query.get(submission_id)

    # Check if the current user is the admin or the user who created the submission.
    if not current_user.is_admin:
        if not submission.user_id == current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

    if not submission:
        return jsonify({'error': 'Submission not found'}), 404

    # Find the UserQuest entry
    user_quest = UserQuest.query.filter_by(user_id=submission.user_id, quest_id=submission.quest_id).first()

    if user_quest:
        # Decrement completions and update points
        user_quest.completions = max(user_quest.completions - 1, 0)  # Ensure it doesn't go negative
        if user_quest.completions == 0:
            user_quest.points_awarded = 0
        else:
            quest = Quest.query.get(submission.quest_id)
            user_quest.points_awarded = max(user_quest.points_awarded - quest.points, 0)  # Adjust the points accordingly

        # Check if badges need to be revoked
        check_and_revoke_badges(submission.user_id)

        # Commit UserQuest changes
        db.session.commit()

    # Now remove the submission
    db.session.delete(submission)
    db.session.commit()
    return jsonify({'success': True})


@quests_bp.route('/quest/all_submissions', methods=['GET'])
def get_all_submissions():
    game_id = request.args.get('game_id', type=int)

    if game_id is None:
        return jsonify({'error': 'Game ID is required'}), 400
    
    # Join QuestSubmission with Quest and User to get necessary details
    submissions = (
        QuestSubmission.query
        .join(Quest, QuestSubmission.quest_id == Quest.id)
        .join(User, QuestSubmission.user_id == User.id)
        .filter(Quest.game_id == game_id)
        .all()
    )

    if not submissions:
        return jsonify({'submissions': []})

    submissions_data = [
        {
            'id': submission.id,
            'quest_id': submission.quest_id,
            'user_id': submission.user_id,  # Include user_id here
            'user_display_name': submission.user.display_name or submission.user.username,
            'user_username': submission.user.username,  # Fallback username
            'image_url': submission.image_url,
            'comment': submission.comment,
            'timestamp': submission.timestamp.strftime('%Y-%m-%d %H:%M'),  # Format to exclude seconds
            'twitter_url': submission.twitter_url,
            'fb_url': submission.fb_url,
            'instagram_url': submission.instagram_url
        }
        for submission in submissions
    ]

    return jsonify({
        'submissions': submissions_data,
        'is_admin': current_user.is_admin
    })


@quests_bp.route('/quest/<int:quest_id>')
@login_required
def quest_details(quest_id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized'}), 403

    quest = Quest.query.get_or_404(quest_id)
    quest_data = {
        'id': quest.id,
        'title': quest.title,
        'description': quest.description,
        'due_date': quest.due_date.isoformat(),
        'status': quest.status
    }
    return jsonify({'quest': quest_data})

@quests_bp.route('/game/<int:game_id>/delete_all', methods=['DELETE'])
@login_required
def delete_all_quests(game_id):
    game = Game.query.get_or_404(game_id)
    
    if game.admin_id != current_user.id:
        return jsonify({"success": False, "message": "You do not have permission to delete quests for this game."}), 403
    
    try:
        Quest.query.filter_by(game_id=game_id).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({"success": True, "message": "All quests deleted successfully."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Failed to delete all quests: {str(e)}"}), 500
    

@quests_bp.route('/game/<int:game_id>/get_title', methods=['GET'])
@login_required
def get_game_title(game_id):
    game = Game.query.get_or_404(game_id)
    
    if game.admin_id != current_user.id:
        return jsonify({"success": False, "message": "You do not have permission to view this game."}), 403
    
    return jsonify({"title": game.title})
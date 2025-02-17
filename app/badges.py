from flask import Blueprint, current_app, render_template, flash, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from .forms import BadgeForm
from .utils import save_badge_image, allowed_file
from .models import db, Quest, Badge, UserQuest, Game
from werkzeug.utils import secure_filename

import bleach
import os
import csv

badges_bp = Blueprint('badges', __name__, template_folder='templates')

ALLOWED_TAGS = []

ALLOWED_ATTRIBUTES = {}

def sanitize_html(html_content):
    return bleach.clean(html_content, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'csv'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@badges_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_badge():
    if not current_user.is_admin:
        flash('Access denied: Only administrators can manage badges.', 'danger')
        return redirect(url_for('main.index'))

    # Fetch unique categories from Quest model
    quest_categories = db.session.query(Quest.category).filter(Quest.category.isnot(None)).distinct().all()

    # Flatten the categories into a list
    category_choices = sorted([category.category for category in quest_categories])

    form = BadgeForm(category_choices=category_choices)

    if form.validate_on_submit():
        filename = None
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename != '':
                filename = save_badge_image(image_file)
        new_badge = Badge(
            name=sanitize_html(form.name.data),
            description=sanitize_html(form.description.data),
            image=filename,
            category=sanitize_html(form.category.data)
        )
        db.session.add(new_badge)
        db.session.commit()
        flash('Badge created successfully!', 'success')
        return redirect(url_for('badges.list_badges'))
    return render_template('create_badge.html', form=form)


@badges_bp.route('/badges', methods=['GET'])
def get_badges():
    game_id = request.args.get('game_id', type=int)
    if game_id:
        game = Game.query.get(game_id)
        if not game:
            return jsonify(error="Game not found"), 404

        # Filter badges by joining with Quest and filtering by game_id.
        badges = Badge.query.join(Quest).filter(
            Quest.game_id == game_id,
            Quest.badge_id.isnot(None)
        ).distinct().all()
    else:
        badges = Badge.query.all()
    
    badges_data = []
    for badge in badges:
        awarding_quest = (
            next((quest for quest in badge.quests if quest.game_id == game_id), None)
            if game_id else (badge.quests[0] if badge.quests else None)
        )
        
        # Calculate the user's completions for the awarding quest.
        if awarding_quest and current_user.is_authenticated:
            user_quest = UserQuest.query.filter_by(
                user_id=current_user.id,
                quest_id=awarding_quest.id
            ).first()
            user_completions_value = user_quest.completions if user_quest else 0
        else:
            user_completions_value = 0

        badges_data.append({
            'id': badge.id,
            'name': badge.name,
            'description': badge.description,
            'image': url_for('static', filename='images/badge_images/' + badge.image) if badge.image else None,
            'category': badge.category,
            'task_name': awarding_quest.title if awarding_quest else None,
            'task_id': awarding_quest.id if awarding_quest else None,
            'badge_awarded_count': awarding_quest.badge_awarded if awarding_quest else 1,
            'user_completions': user_completions_value
        })

    return jsonify(badges=badges_data)



@badges_bp.route('/badges/manage_badges', methods=['GET', 'POST'])
@login_required
def manage_badges():
    if not current_user.is_admin:
        flash('Access denied: Only administrators can manage badges.', 'danger')
        return redirect(url_for('main.index'))

    # Fetch unique categories from Quest model
    quest_categories = db.session.query(Quest.category).filter(Quest.category.isnot(None)).distinct().all()

    # Flatten the categories into a list
    category_choices = sorted([category.category for category in quest_categories])

    form = BadgeForm(category_choices=category_choices)

    if form.validate_on_submit():
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename != '':
                filename = save_badge_image(image_file)
                new_badge = Badge(
                    name=sanitize_html(form.name.data),
                    description=sanitize_html(form.description.data),
                    image=filename,
                    category=sanitize_html(request.form['category'])
                )
                db.session.add(new_badge)
                db.session.commit()
                flash('Badge added successfully.', 'success')
            else:
                flash('No file selected for upload.', 'error')
        else:
            flash('No file part in the request.', 'error')

        return redirect(url_for('badges.manage_badges'))

    badges = Badge.query.all()
    return render_template('manage_badges.html', form=form, badges=badges)


@badges_bp.route('/update/<int:badge_id>', methods=['POST'])
@login_required
def update_badge(badge_id):
    print(f"Updating badge ID: {badge_id}")

    # Fetch the badge from the database or return 404 if not found
    badge = Badge.query.get_or_404(badge_id)
    print(f"Retrieved Badge: {badge.name}")

    # Fetch unique categories from Quest model
    quest_categories = db.session.query(Quest.category).filter(Quest.category.isnot(None)).distinct().all()

    # Flatten the categories into a list
    category_choices = sorted([category.category for category in quest_categories])

    form = BadgeForm(category_choices=category_choices, formdata=request.form)

    # Debug output for form data
    print("Form Data Received:", request.form)
    if request.files:
        print("Files Received:", request.files)

    # Validate form submission
    if form.validate_on_submit():
        print("Form validation successful.")

        # Update badge properties with sanitized inputs
        badge.name = sanitize_html(form.name.data)
        badge.description = sanitize_html(form.description.data)
        badge.category = sanitize_html(form.category.data)

        # Handle category 'none' as null
        if badge.category == 'none':
            badge.category = None

        # Handle image upload
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file.filename != '':
                badge.image = save_badge_image(image_file)
                print(f"Image saved: {badge.image}")

        # Commit changes to the database
        db.session.commit()
        print("Database commit successful.")
        return jsonify({'success': True, 'message': 'Badge updated successfully'})
    else:
        # Print form errors if validation fails
        print("Form validation failed.")
        print("Errors:", form.errors)

    return jsonify({'success': False, 'message': 'Invalid form data', 'errors': form.errors})


@badges_bp.route('/delete/<int:badge_id>', methods=['DELETE'])
@login_required
def delete_badge(badge_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    badge = Badge.query.get(badge_id)
    if not badge:
        return jsonify({'success': False, 'message': 'Badge not found'}), 404
    try:
        db.session.delete(badge)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Badge deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting badge: {e}'}), 500


@badges_bp.route('/categories', methods=['GET'])
def get_quest_categories():
    # Fetch distinct categories from Quest model
    quest_categories = db.session.query(Quest.category).filter(Quest.category.isnot(None)).distinct().all()
    categories = [category.category for category in quest_categories]
    return jsonify(categories=sorted(categories))


@badges_bp.route('/upload_images', methods=['POST'])
@login_required
def upload_images():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 403

    uploaded_files = request.files.getlist('file')
    images_folder = os.path.join(current_app.root_path, 'static', 'images', 'badge_images')

    if not os.path.exists(images_folder):
        os.makedirs(images_folder)

    for uploaded_file in uploaded_files:
        if uploaded_file and allowed_file(uploaded_file.filename):
            # Extract filename and remove any directory path included by the browser
            filename = secure_filename(uploaded_file.filename.split('/')[-1])
            file_path = os.path.join(images_folder, filename)
            uploaded_file.save(file_path)

            # Convert filename to badge name
            badge_name = ' '.join(word.capitalize() for word in filename.rsplit('.', 1)[0].replace('_', ' ').split())
            badge = Badge.query.filter_by(name=badge_name).first()
            if badge:
                badge.image = filename 
                
                db.session.commit()

    return jsonify({'success': True, 'message': 'Images uploaded successfully'})


@badges_bp.route('/bulk_upload', methods=['POST'])
@login_required
def bulk_upload():
    if not current_user.is_admin:
        flash('Access denied: Only administrators can manage badges.', 'danger')
        return redirect(url_for('main.index'))

    print("bulk_upload function started")

    csv_file = request.files.get('csv_file')
    image_files = request.files.getlist('image_files')

    if csv_file:
        print(f"Received CSV file: {csv_file.filename}")
    else:
        print("No CSV file received")

    if image_files:
        print(f"Number of image files received: {len(image_files)}")
    else:
        print("No image files received")

    if not csv_file or not allowed_file(csv_file.filename):
        flash('Invalid or missing CSV file.', 'danger')
        print("Invalid or missing CSV file")
        return redirect(url_for('badges.manage_badges'))

    # Save images to a dictionary
    image_dict = {}
    for image_file in image_files:
        if allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(current_app.root_path, 'static', 'images', 'badge_images', filename)
            image_file.save(image_path)
            image_dict[filename] = filename
            print(f"Saved image: {filename} to {image_path}")

    # Process CSV
    try:
        csv_data = csv_file.read().decode('utf-8').splitlines()

        # Try with tab delimiter
        csv_reader = csv.DictReader(csv_data, delimiter='\t')
        headers = csv_reader.fieldnames
        print(f"CSV Headers with tab delimiter: {headers}")

        if headers is None or len(headers) == 1:
            # Try with comma delimiter
            csv_reader = csv.DictReader(csv_data, delimiter=',')
            headers = csv_reader.fieldnames
            print(f"CSV Headers with comma delimiter: {headers}")

        if 'badge_name' not in headers or 'badge_description' not in headers:
            raise ValueError("CSV file does not contain required headers: 'badge_name' and 'badge_description'")

        for row in csv_reader:
            print(f"Processing row: {row}")
            badge_name = row['badge_name']
            badge_description = row['badge_description']
            badge_filename = badge_name.lower().replace(' ', '_')
            badge_image = image_dict.get(f"{badge_filename}.png")

            if badge_image:
                new_badge = Badge(name=badge_name, description=badge_description, image=badge_image)
                db.session.add(new_badge)
                print(f"Added badge: {badge_name}")
            else:
                flash(f'Image for badge "{badge_name}" not found.', 'warning')
                print(f'Image for badge "{badge_name}" not found.')

    except Exception as e:
        print(f"Error processing CSV file: {e}")
        flash('Error processing CSV file.', 'danger')
        return redirect(url_for('badges.manage_badges'))

    db.session.commit()
    print("Database commit successful")
    flash('Badges and images uploaded successfully.', 'success')
    return redirect(url_for('badges.manage_badges'))
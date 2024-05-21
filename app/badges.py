from flask import Blueprint, current_app, render_template, flash, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from .forms import BadgeForm
from .utils import save_badge_image, allowed_file
from .models import db, Task, Badge, UserTask, Game
from werkzeug.utils import secure_filename

import os
import csv

badges_bp = Blueprint('badges', __name__, template_folder='templates')

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@badges_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_badge():

    if not current_user.is_admin:
        flash('Access denied: Only administrators can manage badges.', 'danger')
        return redirect(url_for('main.index'))
    
    form = BadgeForm()
    if form.validate_on_submit():
        filename = None
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename != '':
                filename = save_badge_image(image_file)
        new_badge = Badge(name=form.name.data, description=form.description.data, image=filename, category=form.category.data)
        db.session.add(new_badge)
        db.session.commit()
        flash('Badge created successfully!', 'success')
        return redirect(url_for('badges.list_badges'))
    return render_template('create_badge.html', form=form)


@badges_bp.route('/badges', methods=['GET'])
def get_badges():
    badges = Badge.query.all()
    badges_data = [{
        'id': badge.id,
        'name': badge.name,
        'description': badge.description,
        'image': url_for('static', filename=badge.image) if badge.image else None,
        'category': badge.category
    } for badge in badges]
    return jsonify(badges=badges_data)


@badges_bp.route('/badges/manage_badges', methods=['GET', 'POST'])
@login_required
def manage_badges():
    if not current_user.is_admin:
        flash('Access denied: Only administrators can manage badges.', 'danger')
        return redirect(url_for('main.index'))

    form = BadgeForm()
    form.category.choices = [category[0] for category in db.session.query(Task.category.distinct()).all() if category[0]]

    if form.validate_on_submit():
        # Similar to how profile pictures are handled
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file and image_file.filename != '':
                filename = save_badge_image(image_file)  # Your function to save the image and return the filename
                # Assuming save_badge_image saves the file and returns a relative path to be stored in the database
                new_badge = Badge(
                    name=form.name.data,
                    description=form.description.data,
                    image=filename,  # Store the filename or relative path in the database
                    category=request.form['category']
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
    badge = Badge.query.get_or_404(badge_id)
    form = BadgeForm()  # Assuming form setup
    if form.validate_on_submit():
        badge.name = form.name.data
        badge.description = form.description.data
        badge.category = form.category.data
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file.filename != '':
                badge.image = save_badge_image(image_file)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Badge updated successfully'})
    return jsonify({'success': False, 'message': 'Invalid form data'})



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
def get_categories():
    categories = [category[0] for category in Badge.query.with_entities(Badge.category).distinct()]
    return jsonify(categories)


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
                rel_path = os.path.join('images', 'badge_images', filename)
                badge.image = rel_path 
                
                db.session.commit()

    return jsonify({'success': True, 'message': 'Images uploaded successfully'})


@badges_bp.route('/bulk_upload', methods=['POST'])
@login_required
def bulk_upload():
    if not current_user.is_admin:
        flash('Access denied: Only administrators can manage badges.', 'danger')
        return redirect(url_for('main.index'))

    csv_file = request.files.get('csv_file')
    image_files = request.files.getlist('image_files')

    if not csv_file or not allowed_file(csv_file.filename):
        flash('Invalid or missing CSV file.', 'danger')
        return redirect(url_for('badges.manage_badges'))

    # Save images to a dictionary
    image_dict = {}
    for image_file in image_files:
        if allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(current_app.root_path, 'static', 'images', 'badge_images', filename))
            image_dict[filename] = os.path.join('images', 'badge_images', filename)

    # Process CSV
    csv_data = csv_file.read().decode('utf-8').splitlines()
    csv_reader = csv.DictReader(csv_data, delimiter='\t')

    for row in csv_reader:
        badge_name = row['badge_name']
        badge_description = row['badge_description']
        badge_filename = badge_name.lower().replace(' ', '_')
        badge_image = image_dict.get(f"{badge_filename}.png")

        if badge_image:
            new_badge = Badge(name=badge_name, description=badge_description, image=badge_image)
            db.session.add(new_badge)
        else:
            flash(f'Image for badge "{badge_name}" not found.', 'warning')

    db.session.commit()
    flash('Badges and images uploaded successfully.', 'success')
    return redirect(url_for('badges.manage_badges'))
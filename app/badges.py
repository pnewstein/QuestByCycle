from flask import Blueprint, current_app, render_template, flash, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from .forms import BadgeForm
from .utils import save_badge_image
from .models import db, Task, Badge, UserTask, Event
from werkzeug.utils import secure_filename
import csv
import os

badges_bp = Blueprint('badges', __name__, template_folder='templates')


@badges_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_badge():
    form = BadgeForm()
    if form.validate_on_submit():
        filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
        new_badge = Badge(name=form.name.data, description=form.description.data, image=filename)
        db.session.add(new_badge)
        db.session.commit()
        flash('Badge created successfully!', 'success')
        return redirect(url_for('badges.list_badges'))
    return render_template('create_badge.html', form=form)


@badges_bp.route('/badges', methods=['GET'])
def get_badges():
    badges = Badge.query.all()
    badges_data = [{'id': badge.id, 'name': badge.name, 'description': badge.description, 'image': badge.image, 'category': badge.category} for badge in badges]
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


@badges_bp.route('/badges/update/<int:badge_id>', methods=['POST'])
@login_required
def update_badge(badge_id):
    badge = Badge.query.get_or_404(badge_id)
    # Process form data
    badge.name = request.form.get('name')
    badge.description = request.form.get('description')
    # Handle file upload if included
    if 'image' in request.files:
        image_file = request.files['image']
        if image_file.filename:
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            image_file.save(filepath)
            badge.image = filename
    db.session.commit()
    return jsonify({'success': True, 'message': 'Badge updated successfully'})


@badges_bp.route('/badges/delete/<int:badge_id>', methods=['DELETE'])
@login_required
def delete_badge(badge_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    try:
        badge = Badge.query.get_or_404(badge_id)
        db.session.delete(badge)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Badge deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting badge: {str(e)}'}), 500


@badges_bp.route('/event/<int:event_id>/upload_badge_images', methods=['GET', 'POST'])
@login_required
def upload_badge_images(event_id):
    badge_ids = request.args.get('badge_ids', '')
    if request.method == 'POST':
        for badge_id in badge_ids.split(','):
            file = request.files.get(f'badge_image_{badge_id}', None)
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(current_app.config['TASKCSV'], filename)
                file.save(filepath)
                
                badge = Badge.query.get(badge_id)
                if badge:
                    badge.image = filepath
                    db.session.commit()

        flash('Badge images updated successfully', 'success')
        return redirect(url_for('tasks.manage_event_tasks', event_id=event_id))
    
    badge_ids = [int(id_) for id_ in badge_ids.split(',') if id_.isdigit()]
    badges = Badge.query.filter(Badge.id.in_(badge_ids)).all()
    return render_template('upload_badge_images.html', badges=badges, event_id=event_id)


from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from .forms import AdvancedBadgeForm
from .models import db, Task, Badge, UserTask, Event
from werkzeug.utils import secure_filename
import csv
import os

badges_bp = Blueprint('badges', __name__, template_folder='templates')


@badges_bp.route('/create_badge', methods=['GET', 'POST'])
@login_required
def create_badge():
    form = AdvancedBadgeForm()
    if form.validate_on_submit():
        # Implement badge creation logic
        flash('Badge created successfully!', 'success')
        return redirect(url_for('badges_bp.manage_badges'))
    return render_template('create_badge.html', form=form)
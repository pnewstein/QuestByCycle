from flask_wtf import FlaskForm
from flask import current_app
from wtforms import StringField, SelectField, SubmitField, IntegerField, PasswordField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, NumberRange, EqualTo, Optional, Email, Length
from wtforms.fields import DateField
from flask_wtf.file import FileField, FileAllowed, FileRequired
from app.models import Badge, VerificationType

import os

class CSRFProtectForm(FlaskForm):
    # Used only for CSRF protection
    pass

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')


class LogoutForm(FlaskForm):
    submit = SubmitField('Logout')


class AddUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Add User')


class EventForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired()])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])  # Use DateField
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[DataRequired()])  # Use DateField
    submit = SubmitField('Create Event')


class TaskForm(FlaskForm):
    enabled = BooleanField('Enabled', default=True)
    category = StringField('Category', validators=[Optional()])
    verification_type = SelectField('Verification Type', choices=[(choice.name, choice.value) for choice in VerificationType], validators=[Optional()])
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    tips = TextAreaField('Tips', validators=[])
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=1)], default=1)  # Assuming tasks have at least 1 point
    completion_limit = IntegerField('Completion Limit', validators=[DataRequired(), NumberRange(min=1)], default=1)
    badge_id = SelectField('Badge', coerce=int, choices=[])
    badge_name = StringField('Badge Name', validators=[])
    badge_description = TextAreaField('Badge Description', validators=[])    
    default_badge_image = SelectField('Select Default Badge Image', coerce=str, choices=[], default='')
    badge_image_filename = FileField('Badge Image', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    submit = SubmitField('Create Task')

    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        self.badge_id.choices = [(0, 'None')] + [(badge.id, badge.name) for badge in Badge.query.all()]
        badge_image_directory = os.path.join(current_app.root_path, 'static/images/default_badges')
        self.default_badge_image.choices = [('','None')] + [(filename, filename) for filename in os.listdir(badge_image_directory)]


class TaskImportForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    tips = TextAreaField('Tips', validators=[])
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=1)], default=1)  # Assuming tasks have at least 1 point
    completion_limit = IntegerField('Completion Limit', validators=[DataRequired(), NumberRange(min=1)], default=1)
    badge_id = SelectField('Select Existing Badge', coerce=int, choices=[], default=0)
    badge_name = StringField('Badge Name', validators=[DataRequired()])
    badge_description = TextAreaField('Badge Description', validators=[DataRequired()])    
    default_badge_image = SelectField('Select Default Badge Image', coerce=str, choices=[], default='')
    badge_image_filename = FileField('Badge Image', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    submit = SubmitField('Add Task')

    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        self.badge_id.choices = [(0, 'None')] + [(b.id, b.name) for b in Badge.query.order_by('name')]
        badge_image_directory = os.path.join(current_app.root_path, 'static/images/default_badges')
        self.default_badge_image.choices = [('','None')] + [(filename, filename) for filename in os.listdir(badge_image_directory)]


class ProfileForm(FlaskForm):
    display_name = StringField('Display Name', validators=[Optional()])
    profile_picture = FileField('Profile Picture', validators=[FileRequired(), FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    age_group = SelectField('Age Group', choices=[('teen', 'Teen'), ('adult', 'Adult'), ('senior', 'Senior')])
    interests = StringField('Interests', validators=[Optional()])
    submit = SubmitField('Update Profile')


class TaskSubmissionForm(FlaskForm):
    evidence = FileField('Upload Evidence', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png', 'pdf'], 'Images and PDFs only!')
    ])
    submit = SubmitField('Submit Task')


class ShoutBoardForm(FlaskForm):
    message = TextAreaField('Message', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Post')


class BadgeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = StringField('Description')
    image = FileField('Badge Image', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    submit = SubmitField('Submit')


class TaskImportForm(FlaskForm):
    csv_file = FileField('CSV File', validators=[DataRequired(), FileAllowed(['csv'], 'CSV files only!')])
    submit = SubmitField('Import Tasks')
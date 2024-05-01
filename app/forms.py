from flask_wtf import FlaskForm
from flask import current_app
from wtforms import StringField, SelectField, SubmitField, IntegerField, PasswordField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, NumberRange, EqualTo, Optional, Email, Length
from wtforms.fields import DateField
from flask_wtf.file import FileField, FileAllowed, FileRequired
from app.models import Badge, Task

import os

class CSRFProtectForm(FlaskForm):
    # Used only for CSRF protection
    pass

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me', default=True)
    submit = SubmitField('Log In')


class LogoutForm(FlaskForm):
    submit = SubmitField('Logout')


class AddUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Add User')


class GameForm(FlaskForm):
    title = StringField('Game Title', validators=[DataRequired()])
    description = StringField('Game Description', validators=[DataRequired(), Length(max=1000)])
    description2 = StringField('Task Rules', validators=[DataRequired(), Length(max=1000)])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])  # Use DateField
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[DataRequired()])  # Use DateField
    details = TextAreaField('Game Details')
    awards = TextAreaField('Awards Details')
    beyond = TextAreaField('Sustainability Details')
    game_goal = IntegerField('Game Goal')  # Add a default value or make it required
    twitter_api_key = StringField('Twitter API Key')
    twitter_api_secret = StringField('Twitter API Secret')
    twitter_access_token = StringField('Twitter Access Token')
    twitter_access_token_secret = StringField('Twitter Access Token Secret')
    facebook_app_id = StringField('Facebook App ID')
    facebook_app_secret = StringField('Facebook App Secret')
    instagram_page_id = StringField('Instagram Page ID')
    submit = SubmitField('Create Game')


class TaskForm(FlaskForm):
    enabled = BooleanField('Enabled', default=True)
    category_choices = [('Environment', 'Environment'), ('Community', 'Community')]  # Example categories
    category = SelectField('Category', choices=category_choices, validators=[DataRequired()])
    verification_type_choices = [
        ('qr_code', 'QR Code'),
        ('photo', 'Photo Upload'),
        ('comment', 'Comment'),
        ('photo_comment', 'Photo Upload and Comment')
    ]
    verification_type = SelectField('Verification Type', choices=verification_type_choices, coerce=str, validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    tips = TextAreaField('Tips', validators=[Optional()])
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=1)], default=1)  # Assuming tasks have at least 1 point
    completion_limit = IntegerField('Completion Limit', validators=[DataRequired(), NumberRange(min=1)], default=1)
    frequency = SelectField('Frequency', choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')], validators=[DataRequired()])
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
        if not os.path.exists(badge_image_directory):
            os.makedirs(badge_image_directory)  # Create the directory if it does not exist
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
    display_name = StringField('Player/Team Name', validators=[Optional()])
    profile_picture = FileField('Profile Picture', validators=[FileRequired(), FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    age_group = SelectField('Age Group', choices=[('teen', 'Teen'), ('adult', 'Adult'), ('senior', 'Senior')])
    interests = StringField('Interests', validators=[Optional()])
    submit = SubmitField('Update Profile')


class TaskSubmissionForm(FlaskForm):
    evidence = FileField('Upload Evidence', validators=[FileRequired(), FileAllowed(['jpg', 'png', 'pdf'], 'Images and PDFs only!')])
    comment = TextAreaField('Comment')  # Assuming you might also want to submit a comment
    submit = SubmitField('Submit Task')


class PhotoForm(FlaskForm):
    photo = FileField(validators=[DataRequired()])
    

class ShoutBoardForm(FlaskForm):
    message = TextAreaField('Message', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Post')



class BadgeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=255)])
    description = TextAreaField('Description', validators=[Length(max=500)])
    image = FileField('Badge Image', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    category = SelectField('Category', choices=[], coerce=str, validators=[Optional()])
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super(BadgeForm, self).__init__(*args, **kwargs)
        self.category.choices = [('','Select a Category')] + list(set([(task.category, task.category) for task in Task.query.filter(Task.category != None)]))


class TaskImportForm(FlaskForm):
    csv_file = FileField('CSV File', validators=[DataRequired(), FileAllowed(['csv'], 'CSV files only!')])
    submit = SubmitField('Import Tasks')
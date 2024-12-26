from flask_wtf import FlaskForm
from flask import current_app
from wtforms import StringField, SelectField, SubmitField, IntegerField, HiddenField, PasswordField, TextAreaField, BooleanField, SelectMultipleField, FieldList, FormField
from wtforms.validators import DataRequired, NumberRange, EqualTo, Optional, Email, Length, ValidationError, URL
from wtforms.fields import DateField
from flask_wtf.file import FileField, FileAllowed
from app.models import Badge

import os

class CSRFProtectForm(FlaskForm):
    # Used only for CSRF protection
    pass


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    accept_license = BooleanField('I agree to the ', validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_accept_license(form, field):
        if not field.data:
            raise ValidationError('You must agree to the terms of service, license agreement, and privacy policy to register.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me', default=True)
    submit = SubmitField('Sign In')


class LogoutForm(FlaskForm):
    submit = SubmitField('Logout')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')


class UpdatePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Update Password')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')


class AddUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Add User')

class DeleteUserForm(FlaskForm):
    submit = SubmitField('Delete Account')

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
    leaderboard_image = FileField('Leaderboard Background Image (height: 400px; .png only)', validators=[FileAllowed(['png'], 'Images only!')])  # 
    twitter_username = StringField('Twitter Username')
    twitter_api_key = StringField('Twitter API Key')
    twitter_api_secret = StringField('Twitter API Secret')
    twitter_access_token = StringField('Twitter Access Token')
    twitter_access_token_secret = StringField('Twitter Access Token Secret')
    facebook_app_id = StringField('Facebook App ID')
    facebook_app_secret = StringField('Facebook App Secret')
    facebook_access_token = StringField('Facebook Access Token')
    facebook_page_id = StringField('Facebook Page ID')
    instagram_user_id = StringField('Instagram User ID', validators=[Optional()])
    instagram_access_token = StringField('Instagram Access Token', validators=[Optional()])
    custom_game_code = StringField('Custom Game Code', validators=[Optional()])  # New field for custom game code
    is_public = BooleanField('Public Game', default=True)  # New field for public game indicator
    allow_joins = BooleanField('Allow Joining', default=True)  # New field for allowing new users to join
    submit = SubmitField('Create Game')



class TaskForm(FlaskForm):
    enabled = BooleanField('Enabled', default=True)
    is_sponsored = BooleanField('Is Sponsored', default=False)
    category = StringField('Category', validators=[DataRequired()])
    verification_type_choices = [
        ('qr_code', 'QR Code'),
        ('photo', 'Photo Upload'),
        ('comment', 'Comment'),
        ('photo_comment', 'Photo Upload and Comment'),
        ('pause', 'Pause')
    ]
    verification_type = SelectField('Submission Requirements', choices=verification_type_choices, coerce=str, validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    tips = TextAreaField('Tips', validators=[Optional()])
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=1)], default=1)  # Assuming tasks have at least 1 point
    completion_limit = IntegerField('Completion Limit', validators=[DataRequired(), NumberRange(min=1)], default=1)
    frequency = SelectField('Frequency', choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')], validators=[DataRequired()])
    badge_id = SelectField('Badge', coerce=int, choices=[], validators=[Optional()])
    badge_name = StringField('Badge Name', validators=[Optional()])
    badge_description = TextAreaField('Badge Description', validators=[Optional()])
    badge_image_filename = FileField('Badge Image', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    default_badge_image = SelectField('Select Default Badge Image', coerce=str, choices=[], default='')
    game_id = HiddenField('Game ID', validators=[DataRequired()])
    submit = SubmitField('Create Task')

    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        self.badge_id.choices = [(0, 'None')] + [(badge.id, badge.name) for badge in Badge.query.all()]
        badge_image_directory = os.path.join(current_app.root_path, 'static/images/badge_images')
        if not os.path.exists(badge_image_directory):
            os.makedirs(badge_image_directory)  # Create the directory if it does not exist
        self.default_badge_image.choices = [('','None')] + [(filename, filename) for filename in os.listdir(badge_image_directory)]
    def validate_completion_limit(form, field):
        valid_completion_limits = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}
        if field.data not in valid_completion_limits:
            field.data = 1

class TaskImportForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    tips = TextAreaField('Tips', validators=[])
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=1)], default=1)  # Assuming tasks have at least 1 point
    completion_limit = IntegerField('Completion Limit', validators=[DataRequired(), NumberRange(min=1)], default=1)
    frequency = SelectField('Frequency', choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')], validators=[DataRequired()])
    verification_type_choices = [
        ('qr_code', 'QR Code'),
        ('photo', 'Photo Upload'),
        ('comment', 'Comment'),
        ('photo_comment', 'Photo Upload and Comment'),
        ('pause', 'Pause')
    ]
    verification_type = SelectField('Submission Requirements', choices=verification_type_choices, coerce=str, validators=[DataRequired()])
    badge_id = SelectField('Select Existing Badge', coerce=int, choices=[], default=0)
    badge_name = StringField('Badge Name', validators=[DataRequired()])
    badge_description = TextAreaField('Badge Description', validators=[DataRequired()])    
    default_badge_image = SelectField('Select Default Badge Image', coerce=str, choices=[], default='')
    badge_image_filename = FileField('Badge Image', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    submit = SubmitField('Add Task')

    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        self.badge_id.choices = [(0, 'None')] + [(b.id, b.name) for b in Badge.query.order_by('name')]
        badge_image_directory = os.path.join(current_app.root_path, 'static/images/badge_images')
        self.default_badge_image.choices = [('','None')] + [(filename, filename) for filename in os.listdir(badge_image_directory)]



class RidingPreferenceForm(FlaskForm):
    preference = BooleanField(label='')  # Placeholder for the label; it will be set dynamically

class ProfileForm(FlaskForm):
    display_name = StringField('Player/Team Name', validators=[Optional()])
    profile_picture = FileField('Profile Picture', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    age_group = SelectField('Age Group', choices=[('teen', 'Teen'), ('adult', 'Adult'), ('senior', 'Senior')])
    interests = StringField('Interests', validators=[Optional()])
    ride_description = StringField('Describe the type of riding you like to do:', validators=[Optional(), Length(max=500)])
    upload_to_socials = BooleanField('Upload Activities to Social Media', default=True)
    show_carbon_game = BooleanField('Show Carbon Reduction Game', default=True)

    # Add riding preferences as a FieldList
    # Use FieldList and SelectMultipleField for multiple choices
    riding_preferences = SelectMultipleField('Riding Preferences', choices=[
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
    ], validators=[Optional()])

    submit = SubmitField('Update Profile')

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)

class BikeForm(FlaskForm):
    bike_picture = FileField('Upload Your Bicycle Picture', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    bike_description = StringField('Bicycle Description', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Update Bike')


class TaskSubmissionForm(FlaskForm):
    evidence = FileField('Upload Evidence', validators=[FileAllowed(['jpg', 'jpeg,' 'png'], 'Images only!')])
    comment = TextAreaField('Comment')  # Assuming you might also want to submit a comment
    submit = SubmitField('Submit Task')


class PhotoForm(FlaskForm):
    photo = FileField(validators=[DataRequired()])
    

class ShoutBoardForm(FlaskForm):
    message = TextAreaField('Message', validators=[DataRequired(), Length(max=500)])
    game_id = HiddenField('Game ID', validators=[DataRequired()])  # Add this field
    submit = SubmitField('Post')


class BadgeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired()])
    category = SelectField('Category', choices=[], validators=[Optional()])
    image = FileField('Badge Image', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    submit = SubmitField('Submit')

    def __init__(self, category_choices=None, *args, **kwargs):
        # Default category choices to an empty list if None is passed
        if category_choices is None:
            category_choices = []

        # Ensure the correct parent class initialization
        super().__init__(*args, **kwargs)

        # Assign valid choices to the category field, including 'None' as the first option
        self.category.choices = [('none', 'None')] + [(choice, choice) for choice in category_choices]


class TaskImportForm(FlaskForm):
    csv_file = FileField('CSV File', validators=[DataRequired(), FileAllowed(['csv'], 'CSV files only!')])
    submit = SubmitField('Import Tasks')

class ContactForm(FlaskForm):
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send')

class SponsorForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    website = StringField('Website', validators=[Optional(), URL(message='Invalid URL format')])
    logo = FileField('Upload Logo', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    description = TextAreaField('Description', validators=[Optional()])
    tier = SelectField('Tier', choices=[('Gold', 'Gold'), ('Silver', 'Silver'), ('Bronze', 'Bronze')], validators=[DataRequired()])
    game_id = HiddenField('Game ID', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def __init__(self, *args, **kwargs):
        super(SponsorForm, self).__init__(*args, **kwargs)

class CarouselImportForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])

class PlayerMessageBoardForm(FlaskForm):
    content = TextAreaField('Message', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Post')

class ProfileWallMessageForm(FlaskForm):
    content = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Post')

from flask_wtf import FlaskForm
from wtforms import RadioField, StringField, SelectField, SubmitField, IntegerField, PasswordField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, NumberRange, EqualTo, Optional, Email
from wtforms.fields import DateField
from flask_wtf.file import FileField, FileAllowed, FileRequired

class CSRFProtectForm(FlaskForm):
    # Used only for CSRF protection
    pass

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')


class SignInForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()], render_kw={'readonly': True})
    class_selected = RadioField('Class', coerce=str, validators=[DataRequired()], choices=[])
    sign_in_comment = TextAreaField('Sign In Comment', validators=[Optional()])

    def __init__(self, *args, **kwargs):
        super(SignInForm, self).__init__(*args, **kwargs)
        self.class_selected.choices = []  # Initialize with empty list


class SignOutForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    comment = StringField('Comment')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


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
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    points = IntegerField('Points', validators=[DataRequired(), NumberRange(min=1)], default=1)  # Assuming tasks have at least 1 point
    submit = SubmitField('Add Task')


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

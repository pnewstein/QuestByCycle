from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from enum import Enum
from sqlalchemy import Enum as SQLAlchemyEnum

db = SQLAlchemy()


class VerificationType(Enum):
    NOT_APPLICABLE = "Not Applicable",
    QR_CODE = "QR Code"
    PHOTO_UPLOAD = "Photo Upload"
    DESTRUCTION_PHOTO = ""
    SELFIE = "Selfie"
    SCREENSHOT = "Screenshot"
    COMMENT = "Comment"
    PHOTO_COMMENT = "Photo Upload and Comment"
    MANUAL_REVIEW = "Manual Review"
    YOUTUBE_URL = "Youtube URL"
    URL = "URL"


class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(150), nullable=True)
    image = db.Column(db.String(500), nullable=True)
    tasks = db.relationship('Task', backref='badge', lazy=True)

user_badges = db.Table('user_badges',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('badge_id', db.Integer, db.ForeignKey('badge.id'), primary_key=True)
)

user_events = db.Table('user_events',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True)
)

class UserTask(db.Model):
    __tablename__ = 'user_tasks'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), primary_key=True)
    completed = db.Column(db.Boolean, default=False)
    completions = db.Column(db.Integer, default=0)  # Track number of completions
    points_awarded = db.Column(db.Integer, default=0)  # Points awarded for the task

    # Ensure user-task uniqueness
    __table_args__ = (db.UniqueConstraint('user_id', 'task_id', name='_user_task_uc'),)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(512))
    is_admin = db.Column(db.Boolean, default=False)
    user_tasks = db.relationship('UserTask', backref='user', lazy='dynamic')
    badges = db.relationship('Badge', secondary=user_badges, lazy='subquery',
        backref=db.backref('users', lazy=True))
    score = db.Column(db.Integer, default=0)
    participated_events = db.relationship('Event', secondary='user_events', lazy='subquery',
                                        backref=db.backref('event_participants', lazy=True))
    display_name = db.Column(db.String(100))
    profile_picture = db.Column(db.String(200))  # Could be a URL or a path
    age_group = db.Column(db.String(50))
    interests = db.Column(db.String(500))  # This could be a comma-separated list or a many-to-many relationship with another table

    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140))
    description = db.Column(db.String(500))
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    evidence_url = db.Column(db.String(500))
    enabled = db.Column(db.Boolean, default=True)
    verification_type = db.Column(SQLAlchemyEnum(VerificationType))
    verification_comment = db.Column(db.String(500), default="")
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))  # Make sure this line is within the class definition
    points = db.Column(db.Integer, default='')
    tips = db.Column(db.String(500), default='')
    completion_limit = db.Column(db.Integer, default=1)  # Limit for how many times a task can be completed
    user_tasks = db.relationship('UserTask', backref='task', lazy='dynamic')
    category = db.Column(db.String(50), nullable=True)
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'), nullable=True)  # Foreign key to Badge
    badge = db.relationship('Badge', back_populates='tasks', uselist=False)

Badge.tasks = db.relationship('Task', order_by=Task.id, back_populates='badge')


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    description = db.Column(db.String(500))
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tasks = db.relationship('Task', backref='event', lazy='dynamic')
    participants = db.relationship('User', secondary='event_participants', lazy='subquery',
                                   backref=db.backref('events', lazy=True))

event_participants = db.Table('event_participants',
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class ShoutBoardMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    
    user = db.relationship('User', backref='shoutboard_messages')
    
    likes = db.relationship('ShoutBoardLike', backref='message', lazy='dynamic')

class ShoutBoardLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('shout_board_message.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('message_id', 'user_id', name='_message_user_uc'),)
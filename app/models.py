from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    description = db.Column(db.String(150))
    # Additional fields like badge image URL

user_badges = db.Table('user_badges',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('badge_id', db.Integer, db.ForeignKey('badge.id'), primary_key=True)
)

user_events = db.Table('user_events',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True)
)

user_tasks = db.Table('user_tasks',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('task_id', db.Integer, db.ForeignKey('task.id'), primary_key=True),
    db.Column('completed', db.Boolean, default=False),
    db.Column('points_awarded', db.Integer)
)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    tasks = db.relationship('Task', secondary=user_tasks, backref=db.backref('users', lazy='dynamic'))
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
    verified = db.Column(db.Boolean, default=False)
    verification_comment = db.Column(db.String(500), default="")
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'))  # Make sure this line is within the class definition
    points = db.Column(db.Integer, default=1)

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
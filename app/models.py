from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy.orm import relationship
from sqlalchemy import Enum as SQLAlchemyEnum

db = SQLAlchemy()

class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    image = db.Column(db.String(500), nullable=True)
    tasks = db.relationship('Task', backref='badge', lazy=True)
    category = db.Column(db.String(150), nullable=True) 
    
user_badges = db.Table('user_badges',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('badge_id', db.Integer, db.ForeignKey('badge.id'), primary_key=True)
)

user_games = db.Table('user_games',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('game_id', db.Integer, db.ForeignKey('game.id'), primary_key=True)
)

class UserTask(db.Model):
    __tablename__ = 'user_tasks'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True, nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id', ondelete='CASCADE'), primary_key=True, nullable=False)
    completions = db.Column(db.Integer, default=0)  # Track number of completions
    points_awarded = db.Column(db.Integer, default=0)  # Points awarded for the task
    completed_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    task = db.relationship("Task", back_populates="user_tasks")

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
    participated_games = db.relationship('Game', secondary='user_games', lazy='subquery',
                                        backref=db.backref('game_participants', lazy=True))
    display_name = db.Column(db.String(100))
    profile_picture = db.Column(db.String(200))  # Could be a URL or a path
    age_group = db.Column(db.String(50))
    interests = db.Column(db.String(500))  # This could be a comma-separated list or a many-to-many relationship with another table
    task_likes = db.relationship('TaskLike', backref='user', lazy='dynamic')

    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_already_liking(self, task):
        return TaskLike.query.filter_by(user_id=self.id, task_id=task.id).count() > 0

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140))
    description = db.Column(db.String(750))
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    evidence_url = db.Column(db.String(500))
    enabled = db.Column(db.Boolean, default=True)
    verification_type = db.Column(db.String(50))  # Changed from SQLAlchemyEnum to String
    verification_comment = db.Column(db.String(1000), default="")
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))  # Make sure this line is within the class definition
    points = db.Column(db.Integer, default='')
    tips = db.Column(db.String(1000), default='', nullable=True)
    completion_limit = db.Column(db.Integer, default=1)  # Limit for how many times a task can be completed
    frequency = db.Column(db.String(50), nullable=True)  # Store frequency as a string
    user_tasks = db.relationship('UserTask', back_populates='task', cascade="all, delete", passive_deletes=True)
    category = db.Column(db.String(50), nullable=True)
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'), nullable=True)  # Foreign key to Badge
    badge = db.relationship('Badge', back_populates='tasks')
    submissions = db.relationship('TaskSubmission', back_populates='task', cascade='all, delete-orphan')
    likes = db.relationship('TaskLike', backref='task', lazy='dynamic')

Badge.tasks = db.relationship('Task', order_by=Task.id, back_populates='badge')


class TaskLike(db.Model):
    __tablename__ = 'task_likes'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('task_id', 'user_id', name='_task_user_uc'),)


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    description = db.Column(db.String(1000))
    description2 = db.Column(db.String(1000))
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    end_date = db.Column(db.DateTime, nullable=False, default=datetime.now(timezone.utc))
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tasks = db.relationship('Task', backref='game', lazy='dynamic')
    participants = db.relationship('User', secondary='game_participants', lazy='subquery', backref=db.backref('games', lazy=True))
    game_goal = db.Column(db.Integer)
    details = db.Column(db.Text)  # New field for detailed game information
    awards = db.Column(db.Text)  # Information about awards
    beyond = db.Column(db.Text)  # Information on living a sustainable bicycle lifestyle
    
    # Twitter credentials
    twitter_api_key = db.Column(db.String(500), nullable=True)
    twitter_api_secret = db.Column(db.String(500), nullable=True)
    twitter_access_token = db.Column(db.String(500), nullable=True)
    twitter_access_token_secret = db.Column(db.String(500), nullable=True)

    facebook_app_id = db.Column(db.String(500), nullable=True)
    facebook_app_secret = db.Column(db.String(500), nullable=True)
    instagram_page_id = db.Column(db.String(500), nullable=True)
    
game_participants = db.Table('game_participants',
    db.Column('game_id', db.Integer, db.ForeignKey('game.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class ShoutBoardMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now(timezone.utc))
    
    user = db.relationship('User', backref='shoutboard_messages')
    likes = db.relationship('ShoutBoardLike', backref='message', lazy='dynamic')

class ShoutBoardLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('shout_board_message.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('message_id', 'user_id', name='_message_user_uc'),)


class TaskSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    comment = db.Column(db.String(1000), nullable=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.now(timezone.utc))

    task = db.relationship('Task', back_populates='submissions')
    user = db.relationship('User', backref='task_submissions')
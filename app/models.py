from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from time import time
from pytz import utc
from sqlalchemy.exc import IntegrityError

import jwt
import random
import string

db = SQLAlchemy()

class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    image = db.Column(db.String(500), nullable=True)
    category = db.Column(db.String(150), nullable=True) 

    quests = db.relationship('Quest', backref='badge', lazy=True)
    
user_badges = db.Table('user_badges',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('badge_id', db.Integer, db.ForeignKey('badge.id'), primary_key=True)
)

user_games = db.Table('user_games',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('game_id', db.Integer, db.ForeignKey('game.id'), primary_key=True),
    db.Column('joined_at', db.DateTime, default=datetime.now(utc))
)

class UserQuest(db.Model):
    __tablename__ = 'user_quests'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True, nullable=False)
    quest_id = db.Column(db.Integer, db.ForeignKey('quest.id', ondelete='CASCADE'), primary_key=True, nullable=False)
    completions = db.Column(db.Integer, default=0)  # Track number of completions
    points_awarded = db.Column(db.Integer, default=0)  # Points awarded for the quest
    completed_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(utc))  # Use timezone-aware datetime
    quest = db.relationship("Quest", back_populates="user_quests")

    def __init__(self, **kwargs):
        super(UserQuest, self).__init__(**kwargs)  # Initialize all fields from passed keyword arguments

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(512))
    is_admin = db.Column(db.Boolean, default=False)
    is_super_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now())
    license_agreed = db.Column(db.Boolean, nullable=False)
    user_quests = db.relationship('UserQuest', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    badges = db.relationship('Badge', secondary=user_badges, lazy='subquery',
                             backref=db.backref('users', lazy=True))
    score = db.Column(db.Integer, default=0)
    participated_games = db.relationship('Game', secondary='user_games', lazy='subquery', backref=db.backref('game_participants', lazy=True))
    display_name = db.Column(db.String(100))
    profile_picture = db.Column(db.String(200))
    age_group = db.Column(db.String(50))
    interests = db.Column(db.String(500))
    quest_likes = db.relationship('QuestLike', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    email_verified = db.Column(db.Boolean, default=False)
    shoutboard_messages = db.relationship('ShoutBoardMessage', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    quest_submissions = db.relationship('QuestSubmission', backref='submitter', lazy='dynamic', cascade='all, delete-orphan')

    # New fields for riding preferences and toggles
    riding_preferences = db.Column(db.ARRAY(db.String), nullable=True)  # Use ARRAY if using Postgres, or JSON for other databases
    ride_description = db.Column(db.String(500), nullable=True)  # Description for type of riding
    bike_picture = db.Column(db.String(200), nullable=True)  # Bike picture URL
    bike_description = db.Column(db.String(500), nullable=True)  # Description of the bicycle
    upload_to_socials = db.Column(db.Boolean, default=True)  # Toggle for auto-uploading to socials
    show_carbon_game = db.Column(db.Boolean, default=True)  # Toggle for showing carbon reduction game
    onboarded = db.Column(db.Boolean, default=False, nullable=True)  # New field to track onboarding status

    selected_game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=True)

    def generate_verification_token(self, expiration=320000):
        return jwt.encode(
            {'verify_email': self.id, 'exp': time() + expiration},
            current_app.config['SECRET_KEY'], algorithm='HS256'
        )

    @staticmethod
    def verify_verification_token(token, expiration=320000):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])['verify_email']
        except:
            return None
        return User.query.get(id)

    def generate_reset_token(self, expiration=320000):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expiration},
            current_app.config['SECRET_KEY'], algorithm='HS256'
        )

    @staticmethod
    def verify_reset_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])['reset_password']
        except:
            return None
        return User.query.get(id)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_already_liking(self, quest):
        return QuestLike.query.filter_by(user_id=self.id, quest_id=quest.id).count() > 0
    
    def get_participated_games(self):
        return [{'id': game.id, 'title': game.title} for game in self.participated_games]
        
    def delete_user(self):
        # Delete ProfileWallMessages where the user is the author or recipient
        ProfileWallMessage.query.filter_by(author_id=self.id).delete(synchronize_session=False)
        ProfileWallMessage.query.filter_by(user_id=self.id).delete(synchronize_session=False)

        # Delete related UserQuests
        for user_quest in self.user_quests:
            db.session.delete(user_quest)

        # Delete related QuestLikes
        for quest_like in self.quest_likes:
            db.session.delete(quest_like)

        # Delete related ShoutBoardMessages
        for message in self.shoutboard_messages:
            db.session.delete(message)

        # Delete related QuestSubmissions
        for submission in self.quest_submissions:
            db.session.delete(submission)

        # Remove user from games
        self.participated_games.clear()

        # Delete the user
        db.session.delete(self)
        db.session.commit()

    def get_score_for_game(self, game_id):
        """
        Retrieve the user's total score for a specific game.
        This method calculates the sum of points awarded for all quests 
        completed by the user within the specified game.
        """
        # Sum up the points from UserQuest entries for quests within the specified game
        total_score = db.session.query(
            db.func.sum(UserQuest.points_awarded)
        ).join(Quest, UserQuest.quest_id == Quest.id
        ).filter(
            UserQuest.user_id == self.id,
            Quest.game_id == game_id
        ).scalar() or 0  # Default to 0 if no score is found

        return total_score
        
class UserIP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ip_address = db.Column(db.String(45), nullable=False)  # IPv4 and IPv6 support
    timestamp = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref='ip_addresses')

class Quest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140))
    description = db.Column(db.String(2000))
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    evidence_url = db.Column(db.String(500))
    enabled = db.Column(db.Boolean, default=True)
    is_sponsored = db.Column(db.Boolean, default=False, nullable=False)
    verification_type = db.Column(db.String(50))
    verification_comment = db.Column(db.String(1000), default="")
    game_id = db.Column(db.Integer, db.ForeignKey('game.id', ondelete='CASCADE'))
    game = db.relationship('Game', back_populates='quests')
    points = db.Column(db.Integer, default=0)
    tips = db.Column(db.String(2000), default='', nullable=True)
    completion_limit = db.Column(db.Integer, default=1)
    frequency = db.Column(db.String(50), nullable=True)
    user_quests = db.relationship('UserQuest', back_populates='quest', cascade="all, delete", passive_deletes=True)
    category = db.Column(db.String(50), nullable=True)
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'), nullable=True)
    submissions = db.relationship('QuestSubmission', back_populates='quest', cascade='all, delete-orphan')
    likes = db.relationship('QuestLike', backref='quest', cascade="all, delete-orphan")
    badge_awarded = db.Column(db.Integer, default=1)

    def __repr__(self):
        return f'<Quest {self.id}>'
    
class QuestLike(db.Model):
    __tablename__ = 'quest_likes'
    id = db.Column(db.Integer, primary_key=True)
    quest_id = db.Column(db.Integer, db.ForeignKey('quest.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (db.UniqueConstraint('quest_id', 'user_id', name='_quest_user_uc'),)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    description = db.Column(db.String(1000))
    description2 = db.Column(db.String(1000))
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.now())
    end_date = db.Column(db.DateTime, nullable=False, default=datetime.now())
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quests = db.relationship('Quest', back_populates='game', cascade="all, delete-orphan", lazy='dynamic')
    participants = db.relationship('User', secondary='game_participants', lazy='subquery', backref=db.backref('games', lazy=True))
    game_goal = db.Column(db.Integer)
    details = db.Column(db.Text)
    awards = db.Column(db.Text)
    beyond = db.Column(db.Text)
    sponsors = db.relationship('Sponsor', back_populates='game', cascade='all, delete-orphan')
    leaderboard_image = db.Column(db.String(500), nullable=True)  # New field for leaderboard image

    twitter_username = db.Column(db.String(500), nullable=True)
    twitter_api_key = db.Column(db.String(500), nullable=True)
    twitter_api_secret = db.Column(db.String(500), nullable=True)
    twitter_access_token = db.Column(db.String(500), nullable=True)
    twitter_access_token_secret = db.Column(db.String(500), nullable=True)

    facebook_app_id = db.Column(db.String(500), nullable=True)
    facebook_app_secret = db.Column(db.String(500), nullable=True)
    facebook_access_token = db.Column(db.String(500), nullable=True)
    facebook_page_id = db.Column(db.String(500), nullable=True)

    instagram_user_id = db.Column(db.String(500), nullable=True)
    instagram_access_token = db.Column(db.String(500), nullable=True)

    custom_game_code = db.Column(db.String(20), unique=True, nullable=True)
    is_public = db.Column(db.Boolean, default=True)
    allow_joins = db.Column(db.Boolean, default=True)
    is_tutorial = db.Column(db.Boolean, default=False)


    @staticmethod
    def generate_unique_code():
        while True:
            code = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
            if not Game.query.filter_by(custom_game_code=code).first():
                return code

    def __init__(self, **kwargs):
        super(Game, self).__init__(**kwargs)
        if not self.custom_game_code:
            self.custom_game_code = self.generate_unique_code()
        else:
            while True:
                try:
                    self.custom_game_code = self.generate_unique_code()
                    db.session.add(self)
                    db.session.commit()
                    break
                except IntegrityError:
                    db.session.rollback()

    @property
    def twitter_url(self):
        return f"https://twitter.com/{self.twitter_username}" if self.twitter_username else "https://twitter.com/QuestByCycle"

    @property
    def facebook_url(self):
        return f"https://facebook.com/{self.facebook_page_id}" if self.facebook_page_id else "https://facebook.com/QuestByCycle"

    @property
    def instagram_url(self):
        return f"https://instagram.com/{self.instagram_user_id}" if self.instagram_user_id else "https://instagram.com/QuestByCycle"

game_participants = db.Table('game_participants',
    db.Column('game_id', db.Integer, db.ForeignKey('game.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class PlayerMessageBoardMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(utc), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    user = db.relationship('User', foreign_keys=[user_id], backref='messages_received')
    author = db.relationship('User', foreign_keys=[author_id], backref='messages_sent')
    

class ShoutBoardMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id', ondelete='CASCADE'), nullable=False)  # Add this line
    timestamp = db.Column(db.DateTime, index=True, default=lambda: datetime.now(utc))
    is_pinned = db.Column(db.Boolean, default=False)
    likes = db.relationship('ShoutBoardLike', backref='message', cascade="all, delete-orphan")


class ShoutBoardLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('shout_board_message.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (db.UniqueConstraint('message_id', 'user_id', name='_message_user_uc'),)

class QuestSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quest_id = db.Column(db.Integer, db.ForeignKey('quest.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    comment = db.Column(db.String(1000), nullable=True)
    timestamp = db.Column(db.DateTime, index=True, default=lambda: datetime.now(utc))
    twitter_url = db.Column(db.String(1024), nullable=True)
    fb_url = db.Column(db.String(1024), nullable=True)
    instagram_url = db.Column(db.String(1024), nullable=True)

    quest = db.relationship('Quest', back_populates='submissions')
    user = db.relationship('User', back_populates='quest_submissions', overlaps="submitter")

class Sponsor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    website = db.Column(db.String(255), nullable=True)
    logo = db.Column(db.String(255), nullable=True)
    description = db.Column(db.String(1000), nullable=True)
    tier = db.Column(db.String(255), nullable=False)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)

    game = db.relationship('Game', back_populates='sponsors')

class ProfileWallMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(utc), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('profile_wall_message.id', ondelete='CASCADE'), nullable=True)

    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('profile_messages_received', cascade="all, delete-orphan"))
    author = db.relationship('User', foreign_keys=[author_id], backref=db.backref('profile_messages_sent', cascade="all, delete-orphan"))
    replies = db.relationship('ProfileWallMessage', backref=db.backref('parent', remote_side=[id]), cascade="all, delete-orphan")


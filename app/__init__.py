from flask import Flask, render_template, current_app, flash, redirect, url_for
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from werkzeug.middleware.proxy_fix import ProxyFix
from app.auth import auth_bp
from app.admin import admin_bp, create_super_admin
from app.main import main_bp
from app.games import games_bp
from app.quests import quests_bp
from app.badges import badges_bp
from app.profile import profile_bp
from app.ai import ai_bp
from app.models import db
from .config import load_config
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta
from flask_socketio import SocketIO
from logging.handlers import RotatingFileHandler

import logging
import os

# Global variable to track the first request
has_run = False

# Initialize extensions
login_manager = LoginManager()
migrate = Migrate()
socketio = SocketIO()
#cache = Cache(config={'CACHE_TYPE': 'simple'})  # Configure as needed

# Set up logging configuration
if not os.path.exists('logs'):
    os.mkdir('logs')

# Configure the root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        RotatingFileHandler("logs/application.log", maxBytes=10240, backupCount=10),
        logging.StreamHandler()  # This sends logs to the console
    ]
)

logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)

    # Load configuration
    inscopeconfig = load_config()
    app.config.update(inscopeconfig)

    # Set SQLAlchemy engine options to mitigate connection issues
    # This instructs SQLAlchemy to check connections before using them and to recycle them after an hour.
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 3600
    }
    
    # Init cache
    #cache.init_app(app)

    # Apply configurations from the TOML file
    app.config['DEFAULT_SUPER_ADMIN_PASSWORD'] = app.config['encryption']['DEFAULT_SUPER_ADMIN_PASSWORD']
    app.config['DEFAULT_SUPER_ADMIN_USERNAME'] = app.config['encryption']['DEFAULT_SUPER_ADMIN_USERNAME']
    app.config['DEFAULT_SUPER_ADMIN_EMAIL'] = app.config['encryption']['DEFAULT_SUPER_ADMIN_EMAIL']
    app.config['UPLOAD_FOLDER'] = app.config['main']['UPLOAD_FOLDER']
    app.config['VERIFICATIONS'] = app.config['main']['VERIFICATIONS']
    app.config['BADGE_IMAGE_DIR'] = app.config['main']['BADGE_IMAGE_DIR']
    app.config['CAROUSEL_IMAGES_DIR'] = app.config['main']['CAROUSEL_IMAGES_DIR']
    app.config['SQLALCHEMY_ECHO'] = app.config['main']['SQLALCHEMY_ECHO']
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['flask']['SQLALCHEMY_DATABASE_URI']
    app.config['DEBUG'] = app.config['flask']['DEBUG']
    app.config['TASKCSV'] = app.config['main']['TASKCSV']
    app.config['OPENAI_API_KEY'] = app.config['openai']['OPENAI_API_KEY']
    app.config['SECRET_KEY'] = app.config['encryption']['SECRET_KEY']
    app.config['SESSION_COOKIE_SECURE'] = app.config['encryption']['SESSION_COOKIE_SECURE']
    app.config['SESSION_COOKIE_NAME'] = app.config['encryption']['SESSION_COOKIE_NAME']
    app.config['SESSION_COOKIE_SAMESITE'] = app.config['encryption']['SESSION_COOKIE_SAMESITE']
    app.config['SESSION_COOKIE_DOMAIN'] = app.config['encryption']['SESSION_COOKIE_DOMAIN']
    app.config['SESSION_REFRESH_EACH_REQUEST'] = app.config['encryption']['SESSION_REFRESH_EACH_REQUEST']
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=app.config['encryption']['REMEMBER_COOKIE_DURATION_DAYS'])
    app.config['MAIL_USERNAME'] = app.config['mail']['MAIL_USERNAME']
    app.config['MAIL_DEFAULT_SENDER'] = app.config['mail']['MAIL_DEFAULT_SENDER']

    # Load social media configurations
    app.config['TWITTER_USERNAME'] = app.config['social']['twitter_username']
    app.config['TWITTER_API_KEY'] = app.config['social']['twitter_api_key']
    app.config['TWITTER_API_SECRET'] = app.config['social']['twitter_api_secret']
    app.config['TWITTER_ACCESS_TOKEN'] = app.config['social']['twitter_access_token']
    app.config['TWITTER_ACCESS_TOKEN_SECRET'] = app.config['social']['twitter_access_token_secret']
    app.config['FACEBOOK_APP_ID'] = app.config['social']['facebook_app_id']
    app.config['FACEBOOK_APP_SECRET'] = app.config['social']['facebook_app_secret']
    app.config['FACEBOOK_ACCESS_TOKEN'] = app.config['social']['facebook_access_token']
    app.config['FACEBOOK_PAGE_ID'] = app.config['social']['facebook_page_id']
    app.config['INSTAGRAM_ACCESS_TOKEN'] = app.config['social']['instagram_access_token']
    app.config['INSTAGRAM_USER_ID'] = app.config['social']['instagram_user_id']
    app.config['SOCKETIO_SERVER_URL'] = app.config['socketio']['SERVER_URL']

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1, x_proto=1, x_port=1)

    # Initialize extensions
    csrf = CSRFProtect(app)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, async_mode='gevent', logger=True, engineio_logger=True)

    # Create super admin
    with app.app_context():
        db.create_all()
        create_super_admin(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(ai_bp, url_prefix='/ai')
    app.register_blueprint(games_bp, url_prefix='/games')
    app.register_blueprint(quests_bp, url_prefix='/quests')
    app.register_blueprint(badges_bp, url_prefix='/badges')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(main_bp)

    # Setup login manager
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User  # Local import to avoid circular dependency
        return User.query.get(int(user_id))
        
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        logger.warning(f"404 error: {error}")
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"500 error: {error}")
        db.session.rollback()
        return render_template('500.html'), 500

    @app.errorhandler(429)
    def too_many_requests(e):
        logger.warning(f"429 error: {e}")
        return render_template('429.html'), 429

    # Context processor to add logout form to all templates
    @app.context_processor
    def inject_logout_form():
        from app.forms import LogoutForm  # Local import to avoid circular dependency
        return dict(logout_form=LogoutForm())
    
    @app.context_processor
    def inject_socketio_url():
        return dict(socketio_server_url=app.config['SOCKETIO_SERVER_URL'])

    @app.context_processor
    def inject_selected_game_id():
        if current_user.is_authenticated:
            return dict(selected_game_id=current_user.selected_game_id or 0)
        else:
            return dict(selected_game_id=None)

    @app.errorhandler(Exception)
    def handle_exception(e):
        # Log the error details
        logger.error(f"Unhandled Exception: {e}")

        # Flash a user-friendly message
        flash('An unexpected error occurred. Please try again later.', 'error')

        # Redirect to a safe page (e.g., home or login)
        return redirect(url_for('main.index'))

    return app
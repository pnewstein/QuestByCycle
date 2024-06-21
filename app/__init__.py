from flask import Flask, render_template, current_app
from flask_login import LoginManager
from flask_migrate import Migrate
from werkzeug.middleware.proxy_fix import ProxyFix
from app.auth import auth_bp
from app.admin import admin_bp, create_super_admin
from app.main import main_bp
from app.games import games_bp
from app.tasks import tasks_bp
from app.badges import badges_bp
from app.profile import profile_bp
from app.ai import ai_bp
from app.models import db
from .config import load_config
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta
from flask_mail import Mail
from flask_socketio import SocketIO

# Global variable to track the first request
has_run = False

# Initialize extensions
login_manager = LoginManager()
migrate = Migrate()
mail = Mail()
socketio = SocketIO()

def create_app():
    app = Flask(__name__)

    # Load configuration
    inscopeconfig = load_config()
    app.config.update(inscopeconfig)

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
    app.config['MAIL_SERVER'] = app.config['mail']['MAIL_SERVER']
    app.config['MAIL_PORT'] = app.config['mail']['MAIL_PORT']
    app.config['MAIL_USE_TLS'] = app.config['mail']['MAIL_USE_TLS']
    app.config['MAIL_USE_SSL'] = app.config['mail']['MAIL_USE_SSL']
    app.config['MAIL_USERNAME'] = app.config['mail']['MAIL_USERNAME']
    app.config['MAIL_PASSWORD'] = app.config['mail']['MAIL_PASSWORD']
    app.config['MAIL_DEFAULT_SENDER'] = app.config['mail']['MAIL_DEFAULT_SENDER']

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1, x_proto=1, x_port=1)

    # Initialize extensions
    csrf = CSRFProtect(app)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    socketio.init_app(app)

    # Create super admin
    with app.app_context():
        db.create_all()
        create_super_admin(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(ai_bp, url_prefix='/ai')
    app.register_blueprint(games_bp, url_prefix='/games')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
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
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500

    @app.errorhandler(429)
    def too_many_requests(e):
        return render_template('429.html'), 429

    # Context processor to add logout form to all templates
    @app.context_processor
    def inject_logout_form():
        from app.forms import LogoutForm  # Local import to avoid circular dependency
        return dict(logout_form=LogoutForm())

    return app

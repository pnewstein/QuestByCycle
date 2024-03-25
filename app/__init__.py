from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import get_config

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    db.init_app(app)
    
    Migrate(app,db)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Blueprint registrations here

    return app

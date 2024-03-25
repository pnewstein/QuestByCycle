# config.py
import os
import toml

base_dir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Basic Config
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a_very_secret_key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(base_dir, 'app.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(base_dir, 'test.db')

class ProductionConfig(Config):
    DEBUG = False

# Function to load and return the config object based on the FLASK_ENV environment variable
def get_config():
    env = os.getenv('FLASK_ENV', 'development')
    if env == 'development':
        return DevelopmentConfig
    elif env == 'testing':
        return TestingConfig
    elif env == 'production':
        return ProductionConfig
    else:
        return Config

# Load the configurations from a TOML file
def load_config_from_toml():
    config_path = os.path.join(base_dir, 'config.toml')
    if os.path.exists(config_path):
        toml_config = toml.load(config_path)
        
        # Assuming there's a [flask] table in the TOML file
        flask_config = toml_config.get('flask', {})
        for key, value in flask_config.items():
            setattr(Config, key.upper(), value)
            
load_config_from_toml()

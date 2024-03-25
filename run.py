# run.py
from flask import Flask
from config import get_config

app = Flask(__name__)
app.config.from_object(get_config())

# Placeholder for Flask routes and other app setups
@app.route('/')
def index():
    return "Welcome to BikeHunt!"

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])

from flask import jsonify, request, url_for, current_app
from flask_login import login_required
from datetime import datetime
from requests_oauthlib import OAuth1Session
import os
import base64
from .models import db, Game, Task, TaskSubmission

def authenticate_twitter(api_key, api_secret, access_token, access_token_secret):
    """Create and return an OAuth1Session object for Twitter API."""
    return OAuth1Session(api_key, api_secret, access_token, access_token_secret)

def upload_media_to_twitter(file_path, api_key, api_secret, access_token, access_token_secret):
    """Upload media to Twitter and return the media_id."""
    twitter = authenticate_twitter(api_key, api_secret, access_token, access_token_secret)
    url = "https://upload.twitter.com/1.1/media/upload.json"

    # Open the file in binary mode
    with open(file_path, 'rb') as file:
        files = {'media': file}
        response = twitter.post(url, files=files)

        if response.status_code == 200:
            media_id = response.json().get('media_id_string')
            return media_id, None
        else:
            return None, response.text


def post_to_twitter(status, media_ids, api_key, api_secret, access_token, access_token_secret):
    """Post a tweet with media using the Twitter API v2."""
    url = "https://api.twitter.com/2/tweets"
    payload = {
        "text": status,
        "media": {
            "media_ids": [media_ids]
        }
    }
    twitter = authenticate_twitter(api_key, api_secret, access_token, access_token_secret)
    response = twitter.post(url, json=payload)
    if response.status_code == 201:
        return response.json(), None
    else:
        return None, response.text
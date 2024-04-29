
from requests_oauthlib import OAuth1Session
import requests

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
    

def authenticate_facebook(app_id, app_secret):
    """Get a Facebook access token."""
    url = 'https://graph.facebook.com/oauth/access_token'
    params = {
        'client_id': app_id,
        'client_secret': app_secret,
        'grant_type': 'client_credentials'
    }
    response = requests.get(url, params=params)
    return response.json()['access_token']


def upload_image_to_facebook(page_id, image_path, access_token):
    """Upload an image to a Facebook Page and return the media object ID."""
    files = {
        'source': (image_path, open(image_path, 'rb'), 'image/jpeg')
    }
    data = {
        'access_token': access_token
    }
    url = f"https://graph.facebook.com/{page_id}/photos"
    response = requests.post(url, files=files, data=data)
    return response.json()  # This response contains 'id' which is the media object ID


def post_to_facebook_with_image(page_id, message, image_id, access_token):
    """Post a message with an image to a Facebook Page."""
    url = f"https://graph.facebook.com/{page_id}/feed"
    payload = {
        'message': message,
        'attached_media[0]': f'{{"media_fbid":"{image_id}"}}',
        'access_token': access_token
    }
    response = requests.post(url, data=payload)
    return response.json()


def post_photo_to_instagram(page_id, image_url, caption, access_token):
    """Post a photo to Instagram via the connected Facebook Page."""
    # Create a container
    url = f'https://graph.facebook.com/{page_id}/media'
    payload = {
        'image_url': image_url,
        'caption': caption,
        'access_token': access_token
    }
    container_response = requests.post(url, data=payload)
    container_id = container_response.json()['id']

    # Publish the container
    publish_url = f'https://graph.facebook.com/{page_id}/media_publish'
    publish_payload = {
        'creation_id': container_id,
        'access_token': access_token
    }
    publish_response = requests.post(publish_url, data=publish_payload)
    return publish_response.json()
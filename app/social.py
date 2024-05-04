from requests_oauthlib import OAuth1Session
from .models import db, Game
import requests
import json
import mimetypes

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


def post_to_twitter(status, media_ids, twitter_username, api_key, api_secret, access_token, access_token_secret):
    """Post a tweet with media using the Twitter API and return the tweet URL."""
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
        tweet_id = response.json().get('data').get('id')  # Capture the tweet ID from the response
        tweet_url = f"https://twitter.com/{twitter_username}/status/{tweet_id}"
        return tweet_url, None  # Return the tweet URL
    else:
        return None, response.text


def get_facebook_page_access_token(game_id):
    # Assume Game model has the necessary fields
    game = Game.query.get(game_id)
    if not game:
        return None  # Or handle the error appropriately

    # Fetch the Page Access Token using the Facebook Graph API
    url = f"https://graph.facebook.com/{game.facebook_page_id}?fields=access_token&access_token={game.facebook_access_token}"
    response = requests.get(url)
    if response.status_code == 200:
        page_access_token = response.json().get('access_token')
        # Optionally update the stored token in database or configuration
        #game.facebook_access_token = page_access_token
        #db.session.commit()
        return page_access_token
    else:
        return None  # Log this error or handle it accordingly



def upload_image_to_facebook(page_id, image_path, game_id):
    """
    Uploads an image to Facebook to get a media object ID.
    Args:
    page_id (str): The Facebook Page ID.
    image_path (str): Local path to the image file.
    access_token (str): Access token for the Facebook Page.
    Returns:
    dict: Response from the Facebook API.
    """
    page_token = get_facebook_page_access_token(game_id)
    if not page_token:
        print("Failed to get access token for page.")
        return None

    # Detect MIME type of the file
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = 'image/jpeg'  # Default to JPEG if MIME type is undetectable

    files = {'file': (image_path, open(image_path, 'rb'), mime_type)}
    data = {
        'access_token': page_token,
        'published': 'false'  # Set to 'false' to upload the image without posting it
    }

    url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
    response = requests.post(url, files=files, data=data)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to upload image: {response.text}")
        return None


def post_to_facebook_with_image(page_id, message, media_object_id, game_id):
    """
    Creates a post on Facebook using the previously uploaded media object ID.

    Args:
    page_id (str): The Facebook Page ID.
    message (str): The message to post.
    media_object_id (str): The media object ID returned by the Facebook image upload.
    access_token (str): Access token for the Facebook Page.

    Returns:
    bool: True if the post was successful, False otherwise.
    """
    page_token = get_facebook_page_access_token(game_id)

    url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
    payload = {
        'message': message,
        'attached_media': json.dumps([{'media_fbid': media_object_id}]),
        'access_token': page_token
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return True
    return False


def post_photo_to_instagram(page_id, image_url, caption, access_token):
    """Post a photo to Instagram via the connected Facebook Page."""
    # Create a container
    url = f'https://graph.facebook.com/v19.0/{page_id}/media'
    payload = {
        'image_url': image_url,
        'caption': caption,
        'access_token': access_token
    }
    container_response = requests.post(url, data=payload)
    container_id = container_response.json()['id']

    # Publish the container
    publish_url = f'https://graph.facebook.com/v19.0/{page_id}/media_publish'
    publish_payload = {
        'creation_id': container_id,
        'access_token': access_token
    }
    publish_response = requests.post(publish_url, data=publish_payload)
    return publish_response.json()
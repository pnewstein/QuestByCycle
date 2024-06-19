import requests
import json
import mimetypes
from requests_oauthlib import OAuth1Session

def authenticate_twitter(api_key, api_secret, access_token, access_token_secret):
    return OAuth1Session(api_key, api_secret, access_token, access_token_secret)

def upload_media_to_twitter(file_path, api_key, api_secret, access_token, access_token_secret):
    twitter = authenticate_twitter(api_key, api_secret, access_token, access_token_secret)
    url = "https://upload.twitter.com/1.1/media/upload.json"

    with open(file_path, 'rb') as file:
        files = {'media': file}
        response = twitter.post(url, files=files)

        if response.status_code == 200:
            media_id = response.json().get('media_id_string')
            return media_id, None
        else:
            return None, response.text

def post_to_twitter(status, media_ids, twitter_username, api_key, api_secret, access_token, access_token_secret):
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
        tweet_id = response.json().get('data').get('id')
        tweet_url = f"https://twitter.com/{twitter_username}/status/{tweet_id}"
        return tweet_url, None
    else:
        return None, response.text

def get_facebook_user_access_token(app_id, app_secret, redirect_uri, code):
    url = 'https://graph.facebook.com/v19.0/oauth/access_token'
    params = {
        'client_id': app_id,
        'redirect_uri': redirect_uri,
        'client_secret': app_secret,
        'code': code
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()['access_token']

def get_long_lived_user_access_token(app_id, app_secret, short_lived_token):
    url = 'https://graph.facebook.com/v19.0/oauth/access_token'
    params = {
        'grant_type': 'fb_exchange_token',
        'client_id': app_id,
        'client_secret': app_secret,
        'fb_exchange_token': short_lived_token
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()['access_token']

def get_facebook_page_access_token(user_access_token, page_id):
    url = f'https://graph.facebook.com/v19.0/{page_id}'
    params = {
        'fields': 'access_token',
        'access_token': user_access_token
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()['access_token']

def upload_image_to_facebook(page_id, image_path, access_token):
    print(f"Preparing to upload image to Facebook Page ID: {page_id}")
    print(f"Access Token: {access_token}")
    print(f"Image Path: {image_path}")

    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = 'image/jpeg'

    files = {'file': (image_path, open(image_path, 'rb'), mime_type)}
    data = {
        'access_token': access_token,
        'published': 'false'
    }

    url = f"https://graph.facebook.com/v19.0/{page_id}/photos"
    print(f"Uploading to URL: {url}")
    response = requests.post(url, files=files, data=data)

    print(f"Facebook API Response Status Code: {response.status_code}")
    print(f"Facebook API Response Text: {response.text}")

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to upload image: {response.text}")
        return None

def post_to_facebook_with_image(page_id, message, media_object_id, access_token):
    url = f"https://graph.facebook.com/v19.0/{page_id}/feed"
    payload = {
        'message': message,
        'attached_media': json.dumps([{'media_fbid': media_object_id}]),
        'access_token': access_token
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        post_id = response.json().get('id')
        fb_url = f"https://www.facebook.com/{post_id}"
        return fb_url, None
    else:
        return None, response.text

def post_photo_to_instagram(page_id, image_url, caption, access_token):
    url = f'https://graph.facebook.com/v19.0/{page_id}/media'
    payload = {
        'image_url': image_url,
        'caption': caption,
        'access_token': access_token
    }
    container_response = requests.post(url, data=payload)
    container_id = container_response.json()['id']

    publish_url = f'https://graph.facebook.com/v19.0/{page_id}/media_publish'
    publish_payload = {
        'creation_id': container_id,
        'access_token': access_token
    }
    publish_response = requests.post(publish_url, data=publish_payload)
    return publish_response.json()

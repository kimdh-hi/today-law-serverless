import requests
import boto3
from pymongo import MongoClient
import json
from datetime import datetime, timedelta
import jwt

def get_secret():
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name="ap-northeast-2"
    )
    get_secret_value_response = client.get_secret_value(
        SecretId='todaylaw-secret'
    )
    token = get_secret_value_response['SecretString']
    return eval(token)

secrets = get_secret()

def db_connect():
    # client = MongoClient(MONGO_URL, 27017, username=MONGO_USERNAME, password=MONGO_PASSWORD)
    return MongoClient("mongodb://{0}:{1}@{2}".format(secrets['user'], secrets['password'], secrets['host']))

def get_token_secret():
    return secrets['token_secret']

def lambda_handler(event, context):
    body = json.loads(event['body'])
    access_token = body['accessToken']

    print('access_token: ', access_token)

    request_url = "https://kapi.kakao.com/v2/user/me"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.post(request_url, headers=headers)
    user_info = response.json()

    print('user_info: ', user_info)

    client = db_connect()
    db = client.todaylaw

    kakao_account = user_info['kakao_account']
    id = str(user_info['id'])
    find_user = db.users.find_one({'user_id': id})

    if find_user == None:
        user_info_doc = {
            "user_id": id,
            "username": kakao_account['email'],
            "name": kakao_account['profile']['nickname'],
            "profile_image": kakao_account['profile']['profile_image_url'],
            "like_laws": [],
            "hate_laws": [],
            "bookmarks": [],
            "comments": [],
            "bio": "",
            "receive_mail": False,
            "recently_view": []
        }
        db.users.insert_one(user_info_doc)

    name = kakao_account['profile']['nickname']

    payload = {
        "user_id": id,
        "name": name,
        #"exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24)
        "exp": datetime.utcnow() + timedelta(seconds=60*60)
    }

    token_secret = get_token_secret()

    token = jwt.encode(payload, token_secret, "HS256")

    print('token = ', token)

    return {
        "statusCode": 200,
        'headers': {
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        },
        "body": json.dumps({
            "result": "success",
            "token": token
        })
    }


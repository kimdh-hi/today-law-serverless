import requests
import boto3
from pymongo import MongoClient
import json
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
    return MongoClient("mongodb://{0}:{1}@{2}".format(secrets['user'], secrets['password'], secrets['host']))

client = db_connect()
db = client.todaylaw

def lambda_handler(event, context):

    try:
        token = event['headers']['Authorization']
        user = verify_token(token)

        body = json.loads(event['body'])

        # 즐겨찾기 추가를 위한 파라미터
        law_id = body['id_give']  # 즐겨찾기를 한 법안의 ID (API로부터 받은 ID)
        title = body['title']
        proposer_name = body['proposer_name']
        proposer_names = body['proposer_names']
        url = body['url']
        date = body['date']

        exist_id = db.bookmark.find_one({'id': law_id})

        if exist_id is not None:
            msg = "이미 즐겨찾기에 저장된 법안입니다."
        else:
            bookmark_doc = {
                "law_id": law_id,
                "url": url,
                "title": title,
                "proposer_name": proposer_name,
                "proposer_names": proposer_names,
                "date": date,
                "user_id": user['user_id']
            }

            db.users.update(
                {'user_id': user['user_id']},
                {'$push': {'bookmarks': law_id}}
            )
            db.bookmark.insert_one(bookmark_doc)

            msg = "즐겨찾기에 저장되었습니다."

        return {
            "statusCode": 200,
            'headers': {
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
            },
            "body": json.dumps({"result": "success", "msg": msg})
        }

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return {
            "statusCode": 403,
            'headers': {
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
            },
            "body": json.dumps({"result": "fail", "msg": "허용되지 않은 접근입니다."})
        }

def verify_token(encoded_token):
    # 인코딩된 토큰의 payload 부분 디코딩
    decoded_token = jwt.decode(encoded_token, secrets['token_secret'], algorithms=['HS256'])
    # 디코딩된 payload의 user_id가 users DB에 있는지 확인
    user = db.users.find_one({'user_id': decoded_token['user_id']}, {'_id': False})

    return user
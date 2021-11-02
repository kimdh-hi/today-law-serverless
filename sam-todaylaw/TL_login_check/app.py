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

token_secret = secrets['token_secret']

def lambda_handler(event, context):
    print(event)
    try:
        print(event)
        token = event['headers']['Authorization']
        user = verify_token(token)
        print(user)

        find_user = db.users.find_one({'user_id': user['user_id']}, {'_id': False})

        if find_user is not None:
            return {
                "statusCode": 200,
                'headers': {
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
                },
                "body": json.dumps({"result": "success", "user": find_user})
            }
        else:
            return {
                "statusCode": 500,
                'headers': {
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
                },
                "body": json.dumps({"result": "fail", "msg": "허용되지 않은 접근입니다."})
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
    decoded_token = jwt.decode(encoded_token, token_secret, algorithms=['HS256'])
    # 디코딩된 payload의 user_id가 users DB에 있는지 확인
    user = db.users.find_one({'user_id': decoded_token['user_id']}, {'_id': False})

    return user
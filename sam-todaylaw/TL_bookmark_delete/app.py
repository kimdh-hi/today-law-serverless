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
    # client = MongoClient(MONGO_URL, 27017, username=MONGO_USERNAME, password=MONGO_PASSWORD)
    return MongoClient("mongodb://{0}:{1}@{2}".format(secrets['user'], secrets['password'], secrets['host']))

client = db_connect()
db = client.todaylaw

def lambda_handler(event, context):
    try:
        token = event['headers']['Authorization']
        user = verify_token(token)

        body = json.loads(event['body'])

        id_receive = body['id_give']
        bookmark_id = db.bookmark.find_one({'law_id': id_receive, 'user_id': user['user_id']}, {'_id': False})

        if bookmark_id is not None:
            # users DB의 bookmark 필드에서 삭제 (이것도 필요한 부분인지 아직 모르겠음)
            db.users.update(
                {'user_id': user['user_id']},
                {'$pull': {'bookmark_id': id_receive}}
            )
            # bookmark db에서 삭제
            db.bookmark.delete_one({"law_id": id_receive, "user_id": user['user_id']})
            msg = "법안이 삭제 되었습니다."
        else:
            msg = "즐겨찾기에 없는 법안입니다."

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
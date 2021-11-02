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


token_secret = secrets['token_secret']
client = db_connect()
db = client.todaylaw


def lambda_handler(event, context):
    try:
        token = event['headers']['Authorization']
        user = verify_token(token)
        body = json.loads(event['body'])
        id_receive = body['id_give']

        title_receive = body['title_give']
        content_receive = body['content_give']
        content_receive = content_receive[:100]
        content_receive += " ..."

        proposer_name_receive = body['proposer_name_give']
        proposer_names_receive = body['proposer_names_give']
        url_receive = body['url_give']

        hate_laws = db.users.find_one(
            {'user_id': user['user_id']},
            {'_id': 0}
        )['hate_laws']

        flag = True

        for hate_law in hate_laws:
            if id_receive in hate_law['hate_law_id']:
                res = db.users.update(
                    {'user_id': user['user_id']},
                    {'$pull':
                         {'hate_laws':
                              {'hate_law_id': id_receive, 'title': title_receive}
                          }
                     },
                )

                hates = db.ranking.find_one({'id': id_receive})
                current_hate = hates['hate']
                new_hate = current_hate - 1
                current_like = hates['like']
                db.ranking.update_one({'id': id_receive}, {'$set': {'hate': new_hate}})

                flag = False

        if flag:
            doc = {
                'hate_law_id': id_receive,
                'title': title_receive,
                'content': content_receive,
                'proposer_name': proposer_name_receive,
                'proposer_names': proposer_names_receive,
                'url': url_receive
            }
            db.users.update(
                {'user_id': user['user_id']},
                {'$push':
                     {'hate_laws': doc}
                 }
            )

            hates = db.ranking.find_one({'id': id_receive})
            current_hate = hates['hate']
            new_hate = current_hate + 1
            current_like = hates['like']
            db.ranking.update_one({'id': id_receive}, {'$set': {'hate': new_hate}})

        return {
            "statusCode": 200,
            'headers': {
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
            },
            "body": json.dumps({
                "result": "success",
                'like': current_like,
                'hate': new_hate,
                'title': title_receive,
                'content': content_receive,
                'proposer_name': proposer_name_receive,
                'proposer_names': proposer_name_receive,
                'url': url_receive
            })
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
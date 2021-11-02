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

        like_laws = db.users.find_one(
            {'user_id': user['user_id']},  # 현재 인증된 사용자로 DB 조회
            {'_id': 0}
        )['like_laws']

        flag = True

        for like_law in like_laws:
            if id_receive in like_law['like_law_id']:
                res = db.users.update(
                    {'user_id': user['user_id']},  # 현재 인증된 사용자로 DB 조회
                    {'$pull':  # 리스트에서 제거
                         {'like_laws':  # like_laws 리스트의 요소중 like_law_id 필드가 id_receive인 요소
                              {'like_law_id': id_receive, 'title': title_receive}
                          }
                     },
                )

                # 좋아요를 감소시키는 부분
                likes = db.ranking.find_one({'id': id_receive})
                current_like = likes['like']
                new_like = current_like - 1
                current_hate = likes['hate']
                db.ranking.update_one({'id': id_receive}, {'$set': {'like': new_like}})
                flag = False

        if flag:
            # 사용자의 좋아요 목록에 추가
            doc = {
                'like_law_id': id_receive,
                'title': title_receive,
                'content': content_receive,
                'proposer_name': proposer_name_receive,
                'proposer_names': proposer_names_receive,
                'url': url_receive
            }
            db.users.update(
                {'user_id': user['user_id']},
                {'$push':
                     {'like_laws': doc}
                 }
            )

            # 좋아요를 증가시키는 부분
            likes = db.ranking.find_one({'id': id_receive})
            current_like = likes['like']
            new_like = current_like + 1
            current_hate = likes['hate']
            db.ranking.update_one({'id': id_receive}, {'$set': {'like': new_like}})

        return {
            "statusCode": 200,
            'headers': {
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
            },
            "body": json.dumps({
                "result": "success",
                'id': id_receive,
                'like': new_like,
                'hate': current_hate,
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
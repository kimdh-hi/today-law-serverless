import requests
import boto3
from bs4 import BeautifulSoup
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
    body = json.loads(event['body'])

    url_receive = body['url_give']
    id_receive = body['id_give']
    title = body['title_give']
    proposer_name = body['proposer_name_give']
    proposer_names = body['proposer_names_give']


    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)AppleWebKit/537.36 (HTML, like Gecko) Chrome/73.0.3683.86 Safari/537.36'}
    data = requests.get(url_receive, headers=headers)

    soup = BeautifulSoup(data.text, 'html.parser')
    content = soup.select_one('#summaryContentDiv').text
    date = soup.select_one(
        'body > div > div.contentWrap > div.subContents > div > div.contIn > div.tableCol01 > table > tbody > tr > td:nth-child(2)').text

    ranking = db.ranking.find_one({'id': id_receive}, {'_id': False})
    if ranking is not None:
        count = ranking['count']
        new_count = count + 1
        db.ranking.update_one({'id': id_receive}, {'$set': {'count': new_count}})
    else:
        doc = {
            'id': id_receive,
            'url': url_receive,
            'title': title,
            'proposer_name': proposer_name,
            'proposer_names': proposer_names,
            'date': date,
            'count': 1,
            'like': 0,
            'hate': 0
        }

        db.ranking.insert_one(doc)

    # 좋아요, 싫어요 DB에서 찾아서 보내주기
    like = db.ranking.find_one({'id': id_receive}, {'_id': False})
    like_like = like['like']
    hate = db.ranking.find_one({'id': id_receive}, {'_id': False})
    hate_hate = hate['hate']

    access_token = event['headers']['Authorization']
    recently_view(id_receive, title, url_receive, proposer_name, proposer_names, content, access_token)

    return {
        "statusCode": 200,
        'headers': {
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        },
        "body": json.dumps({
            'content': content,
            'title': title,
            'date': date,
            'proposer_name': proposer_name,
            'proposer_names': proposer_names,
            'id': id_receive
        })
    }

def recently_view(id, title, url, proposer_name, proposer_names, content, access_token):

    try:
        user = verify_token(access_token)
        user = db.users.find_one({'user_id': user['user_id']}, {'_id': False})

        recently_list = list(db.users.find(
            {'user_id': user['user_id']}, {'recently_view': True, '_id': False}
        ))

        while (len(recently_list[0]['recently_view']) > 5):
            del recently_list[0]['recently_view'][0]
            db.users.update(
                {'user_id': user['user_id']},
                {'$pop': {'recently_view': -1}}
            )
        temp = True
        for i in range(len(recently_list[0]['recently_view'])):
            if (recently_list[0]['recently_view'][i]['recently_view_id'] == id):
                temp = False
                break

        if temp == True:
            db.users.update(
                {'user_id': user['user_id']},
                {'$push': {
                    'recently_view': {'recently_view_id': id, 'title': title, 'url': url,
                                      'proposer_name': proposer_name,
                                      'proposer_names': proposer_names, 'content': content}}}, upsert=True
            )
        return
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return


def verify_token(encoded_token):
    # 인코딩된 토큰의 payload 부분 디코딩
    decoded_token = jwt.decode(encoded_token, token_secret, algorithms=['HS256'])
    # 디코딩된 payload의 user_id가 users DB에 있는지 확인
    user = db.users.find_one({'user_id': decoded_token['user_id']}, {'_id': False})

    return user
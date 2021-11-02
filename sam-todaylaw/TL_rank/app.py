import requests
import boto3
from pymongo import MongoClient
import json

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


def lambda_handler(event, context):

    client = db_connect()
    db = client.todaylaw

    rank_list = db.ranking.find({}).sort([('count',-1), ('title',1)]).limit(5)
    rank_result = []

    for idx, rank in enumerate(rank_list):
        title = title_row_check(rank['title'])
        doc = {
            'id':rank['id'],
            'rank':idx+1,
            'url':rank['url'],
            'title':title,
            'proposer_name': rank['proposer_name'],
            'proposer_names': rank['proposer_names'],
            'date':rank['date'],
            'count':rank['count'],
            'like':rank['like'],
            'hate':rank['hate']
        }

        rank_result.append(doc)

    return {
        "statusCode": 200,
        'headers': {
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        },
        "body": json.dumps(rank_result)
    }


def title_row_check(title):
    title_max_length = 22
    if len(title) >= title_max_length:
        title = title[:title_max_length]
        title = title + " ..."
    return title

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


token_secret = secrets['token_secret']
client = db_connect()
db = client.todaylaw


def lambda_handler(event, context):

    likes_list = list(db.ranking.find({}, {'_id': False}).sort([('like', -1), ('title', 1)]).limit(50))

    return {
        "statusCode": 200,
        'headers': {
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
        },
        "body": json.dumps({
            "result": "success",
            "likes_list": likes_list
        })
    }



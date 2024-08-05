import os
import json
import boto3


region = os.environ.get('AWS_REGION')
account_id = boto3.client('sts').get_caller_identity()['Account']

campaignArn='arn:aws:personalize:'+region+':'+str(account_id)+':campaign/personalize-poc-rerank'

response = {
    "statusCode": 200,
    "headers": {
        "Access-Control-Allow-Origin": '*'
    },
    "isBase64Encoded": False
}

def lambda_handler(event, context):
    print(event)
    
    user_id = 1
    if "user_id" in event.keys():
        user_id = event['user_id']
    elif "queryStringParameters" in event.keys():
        if "user_id" in event['queryStringParameters'].keys():
            user_id = event['queryStringParameters']['user_id'].strip()

    item_id_list = ""
    if "item_id_list" in event.keys():
        item_id_list = event['item_id_list']
    elif "queryStringParameters" in event.keys():
        if "item_id_list" in event['queryStringParameters'].keys():
            item_id_list = event['queryStringParameters']['item_id_list'].strip()
    
    item_id_list=item_id_list.split(',')
    print('item_id_list:',item_id_list)
    
    if user_id == '' or len(item_id_list) == 0:
        ranking_result = 'user id or item list is null'
    else:
        personalize_runtime = boto3.client('personalize-runtime')
    
        result = personalize_runtime.get_personalized_ranking(
            campaignArn = campaignArn,
            userId = user_id,
            inputList = item_id_list
        )
        print('result:',result)
        ranking_result = result['personalizedRanking']
        
    print("ranking_result:",ranking_result)
    
    response['body'] = json.dumps(
                    {
                        'ranking_result':ranking_result
                    })
    return response
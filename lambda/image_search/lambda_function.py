import json
from typing import List
from opensearch_search import get_opensearch_client
from embeddings import *
import boto3

bucket = os.environ.get('bucket_name')

def vector_search(index: str, query_vector: List[float], size: int = 10,vector_field: str = "vector_field"):
    client = get_opensearch_client()
    offset = 0
    collapse_size = int(max(size / 15, 15))

    results = client.search(index = index, body={
                "size": size,
                "query": {"knn": {vector_field: {"vector": query_vector, "k": size}}},
            }
        )
    return results['hits']['hits']



def lambda_handler(event, context):
    
    print("event:",event)
    evt_body = event['queryStringParameters']
    
    url = ""
    if "url" in evt_body.keys():
        url = evt_body['url'].strip()
    print('url:',url)
    
    index = ""
    if "index" in evt_body.keys():
        index = evt_body['index']
    print('index:',index)
    
    task = 'image-search'
    if "task" in evt_body.keys():
        task = evt_body['task']
    print('task:',task)
        
    embeddingType = 'sagemaker'
    if "embeddingType" in evt_body.keys():
        embeddingType = evt_body['embeddingType']
    
    embeddingEndpoint = ""
    if "embeddingEndpoint" in evt_body.keys():
        embeddingEndpoint = evt_body['embeddingEndpoint']
    
    vectorSearchNumber = 3
    if "vectorSearchNumber" in evt_body.keys():
        vectorSearchNumber = int(evt_body['vectorSearchNumber'])
    print('vectorSearchNumber:',vectorSearchNumber)

    vectorScoreThresholds = 0
    if "vectorScoreThresholds" in evt_body.keys() and evt_body['vectorScoreThresholds'] is not None:
        vectorScoreThresholds = float(evt_body['vectorScoreThresholds'])
    print('vectorScoreThresholds:', vectorScoreThresholds)

    vectorField = "image_vector_field"
    if "vectorField" in evt_body.keys():
        vectorField = evt_body['vectorField']
    print('vectorField:', vectorField)
    
    protentialTags = ""
    if "protentialTags" in evt_body.keys():
        protentialTags = evt_body['protentialTags']
    print('protentialTags:',protentialTags)
    
    imageName = ""
    if "imageName" in evt_body.keys():
        imageName = evt_body['imageName']
    print('imageName:',imageName)
    
    product = ""
    if "product" in evt_body.keys():
        product = evt_body['product']
    print('product:',product)
    
    
    prompt = '请找出图片中{product}的图片坐标，给出一个准确的边界框，输出x,y,x1,y1共4个参数，其中x,y代表{product}的左上角的坐标，x1,y1代表{product}右下角的坐标，{product}的图片坐标尽量只保留{product}，输出答案为json格式'
    if "prompt" in evt_body.keys():
        prompt = evt_body['prompt']
    print('prompt:',prompt)
    
    if task == 'image-coordinate' and len(bucket) > 0 and len(imageName) > 0 and len(product) > 0:
        coordinate = get_image_coordinate(bucket, imageName, product, prompt)
        response = {
                "statusCode": 200,
                "headers": {
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,GET'
                },
                "isBase64Encoded": False
            }
        response['body'] = json.dumps(
            {
                'coordinate':coordinate
            }
        ) 
    
    elif task == 'image-search' and (len(url) > 0 or len(imageName) > 0) and len(embeddingEndpoint) >0:
        
        if len(url) > 0:
            image_embedding = get_image_embedding_sagemaker(embeddingEndpoint,url)
        elif len(imageName) > 0 and len(bucket) > 0:
            image_embedding = get_image_embedding_s3(embeddingEndpoint,bucket,imageName)
        results = vector_search(index,image_embedding,size=vectorSearchNumber,vector_field=vectorField)
        products = []
        for result in results:
            score = float(result['_score'])
            metadata = result['_source']['metadata']
            if score >= vectorScoreThresholds:
                products.append({'score':score,'source':metadata})
                
        print('products:',products)
        response = {
                "statusCode": 200,
                "headers": {
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,GET'
                },
                "isBase64Encoded": False
            }
        response['body'] = json.dumps(
            {
                'products': products
            }
        )  
    
    elif task == 'classification' and len(embeddingEndpoint) >0 and len(url) > 0 and len(protentialTags) > 0:
        protentialTags = protentialTags.split(',')
        tag_confidentials = {}
    
        prompts = [f"the product is {item}" for item in protentialTags]
        base64_string = encode_image(url)
        inputs = {"image": base64_string, "prompt": prompts}
        
        output = run_inference(embeddingEndpoint, inputs)
        confidentialScores = output[0]
        print('confidentialScores:',confidentialScores)
        
        tagConfidentials = dict(zip(protentialTags,confidentialScores))
        print('tagConfidentials',tagConfidentials)
        
        response = {
                "statusCode": 200,
                "headers": {
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,GET'
                },
                "isBase64Encoded": False
        }
        response['body'] = json.dumps(
            {
                'tagConfidentials': tagConfidentials
            }
        )
        
        print('tagConfidentials:',tagConfidentials)
        
    elif task == 'opensearch_index':
        index_list = []
        try:
            #get indices list from opensearch
            client = get_opensearch_client()
    
            result = list(client.indices.get_alias().keys())
            
            for indice in result:
                if not indice.startswith("."):
                    index_list.append(indice)
            #         index_list.append({"name": indice, "s3_prefix": "", "aos_indice": indice})
            print(index_list)
            response = {
                "statusCode": 200,
                "headers": {
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,GET'
                },
                "isBase64Encoded": False
            }
            
            response['body'] = json.dumps(index_list)
            
        except Exception as e:
            print(e)
            response = {
                'statusCode': 500,
                'body': json.dumps('Internal Server Error')
            }
    elif task == 'sagemaker_endpoint':
        sagemaker = boto3.client('sagemaker')
        endpoints = sagemaker.list_endpoints()
        # 从响应中提取处于"InService"状态的所有端点的名称
        endpoint_names = [
            endpoint['EndpointName'] for endpoint in endpoints['Endpoints']
            if endpoint['EndpointStatus'] == 'InService'
        ]
        response = {
            "statusCode": 200,
            "headers": {
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,GET'
            },
            "isBase64Encoded": False
        }
        response['body'] = json.dumps(endpoint_names)
        
    else:
        response = {
                'statusCode': 500,
        }
        response['body'] = json.dumps(
            {
                'result':"Paremeters Server Error"
            }
        )
    
    return response
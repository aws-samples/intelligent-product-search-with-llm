import json
from typing import List
from opensearch_search import get_opensearch_client
from embeddings import get_embedding_sagemaker,get_reranker_scores
import boto3

def text_search(index: str, search_term: str, name:str='', keyworks:str='', description:str='', size: int = 10):
    client = get_opensearch_client()
    offset = 0
    collapse_size = int(max(size / 15, 15))
    
    body ={
            "from": offset,
            "size": size,
            "query": {
                "dis_max" : {
                    "queries" : [
                    ],
                    "tie_breaker" : 0.7
                }
            },
            "fields":[
                "_id"
            ]
        }
    
    if len(name) > 0:
        name_query = { "match_bool_prefix" : { "metadata."+name : { "query": search_term, "boost": 1.2 }}}
        body['query']['dis_max']['queries'].append(name_query)
        
    if len(keyworks) > 0:
        keywork_query = { "match_bool_prefix" : { "metadata."+keyworks : { "query": search_term, "boost": 1 }}}
        body['query']['dis_max']['queries'].append(keywork_query)
    
    if len(description) > 0:
        description_query = { "match_bool_prefix" : { "metadata."+description : { "query": search_term, "boost": 1 }}}
        body['query']['dis_max']['queries'].append(description_query)

    results = client.search(index = index, body=body)

    return results['hits']['hits']

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
    
    query = ""
    if "query" in evt_body.keys():
        query = evt_body['query'].strip()
    print('query:',query)
    
    index = ""
    if "index" in evt_body.keys():
        index = evt_body['index']
    print('index:',index)
    
    searchType = 'text'
    if "searchType" in evt_body.keys():
        searchType = evt_body['searchType']
    print('searchType:',searchType)
        
    embeddingType = 'sagemaker'
    if "embeddingType" in evt_body.keys():
        embeddingType = evt_body['embeddingType']
    
    embeddingEndpoint = ""
    if "embeddingEndpoint" in evt_body.keys():
        embeddingEndpoint = evt_body['embeddingEndpoint']

    textSearchNumber = 0
    if "textSearchNumber" in evt_body.keys() and evt_body['textSearchNumber'] is not None:
        textSearchNumber = int(evt_body['textSearchNumber'])
    print('textSearchNumber:', textSearchNumber)
    
    vectorSearchNumber = 0
    if "vectorSearchNumber" in evt_body.keys() and evt_body['vectorSearchNumber'] is not None:
        vectorSearchNumber = int(evt_body['vectorSearchNumber'])
    print('vectorSearchNumber:', vectorSearchNumber)

    vectorScoreThresholds = 0
    if "vectorScoreThresholds" in evt_body.keys() and evt_body['vectorScoreThresholds'] is not None:
        vectorScoreThresholds = float(evt_body['vectorScoreThresholds'])
    print('vectorScoreThresholds:', vectorScoreThresholds)

    textScoreThresholds = 0
    if "textScoreThresholds" in evt_body.keys() and evt_body['textScoreThresholds'] is not None:
        textScoreThresholds = float(evt_body['textScoreThresholds'])
    print('textScoreThresholds:', textScoreThresholds)

    vectorField = "vector_field"
    if "vectorField" in evt_body.keys():
        vectorField = evt_body['vectorField']
    print('vectorField:', vectorField)
    
    language = "chinese"
    if "language" in evt_body.keys():
        language = evt_body['language']
    print('language:', language)
    
    productIdName = ""
    if "productIdName" in evt_body.keys():
        productIdName = evt_body['productIdName']
    print('productIdName:', productIdName)
    
    rerankerEndpoint = ""
    if "rerankerEndpoint" in evt_body.keys():
        rerankerEndpoint = evt_body['rerankerEndpoint']
        
    keyworks = ""
    if "keyworks" in evt_body.keys():
        keyworks = evt_body['keyworks']
    print('keyworks:', keyworks)
    
    description = ""
    if "description" in evt_body.keys():
        description = evt_body['description']
    print('description:', description)
        
    task = 'search'
    if "task" in evt_body.keys():
        task = evt_body['task']
    print('task:',task)
    
    if task == 'search':
        products = []
        product_id_set = set()
        if (searchType == 'text' or searchType == 'mix') and len(index) > 0 and len(query) > 0:
            results = text_search(index,query,productIdName,keyworks,description,size=textSearchNumber)
            for result in results:
                score = float(result['_score'])
                metadata = result['_source']['metadata']
                if score >= textScoreThresholds:
                    if len(productIdName) > 0:
                        product_id = metadata[productIdName]
                        if product_id not in product_id_set:
                            products.append({'score':score,'source':metadata})
                            product_id_set.add(product_id)
                    else:
                        products.append({'score':score,'source':metadata})
           
        if (searchType == 'vector' or searchType == 'mix') and embeddingType == 'sagemaker' and len(index) > 0 and len(query) > 0 and len(embeddingEndpoint) > 0:
            embedding = get_embedding_sagemaker(embeddingEndpoint,query,language=language,is_query=True)
            results = vector_search(index,embedding,size=vectorSearchNumber,vector_field=vectorField)
            for result in results:
                score = result['_score']
                metadata = result['_source']['metadata']
                if score >= vectorScoreThresholds:
                    if len(productIdName) > 0:
                        product_id = metadata[productIdName]
                        if product_id not in product_id_set:
                            products.append({'score':score,'source':metadata})
                            product_id_set.add(product_id)
                    else:
                        products.append({'score':score,'source':metadata})
                        
        if searchType == 'mix' and len(rerankerEndpoint) > 0:
            pairs = []
            for product in products:
                product_name = product['source'][productIdName]
                pair = [query,product_name]
                pairs.append(pair)
    
            scores = get_reranker_scores(pairs,rerankerEndpoint)
            scores = scores['rerank_scores']
            new_products=[]
            for i in range(len(products)):
                new_product = products[i].copy()
                new_product['rerank_score'] = scores[i]
                new_products.append(new_product)
            products = sorted(new_products,key=lambda new_products:new_products['rerank_score'],reverse=True)
            
        
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
        }) 
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

        
import re
import os
import json
import traceback
import urllib.parse
import boto3
from datetime import datetime
import time
from opensearch_search import add_products,get_opensearch_client
from embeddings import get_image_embedding_sagemaker,get_embedding_sagemaker,get_embedding_bedrock,get_embedding_bedrock_multimodal
from model import invoke_model_local,invoke_model_api
import csv

s3_cli = boto3.client('s3')
bucketName = os.environ.get('bucket_name')

model_parameters = {"max_tokens_to_sample": 700,"temperature": 0}
prompt_template = """
you are a e-commerce website product manager, Your task is to extract the product's features base on product infomation, to make it easier for customers to search for the product, 
and the product's key features include: name, category, color, size, material and functionality, The feature text needs to be short, output as json format.

<product information>
{product_information}
</product information>

No need to preface, directly output the product’s key features as json format.

"""

def lambda_handler(event, context):
    
    print("event:",event)
    evt_body = event['queryStringParameters']
    
    print("bucketName:",bucketName)
    
    index = ""
    if "index" in evt_body.keys():
        index = evt_body['index']
    print('index:',index)
    
    imageEmbeddingEndpoint = ""
    if "imageEmbeddingEndpoint" in evt_body.keys():
        imageEmbeddingEndpoint = evt_body['imageEmbeddingEndpoint']
        
    textEmbeddingEndpoint = ""
    if "textEmbeddingEndpoint" in evt_body.keys():
        textEmbeddingEndpoint = evt_body['textEmbeddingEndpoint']
        
    fileName = ""
    if "fileName" in evt_body.keys():
        fileName = evt_body['fileName']
    print("fileName:",fileName)
    
    task = "data_load"
    if "task" in evt_body.keys():
        task = evt_body['task']
    print("task:",task)

    loadType = "text"  # text / image / text_and_image
    if "loadType" in evt_body.keys():
        loadType = evt_body['loadType']
    print("loadType:",loadType)
        
    llmKeywords = "No"  # Yes / No
    if "llmKeywords" in evt_body.keys():
        llmKeywords = evt_body['llmKeywords']
    print("llmKeywords:",llmKeywords)
    
    modelId = ""
    if "modelId" in evt_body.keys():
        modelId = evt_body['modelId']
    print("modelId:",modelId)    
    
    textEmbeddingModelId = ""
    if "textEmbeddingModelId" in evt_body.keys():
        textEmbeddingModelId = evt_body['textEmbeddingModelId']
    print("textEmbeddingModelId:",textEmbeddingModelId)  
    
    imageEmbeddingModelId = ""
    if "imageEmbeddingModelId" in evt_body.keys():
        imageEmbeddingModelId = evt_body['imageEmbeddingModelId']
    print("imageEmbeddingModelId:",imageEmbeddingModelId)  
    
    apiUrl = ""
    if "apiUrl" in evt_body.keys():
        apiUrl = evt_body['apiUrl']
    print("apiUrl:",apiUrl)
        
    imageColoumName = ''
    if "imageColoumName" in evt_body.keys():
        imageColoumName = evt_body['imageColoumName']
    print("imageColoumName:",imageColoumName)
    
    language = 'english'
    if "language" in evt_body.keys():
        language = evt_body['language']
    print("language:",language)
    
    textColoumName = ''
    if "textColoumName" in evt_body.keys():
        textColoumName = evt_body['textColoumName']
    print("textColoumName:",textColoumName)
    textColoumNameList = textColoumName.split(',')
        
    if task == 'data_load' and len(fileName) > 0 and (len(textEmbeddingEndpoint) > 0 or len(imageEmbeddingEndpoint) > 0 \
                                                    or len(textEmbeddingModelId) >0 or len(imageEmbeddingModelId) > 0):
    
        now1 = datetime.now()#begin time
        localFile = "{}/{}".format('/tmp', fileName.split("/")[-1])
        s3_cli.download_file(Bucket=bucketName,
                             Key=fileName,
                             Filename=localFile
                             )
        print("finish download file:",fileName)
        
        product_info_list = []
        product_embedding_list = []
        image_embedding_list = []
        metadatas = []
        error_records = []
        
        csvfile=open(localFile,mode='r',encoding='utf-8')
        reader = [each for each in csv.DictReader(csvfile, delimiter=',')]
        
        
        for line in reader:
            print('line:',line)
            metadata = {}
            image_url = ''
            product_info = ''
            keyFeatures = {}
            
            for key in line.keys():
                key_name = key.replace('\ufeff','').strip()
                value = line[key].strip()
                
                if len(key_name) > 0:
                    metadata[key_name] = value
                    if len(imageColoumName) > 0 and key_name == imageColoumName:
                        image_url = value
                    if len(textColoumNameList) > 0 and key_name in textColoumNameList:
                        if llmKeywords == "Yes":
                            keyFeatures[key_name] = value
                        else:
                            if len(product_info) == 0:
                                product_info = value
                            else:
                                product_info += (',' + value)
                            
            if llmKeywords == "Yes":
                product_information = json.dumps(keyFeatures)
                print('product_information:',product_information)
                prompt = prompt_template.format(product_information=product_information)
                #print('prompt:',prompt)
                if True:
                # try:
                    if len(apiUrl) > 0:
                        search_term = invoke_model_api(prompt,modelId,apiUrl,model_parameters)
                        print('search_term:',search_term)
                    else:
                        print('in the invoke_model_local')
                        search_term = invoke_model_local(prompt,modelId,model_parameters)
                        print('search_term:',search_term)
                    metadata['SEARCH_TERM'] = search_term
                    product_info = search_term
                # except:
                #     print("invoke model to get search term error")

            image_embedding = ''
            if loadType.find('image') >= 0 and len(image_url) > 0:
                try:
                    if len(imageEmbeddingModelId) > 0:
                        image_embedding = get_embedding_bedrock_multimodal(url=image_url,model_id=imageEmbeddingModelId)
                    elif len(imageEmbeddingEndpoint) > 0:
                        image_embedding = get_image_embedding_sagemaker(imageEmbeddingEndpoint,image_url)
                    print('finish image embedding')
                except:
                    error_records.append(metadata)
                    print("image embedding error")
            
            text_embedding = ''
            if loadType.find('text') >= 0 and len(product_info) > 0:
                if True:
                # try:
                    if len(textEmbeddingModelId) > 0:
                        text_embedding = get_embedding_bedrock(product_info,textEmbeddingModelId)
                    elif len(textEmbeddingEndpoint) > 0:
                        text_embedding = get_embedding_sagemaker(textEmbeddingEndpoint,product_info,language=language)
                    print('finish text embedding')
                # except:
                #     error_records.append(metadata)
                #     print("text embedding error")
                    
            if loadType.find('image') >= 0 and loadType.find('text') >= 0:
                if len(image_embedding) == 0 or len(text_embedding) == 0:
                    continue
            elif loadType.find('image') >= 0 and len(image_embedding) == 0:
                continue
            elif loadType.find('text') >= 0 and len(text_embedding) == 0:
                continue
            
            metadatas.append(metadata)
            if len(product_info) > 0:
                product_info_list.append(product_info)
            if len(text_embedding) > 0:
                product_embedding_list.append(text_embedding)
            if len(image_embedding) > 0:
                image_embedding_list.append(image_embedding)
                
        print('product_info_list len:',len(product_info_list))
        print('metadatas len:',len(metadatas))
        print('product_embedding_list len:',len(product_embedding_list))
                
        if len(image_embedding_list) > 0 or len(product_embedding_list) > 0:
            add_products(index,product_info_list,product_embedding_list,metadatas,image_embedding_list)
        
        print('finish add products to opensearch,index is:' + index)
        now2 = datetime.now()
        print("Total File import takes time:",now2-now1)
        
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
                'result':"finish load the file:" + fileName,
                'records':len(metadatas),
                'error_records':error_records
            }
        )
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
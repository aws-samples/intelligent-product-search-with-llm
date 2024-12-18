import boto3
import botocore
import json
import base64
import requests
from PIL import Image
from io import BytesIO
import os

def get_embedding_bedrock(inputs:str,model_id:str="amazon.titan-embed-text-v2:0",dimensions:int=1024):
    bedrock = boto3.client(service_name='bedrock-runtime')
    accept = "application/json"
    contentType = "application/json"
    
    body = {}
    if model_id.find('cohere') >=0:
        body = {'texts':[inputs],"input_type":"search_document"}
    elif model_id.find('amazon') >=0:
        body = {'inputText':inputs,"dimensions":dimensions,"normalize": True}
    
    body = json.dumps(body)
    response = bedrock.invoke_model(
        body=body, modelId=model_id, accept=accept, contentType=contentType
    )
    response_body = json.loads(response.get("body").read())
    
    if model_id.find('cohere') >=0:
        response = response_body['embeddings'][0]
    elif model_id.find('amazon') >=0:
        response = response_body['embedding']
    
    return response

def get_embedding_bedrock_multimodal(inputs:str='',url:str='',image_name:str='',bucket:str='',model_id:str="amazon.titan-embed-image-v1"):
    bedrock = boto3.client(service_name='bedrock-runtime')
    accept = "application/json"
    contentType = "application/json"
    body = {}
    
    if len(inputs) > 0:
        body = {'inputText':inputs}
        
    if len(url) > 0:
        image = Image.open(BytesIO(requests.get(url).content))
        image_string = encode_image_base64(image)
        body = {'inputImage':image_string}
    elif len(image_name) > 0 and len(bucket) > 0:
        s3 = boto3.client('s3')
        image_object = s3.get_object(Bucket=bucket, Key=image_name)
        file_stream = image_object['Body']
        image = Image.open(file_stream)
        image_string = encode_image_base64(image)
        body = {'inputImage':image_string}
        
    body = json.dumps(body)
    
    response = bedrock.invoke_model(
        body=body, modelId=model_id, accept=accept, contentType=contentType
    )
    response_body = json.loads(response.get("body").read())
    return response_body['embedding']


def get_embedding_sagemaker(endpoint_name: str, inputs: str, language: str = 'chinese',is_query: bool=False):
    instruction = "为这个句子生成表示以用于检索相关文章："
    if language == 'english':
        instruction = "Represent this sentence for searching relevant passages:"
    inputs = {"inputs": inputs, "is_query":is_query,"instruction":instruction}
    response = run_inference(endpoint_name, inputs)
    return response[0]
    
def encode_image_base64(image):
    print(image.size)
    max_size = 1600
    if image.size[0] > max_size:
        image = image.resize((max_size,int(image.size[1]*max_size / image.size[0])))
        print('resize image size:',image.size)
    output_buffer = BytesIO()
    image.save(output_buffer, format='JPEG')
    byte_data = output_buffer.getvalue()
    image_base64 = base64.b64encode(byte_data).decode("utf-8")
    return image_base64
    
    
def encode_image(url,resize:bool=False):
    if resize:
        image = Image.open(BytesIO(requests.get(url).content))
        base64_string = encode_image_base64(image)
    else:    
        img_str = base64.b64encode(requests.get(url).content)
    base64_string = img_str.decode("utf-8")
    return base64_string

def get_image_embedding_sagemaker(endpoint_name: str, url: str):
    image_embedding = ''
    if len(endpoint_name) >0 and len(url) > 0:
        image = Image.open(BytesIO(requests.get(url).content))
        image_string = encode_image_base64(image)
        inputs = {"image": image_string}
        output = run_inference(endpoint_name, inputs)
        image_embedding = output['image_embedding'][0]
    return image_embedding
    
def get_image_embedding_s3(endpoint_name: str, bucket:str, image_name: str):
    image_embedding = ''
    if len(endpoint_name) >0 and len(image_name) > 0:
        
        s3 = boto3.client('s3')
        image_object = s3.get_object(Bucket=bucket, Key=image_name)
        file_stream = image_object['Body']
        image = Image.open(file_stream)
        image_string = encode_image_base64(image)
        inputs = {"image": image_string}
        output = run_inference(endpoint_name, inputs)
        image_embedding = output['image_embedding'][0]
    return image_embedding
    
def run_inference(endpoint_name, inputs):
    smr_client = boto3.client("sagemaker-runtime")
    response = smr_client.invoke_endpoint(EndpointName=endpoint_name, Body=json.dumps(inputs))
    return json.loads(response["Body"].read().decode("utf-8"))
    
def get_reranker_scores(pairs, endpoint_name):
    smr_client = boto3.client("sagemaker-runtime")
    response_model = smr_client.invoke_endpoint(
        EndpointName=endpoint_name,
        Body=json.dumps(
            {
                "inputs": pairs
            }
        ),
        ContentType="application/json",
    )
    output = json.loads(response_model['Body'].read().decode('utf8'))
    return output
    
    
def invoke_claude_3_multimodal(prompt, base64_image_data,model_id:str="anthropic.claude-3-sonnet-20240229-v1:0"):
        """
        Invokes Anthropic Claude 3 Sonnet to run a multimodal inference using the input
        provided in the request body.

        :param prompt:            The prompt that you want Claude 3 to use.
        :param base64_image_data: The base64-encoded image that you want to add to the request.
        :return: Inference response from the model.
        """

        # Initialize the Amazon Bedrock runtime client
        client = boto3.client(
            service_name="bedrock-runtime", region_name=os.environ.get("AWS_REGION")
        )

        # Invoke the model with the prompt and the encoded image
        
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "temperature": 0.01,
            "system":"请回答问题",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": base64_image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        }
                    ],
                }
            ],
        }
    
        try:
            response = client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body),
            )

            response_body = json.loads(response.get("body").read().decode())
            return response_body.get("content")[0].get("text")

        except botocore.exceptions.ClientError as err:
            print(
                "Couldn't invoke Claude 3 Sonnet. Here's why: %s: %s",
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
    
def get_product_coordinate(product,image:Image,prompt:str,model_id:str):
    prompt = prompt.format(product=product)
    
    print('image size:',image.size)
    # if image.size[0] > 500:
    #     image = image.resize((500,int(image.size[1]*500 / image.size[0])))
    #     print('resize image size:',image.size)

    output_buffer = BytesIO()
    image.save(output_buffer, format='JPEG')
    byte_data = output_buffer.getvalue()
    base64_image_data = base64.b64encode(byte_data).decode("utf-8")
    return invoke_claude_3_multimodal(prompt, base64_image_data,model_id)
    
def get_image_coordinate(bucket:str, image_name: str,product: str, prompt:str,model_id:str):
    if len(bucket) >0 and len(image_name) > 0 and len(product) > 0: 
        
        s3 = boto3.client('s3')
        image_object = s3.get_object(Bucket=bucket, Key=image_name)
        file_stream = image_object['Body']
        image = Image.open(file_stream)
        
        product_coordinate = get_product_coordinate(product,image,prompt,model_id)
        print('product_coordinate:',product_coordinate)
            
    return product_coordinate
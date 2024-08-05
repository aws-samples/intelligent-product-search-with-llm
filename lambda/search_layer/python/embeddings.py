import boto3
import botocore
import json
import base64
import requests
from PIL import Image
from io import BytesIO
import os

smr_client = boto3.client("sagemaker-runtime")

def get_embedding_sagemaker(endpoint_name: str, inputs: str, language: str = 'chinese',is_query: bool=False):
    instruction = "为这个句子生成表示以用于检索相关文章："
    if language == 'english':
        instruction = "Represent this sentence for searching relevant passages:"
    inputs = {"inputs": inputs, "is_query":is_query,"instruction":instruction}
    response = run_inference(endpoint_name, inputs)
    return response[0]
    
def encode_image(url):
    img_str = base64.b64encode(requests.get(url).content)
    base64_string = img_str.decode("latin1")
    return base64_string

def get_image_embedding_sagemaker(endpoint_name: str, url: str):
    image_embedding = ''
    if len(endpoint_name) >0 and len(url) > 0:
        base64_string = encode_image(url)
        inputs = {"image": base64_string}
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
        
        output_buffer = BytesIO()
        image.save(output_buffer, format='JPEG')
        byte_data = output_buffer.getvalue()
        image_base64 = base64.b64encode(byte_data).decode("utf-8")
        
        inputs = {"image": image_base64}
        output = run_inference(endpoint_name, inputs)
        image_embedding = output['image_embedding'][0]
    return image_embedding
    
def run_inference(endpoint_name, inputs):
    response = smr_client.invoke_endpoint(EndpointName=endpoint_name, Body=json.dumps(inputs))
    return json.loads(response["Body"].read().decode("utf-8"))
    
def get_reranker_scores(pairs, endpoint_name):
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
    
    
def invoke_claude_3_multimodal(prompt, base64_image_data):
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
        model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
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
    
def get_product_coordinate(product,image:Image,prompt:str):
    prompt = prompt.format(product=product)
    
    print('image size:',image.size)
    if image.size[0] > 500:
        image = image.resize((500,int(image.size[1]*500 / image.size[0])))
        print('resize image size:',image.size)

    output_buffer = BytesIO()
    image.save(output_buffer, format='JPEG')
    byte_data = output_buffer.getvalue()
    base64_image_data = base64.b64encode(byte_data).decode("utf-8")
    return invoke_claude_3_multimodal(prompt, base64_image_data)
    
def get_image_coordinate(bucket:str, image_name: str,product: str, prompt:str):
    if len(bucket) >0 and len(image_name) > 0 and len(product) > 0: 
        
        s3 = boto3.client('s3')
        image_object = s3.get_object(Bucket=bucket, Key=image_name)
        file_stream = image_object['Body']
        image = Image.open(file_stream)
        
        product_coordinate = get_product_coordinate(product,image,prompt)
        print('product_coordinate:',product_coordinate)
            
    return product_coordinate
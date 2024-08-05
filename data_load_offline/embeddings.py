import boto3
import json
import base64
import requests

smr_client = boto3.client("sagemaker-runtime")

def get_embedding_sagemaker(endpoint_name: str, inputs: str, language: str = 'chinese'):
    is_query = False
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
    
def run_inference(endpoint_name, inputs):
    response = smr_client.invoke_endpoint(EndpointName=endpoint_name, Body=json.dumps(inputs))
    return json.loads(response["Body"].read().decode("utf-8"))
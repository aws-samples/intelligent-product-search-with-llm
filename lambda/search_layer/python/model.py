import boto3
import json
from typing import Dict,Any
from bedrockAdapter import BedrockAdapter
import requests

bedrock = boto3.client(service_name='bedrock-runtime')

def invoke_model_local(prompt: str,model_id:str,model_kwargs: Dict[str, Any]):
    
    provider = model_id.split(".")[0]
    model_kwargs['modelId'] = model_id
    modle_input = BedrockAdapter.prepare_input(provider,prompt,model_kwargs)
    body = json.dumps(modle_input)
    #print('body:',body)
    try:
        accept = "application/json"
        contentType = "application/json"
        response = bedrock.invoke_model(
            body=body, modelId=model_id, accept=accept, contentType=contentType
        )
        function_call_response = BedrockAdapter.prepare_output(provider,response)
        # function_call_response = json.loads(response.get("body").read().decode())
        return function_call_response
    
    except Exception as e:
        raise ValueError(f"Error raised by bedrock service: {e}")
        
def request_model(url):
    response = requests.get(url)
    result = response.text
    # print('result:',result)
    result = json.loads(result)
    answer = result['answer']
    return answer
        
def invoke_model_api(prompt: str,model_id:str,api_url:str,model_kwargs: Dict[str, Any]):
    url = api_url + '/bedrock?'
    
    url += ('prompt='+prompt)
    url += ('&modelId='+model_id)
    if len(model_kwargs) > 0:
        for key in model_kwargs.keys():
            url += ('&' + str(key) + '=' + str(model_kwargs[key]))
    try:
        answer = request_model(url)
        return answer
    except Exception as e:
        try:
            answer = request_model(url)
            return answer
        except Exception as e:
            raise ValueError(f"Error raised by bedrock api service: {e}")

    
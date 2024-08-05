import requests
import streamlit as st
import streamlit.components.v1 as components
import json
import time
from datetime import datetime
import pandas as pd
import boto3
from botocore.exceptions import ClientError
import os
import ast
import pandas as pd
import shutil

#region = os.environ.get('AWS_REGION')
#account = os.environ.get('AWS_ACCOUNT_ID')
#print('region:',region)
#print('account:',account)


def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        print(e)
        return False
    return True


def split_csv(file_name,output_dir,row_per_file:int=10):
        chunk_iterator = pd.read_csv(file_name, chunksize=row_per_file)
        file_number = 1
        file_list = []
        for chunk in chunk_iterator:
                new_file_name = f'{output_dir}/data{file_number}.csv'
                chunk.to_csv(new_file_name,index=False)
                file_list.append(new_file_name)
                file_number += 1

        return file_list


def get_sagemaker_endpoint(invoke_url):
    url = invoke_url + '/data_load?'
    url += ('&task=sagemaker_endpoint')
    print('url:',url)
    response = requests.get(url)
    response = ast.literal_eval(response.text)
    print('sagemaker endpoint:',response)
    return response

def get_openserch_index(invoke_url):
    url = invoke_url + '/data_load?'
    url += ('&task=opensearch_index')
    print('url:',url)
    response = requests.get(url)
    response = ast.literal_eval(response.text)
    print('opensearch index:',response)
    return response

def data_load(invoke_url,index,file_name,load_type,text_coloum_name: str='',llm_keywords: str='',image_coloum_name: str='',text_endpoint_name: str='',image_endpoint_name: str='',model_id: str='',api_url: str=''):
    url = invoke_url + '/data_load?'
    url += ('&index='+index)
    url += ('&task=data_load')
    url += ('&fileName='+file_name)
    url += ('&loadType='+load_type)

    if load_type.find('text') >= 0 and len(text_coloum_name) > 0:
        url += ('&textColoumName='+text_coloum_name)

    if load_type.find('text') >= 0 and len(llm_keywords) > 0:
        url += ('&llmKeywords='+llm_keywords)    

    if load_type.find('text') >= 0 and llm_keywords == 'Yes' and len(model_id) > 0:
        url += ('&modelId='+model_id)

    if load_type.find('text') >= 0 and llm_keywords == 'Yes' and len(api_url) > 0:
        url += ('&apiUrl='+api_url)

    if load_type.find('image') >= 0 and len(image_coloum_name) > 0:
        url += ('&imageColoumName='+image_coloum_name)

    if load_type.find('text') >= 0 and len(text_endpoint_name) > 0:
        url += ('&textEmbeddingEndpoint='+text_endpoint_name)
    
    if load_type.find('image') >= 0 and len(image_endpoint_name) > 0:
        url += ('&imageEmbeddingEndpoint='+image_endpoint_name)

    print('url:',url)
    now1 = datetime.now()
    response = requests.get(url)
    now2 = datetime.now()
    print('request task time:',now2-now1)
    response = json.loads(response.text)
    print('response:',response)
    return response

# Re-initialize the chat
def new_file() -> None:
    st.session_state.uploaded_file = ''

    
with st.sidebar:
    invoke_url = st.text_input(
        "Please input a data load api url",
        "https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod",
        key="image_search_invoke_url",
    )
    
    account = st.text_input(
        "Please input aws account:",
        "xxxxxxxxxxx",
        key="account",
    )
    region = st.text_input(
        "Please input region:",
        "us-east-1",
        key="region",
    )

    sagemaker_endpoint = get_sagemaker_endpoint(invoke_url)
    openserch_index = get_openserch_index(invoke_url)
    data_opensearch_index = st.selectbox("Please Select opensearch index",openserch_index)
    new_index = st.text_input("New index","")
    load_type  = st.radio("Load Type",["text","image",'text_and_image'])
  
    text_coloum_name = ''
    text_endpoint_name = ''
    if load_type.find('text') >=0:
        text_endpoint_name = st.selectbox("Please Select text embedding sagemaker endpoint", sagemaker_endpoint)
        text_coloum_name = st.text_input("Text embedding coloum name,Separate multiple fields using ,","NAME,CATEGORY,KEYWORDS,SHORT_DESCRIPTION")
        llm_keywords  = st.radio("Use LLM to extract keywords",["Yes","No"])
        if llm_keywords == "Yes":
            model_id = st.text_input("Input the model id","anthropic.claude-3-sonnet-20240229-v1:0")
            api_url = st.text_input("If call another region's bedrock, Input the api url","https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod")

    image_coloum_name = ''
    image_endpoint_name = ''
    if load_type.find('image') >=0:
        image_endpoint_name = st.selectbox("Please Select image embedding sagemaker endpoint", sagemaker_endpoint)
        image_coloum_name = st.text_input("Image coloum name","mainImage")

    size = 10
    if load_type == 'text' and llm_keywords == 'No':
        size = 100
    elif load_type == 'text' and llm_keywords == 'Yes':
        size = 6

# Add a button to start a new chat
st.sidebar.button("New File", on_click=new_file, type='primary')


st.session_state.uploaded_file = st.file_uploader("Upload File",type=['csv'])


if st.session_state.uploaded_file:
    
    index = data_opensearch_index
    if len(new_index) > 0:
        index = new_index
    
    if len(index) == 0:
        st.write('Index is None!')

    elif account is None:
        st.write('account is None!')

    elif region is None:
        st.write('region is None!')

    elif load_type.find('text') >=0 and text_coloum_name is None:
        st.write('Text coloum name is None!')

    elif load_type.find('image') >=0 and image_coloum_name is None:
        st.write('Image coloum name is None!')

    else:
        bucket_name = "intelligent-search-data" + "-" + account + "-" + region
        print('name:',st.session_state.uploaded_file.name)
        file_name = st.session_state.uploaded_file.name.split('.')[0] + '-' + str(time.time()) + '.' + st.session_state.uploaded_file.name.split('.')[1]

        data = pd.read_csv(st.session_state.uploaded_file)
        data.to_csv(file_name,index=False)

        data_dir = file_name.split('.')[0]
        os.mkdir(data_dir)
        file_list = split_csv(file_name,data_dir,size)
        total_number = 0
        total_error_records = []
        percent_complete = 0
        if len(file_list) > 0:
            progress_text = "Data is loading to OpenSearch. Please wait."
            my_bar = st.progress(0, text=progress_text)

            with st.empty():
                for i in range(len(file_list)):
                    split_data = pd.read_csv(file_list[i])
                    if len(split_data) > 0:
                        split_file_name = file_list[i]
                        object_name = split_file_name.replace('/','-')
                        upload_file(split_file_name,bucket_name,object_name)
                        
                        try:
                            response = data_load(invoke_url,index,object_name,load_type,text_coloum_name,llm_keywords,image_coloum_name,text_endpoint_name,image_endpoint_name,model_id,api_url)
                        except Exception as e:
                            print(e)
                            
                        if 'message' in response.keys() and response['message'] == 'Endpoint request timed out':
                            response = data_load(invoke_url,index,object_name,load_type,text_coloum_name,llm_keywords,image_coloum_name,text_endpoint_name,image_endpoint_name,model_id,api_url)
                            if 'result' not in response.keys():
                                continue
                        
                        result = response['result']
                        print("result:",result)
                        records = response['records']
                        error_records = response['error_records']

                        total_number += int(records)
                        st.write('Number of records successfully loaded: ' + str(total_number))

                        if len(total_error_records) > 0:
                            st.write('Error records: ')
                            if len(error_records) > 0:
                                total_error_records.extend(error_records)
                            for record in total_error_records:
                                st.write(record)
                    
                    if len(file_list) <= 100 and percent_complete + int(100/len(file_list)) <= 100:
                        percent_complete += int(100/len(file_list))
                        my_bar.progress(percent_complete, text=progress_text)
                    else:
                        if i % int(len(file_list)/100) == 0 and percent_complete + 1 <= 100:
                            percent_complete += 1
                            my_bar.progress(percent_complete, text=progress_text)

                my_bar.progress(100, text="finish load the data!")
                

        os.remove(file_name)
        shutil.rmtree(data_dir)
import requests
import streamlit as st
import streamlit.components.v1 as components
import json
from datetime import datetime
import pandas as pd
from PIL import Image
from io import BytesIO
import base64
import boto3
from botocore.exceptions import ClientError
import time
import os
import ast

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
        return False
    return True


def get_sagemaker_endpoint(invoke_url):
    url = invoke_url + '/image_search?'
    url += ('&task=sagemaker_endpoint')
    print('url:',url)
    response = requests.get(url)
    response = ast.literal_eval(response.text)
    print('sagemaker endpoint:',response)
    return response

def get_openserch_index(invoke_url):
    url = invoke_url + '/image_search?'
    url += ('&task=opensearch_index')
    print('url:',url)
    response = requests.get(url)
    response = ast.literal_eval(response.text)
    print('opensearch index:',response)
    return response

def get_image_coordinate(image_name,product,bucket_name,invoke_url,bucket:str='',prompt:str=''):
    url = invoke_url + '/image_search?'
    new_image_name = image_name.split('.')[0] + '-' + str(time.time()) + '.' + image_name.split('.')[-1]
    upload_file(image_name,bucket_name,new_image_name)
    url += ('&imageName='+new_image_name)
    if len(product) > 0:
        url += ('&product='+product)
    if len(bucket) > 0:
        url += ('&bucket='+bucket)
    if len(prompt) > 0:
        url += ('&prompt='+prompt)

    url += ('&task=image-coordinate')

    print('url:',url)
    response = requests.get(url)
    result = response.text
    result = json.loads(result)
    print("result:",result)
    coordinate = result['coordinate']
    if coordinate.find('\n\n') > 0:
        coordinate = coordinate.split('\n\n')[1].strip()
    coordinate = json.loads(coordinate)
    print('coordinate:',coordinate)

    return coordinate

def image_search_url(image_url,index,invoke_url,endpoint_name,vectorSearchNumber):
    url = invoke_url + '/image_search?'
    if len(image_url) > 0:
        url += ('&url='+image_url)
    url += ('&index='+index)
    url += ('&task=image-search')
    url += ('&embeddingEndpoint='+endpoint_name)
    url += ('&vectorSearchNumber='+str(vectorSearchNumber))

    print('url:',url)
    response = requests.get(url)
    result = response.text
    result = json.loads(result)
    print("result:",result)
    products = result['products']
    return products


def image_search_localfile(image_name,index,invoke_url,bucket_name,endpoint_name,vectorSearchNumber):
    url = invoke_url + '/image_search?'
    new_image_name = image_name.split('.')[0] + '-' + str(time.time()) + '.' + image_name.split('.')[-1]
    upload_file(image_name,bucket_name,new_image_name)
    url += ('&imageName='+new_image_name)
    url += ('&index='+index)
    url += ('&task=image-search')
    url += ('&embeddingEndpoint='+endpoint_name)
    url += ('&vectorSearchNumber='+str(vectorSearchNumber))

    print('url:',url)
    response = requests.get(url)
    result = response.text
    result = json.loads(result)
    print("result:",result)
    products = result['products']

    return products


# Re-initialize the chat
def new_image() -> None:
    st.session_state.url = ''
    st.session_state.uploaded_file = ''
    
with st.sidebar:

    search_invoke_url = st.text_input(
        "Please input a image search api url",
        "",
        key="image_search_invoke_url",
    )

    account = st.text_input(
        "Please input aws account:",
        "",
        key="account",
    )
    region = st.text_input(
        "Please input region:",
        "",
        key="region",
    )

    sagemaker_endpoint = get_sagemaker_endpoint(search_invoke_url)
    openserch_index = get_openserch_index(search_invoke_url)
    
    image_search_sagemaker_endpoint = st.selectbox("Please Select image embedding sagemaker endpoint",sagemaker_endpoint)
    index = st.selectbox("Please Select opensearch index",openserch_index)

    vectorSearchNumber = st.slider("Image Search Number",min_value=1, max_value=10, value=3, step=1)
    image_coloum_name = st.text_input(label="Image coloum name", value="mainImage")
    product_catagory = st.text_input(label="Image search catagory", value="")

# Add a button to start a new chat
st.sidebar.button("New Image", on_click=new_image, type='primary')

st.session_state.url = st.text_input(label="Please input image URL", value="")
st.session_state.uploaded_file = st.file_uploader("Upload Image",type=['png', 'jpg','jpeg'])


#if st.button('Image Search'):
if st.session_state.url or st.session_state.uploaded_file:
    if len(st.session_state.url) ==0 and  not st.session_state.uploaded_file:
        st.write("Image is None")
    elif len(search_invoke_url) == 0:
        st.write("Search invoke url is None")
    elif len(index) == 0:
        st.write("Opensearch index is None")
    elif len(image_search_sagemaker_endpoint) == 0:
        st.write("Search sagemaker endpoint is None")
    elif len(account) == 0:
        st.write('account is None!')
    elif len(region) == 0:
        st.write('region is None!')

    else:
        bucket_name = "intelligent-image-search-data" + "-" + account + "-" + region
        st.write('输入图片：')
        products = []
        if len(st.session_state.url) > 0:
            st.image(st.session_state.url)
            products = image_search_url(st.session_state.url,index,search_invoke_url,image_search_sagemaker_endpoint,vectorSearchNumber)
        elif st.session_state.uploaded_file:
            st.image(st.session_state.uploaded_file)
            image = Image.open(st.session_state.uploaded_file)
            image.save(st.session_state.uploaded_file.name)

            if len(product_catagory) == 0 :
                products = image_search_localfile(st.session_state.uploaded_file.name,index,search_invoke_url,bucket_name,image_search_sagemaker_endpoint,vectorSearchNumber)
            else:
                coordinate = get_image_coordinate(st.session_state.uploaded_file.name,product_catagory,bucket_name,search_invoke_url)
                products = []
                if len(coordinate) > 0:
                    image = Image.open(st.session_state.uploaded_file.name)
                    print('image size:',image.size)
                    if image.size[0] > 500:
                        image = image.resize((500,int(image.size[1]*500 / image.size[0])))
                    print('resize image size:',image.size)

                    cropped_iamge = image.crop((coordinate['x'],coordinate['y'],coordinate['x1'],coordinate['y1']))
                    st.write('提取产品图片：')
                    st.image(cropped_iamge)
                    cropped_iamge.save('cropped_'+st.session_state.uploaded_file.name)
                    products = image_search_localfile('cropped_'+st.session_state.uploaded_file.name,index,search_invoke_url,bucket_name,image_search_sagemaker_endpoint,vectorSearchNumber)
                    os.remove('cropped_'+st.session_state.uploaded_file.name)

            os.remove(st.session_state.uploaded_file.name)
        items_num = len(products)
        if items_num == 0:
            response = '没找到符合要求的商品，请试试其它问题吧！'
            st.write(response)
        elif items_num >= 1:
            st.write('搜索结果：')
            col1, col2, col3 = st.columns(3)
            image_list = []
            scores_list = []
            source_list = []
                
            for product in products:
                score = product['score']
                scores_list.append(str(score))
                source = product['source']
                source_list.append(source)
                
                if image_coloum_name in source.keys():
                    image_list.append(source[image_coloum_name])

            with col1:
                for i in range(items_num):
                    col = i % 3
                    if col == 0:
                        st.image(image_list[i])
                        with st.expander("详情"):
                            score = scores_list[i]
                            score_str = f"<p style='font-size:12px;'>score:{score}</p>"
                            st.markdown(score_str,unsafe_allow_html=True)
                            
                            source = source_list[i]
                            for key in source.keys():
                                value = source[key].strip()
                                info_str = f"<p style='font-size:12px;'>{key}:{value}</p>"
                                st.markdown(info_str,unsafe_allow_html=True)

            with col2:
                for i in range(items_num):
                    col = i % 3
                    if col == 1:
                        st.image(image_list[i])
                        with st.expander("详情"):
                            score = scores_list[i]
                            score_str = f"<p style='font-size:12px;'>score:{score}</p>"
                            st.markdown(score_str,unsafe_allow_html=True)
                            
                            source = source_list[i]
                            for key in source.keys():
                                value = source[key].strip()
                                info_str = f"<p style='font-size:12px;'>{key}:{value}</p>"
                                st.markdown(info_str,unsafe_allow_html=True)
                            
            with col3:
                for i in range(items_num):
                    col = i % 3
                    if col == 2:
                        st.image(image_list[i])
                        with st.expander("详情"):
                            score = scores_list[i]
                            score_str = f"<p style='font-size:12px;'>score:{score}</p>"
                            st.markdown(score_str,unsafe_allow_html=True)
                            
                            source = source_list[i]
                            for key in source.keys():
                                value = source[key].strip()
                                info_str = f"<p style='font-size:12px;'>{key}:{value}</p>"
                                st.markdown(info_str,unsafe_allow_html=True)
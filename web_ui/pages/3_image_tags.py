import requests
import streamlit as st
import streamlit.components.v1 as components
import json
from datetime import datetime
import pandas as pd
import boto3
from botocore.exceptions import ClientError
import ast

def get_sagemaker_endpoint(invoke_url):
    url = invoke_url + '/image_search?'
    url += ('&task=sagemaker_endpoint')
    print('url:',url)
    response = requests.get(url)
    response = ast.literal_eval(response.text)
    print('sagemaker endpoint:',response)
    return response

def get_protential_tags(image_url,protential_tags,invoke_url,endpoint_name):
    url = invoke_url + '/image_search?'
    url += ('&url='+image_url)
    url += ('&task=classification')
    url += ('&protentialTags='+protential_tags)
    url += ('&embeddingEndpoint='+endpoint_name)
    
    print('url:',url)
    response = requests.get(url)
    result = response.text
    result = json.loads(result)
    print("result:",result)
    tag_confidentials = result['tagConfidentials']
    
    return tag_confidentials


# Re-initialize the chat
def new_image() -> None:
    st.session_state.url = ''
    
with st.sidebar:

    search_invoke_url = st.text_input(
        "Please input a image tag api url",
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
    image_tags_sagemaker_endpoint = st.selectbox("Please Select image embedding sagemaker endpoint",sagemaker_endpoint)
    
    threshold = st.slider("Tag threshold",min_value=0.0, max_value=1.0, value=0.3, step=0.01)

# Add a button to start a new chat
st.sidebar.button("New Image", on_click=new_image, type='primary')

st.session_state.url = st.text_input(label="Please input image URL", value="")

color_tags = st.text_input("color protential tags","white,black,green,pink,blue,gold,organge,gray,brown,red")
category_tags = st.text_input("category protential tags","Hole Shoes,Sandals,Half Slippers,Beach Shoes,Sneakers,Running Shoes,Canvas Shoes,Water Shoes,Hiking Shoes")
material_tags = st.text_input("material protential tags","Flat Bottom,Thick Bottom,Rubber Sole,Mesh Surface,Drain Hole,Anti-Slippery,Non-slip Soles,Hollow,Plastic")
protential_tags_list = []
protential_tags_list.append(color_tags)
protential_tags_list.append(category_tags)
protential_tags_list.append(material_tags)

if st.session_state.url:
    if len(st.session_state.url) ==0:
        st.write("Image url is None")
    elif len(search_invoke_url) == 0:
            st.write("Search invoke url is None")

    st.write('输入图片：')
    st.image(st.session_state.url)


    if len(image_tags_sagemaker_endpoint) == 0:
        st.write("Iamge tags sagemaker endpoint is None")
    else:
        
        for protential_tags in protential_tags_list:
            tag_confidentials = get_protential_tags(st.session_state.url,protential_tags,search_invoke_url,image_tags_sagemaker_endpoint)
            
            st.write('tag confidentials:')
            category = [tag for tag in tag_confidentials if tag_confidentials[tag] > threshold]
        
            tags = list(tag_confidentials.keys())
            scores = [round(score,3) for score in tag_confidentials.values()]
            data = {
                "category": tags,
                "scores": scores
            }
            df = pd.DataFrame(data)
            st.dataframe(df)
            st.write('Category:')
            st.write(category)
            st.write('--------------------------------')
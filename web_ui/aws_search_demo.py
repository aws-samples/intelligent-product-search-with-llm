import streamlit as st

st.set_page_config(
    page_title = 'aws search solution'
)

st.write('# AWS Product Search Solution')

st.markdown(
    """
    AWS Product Search Solution is a solution for improving e-commerce product search results. Its main features include:
    ### product search
    - Text search: Search by matching the query text entered by the user with the product description text
    - Vector search: Search by calculating the vector similarity between the query text vector input by the user and the product description text vector.
    - Hybrid search: supports both text search and vector search
    
    ### Image search
    - Vector search: Search by calculating the vector similarity between the user input image vector and the product image vector

    ### Image tagging
    - Vector tagging: Tagging by calculating the vector similarity between the user input image vector and the label information vector
    
    """
)
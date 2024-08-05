import os
import aws_cdk as cdk
from lib.ss_image_search_stack import ImageSearchStack
from lib.ss_text_search_stack import TextSearchStack
from lib.ss_search_notebook import SearchNotebookStack
from lib.ss_opensearch_stack import ProductOpenSearchStack
from lib.ss_data_load_stack import DataLoadStack
from lib.ss_bedrock_invoke_stack import BedrockStack
from lib.ss_personalize_stack import PersonalizeRankingStack


ACCOUNT = os.getenv('AWS_ACCOUNT_ID', '')
REGION = os.getenv('AWS_REGION', '')
AWS_ENV = cdk.Environment(account=ACCOUNT, region=REGION)
env = AWS_ENV
print(env)
app = cdk.App()


search_notebook_stack = SearchNotebookStack(app, "SearchNotebookStack", env=env)
product_opensearch_stack = ProductOpenSearchStack(app, "ProductOpenSearchStack", env=env)
data_load_stack = DataLoadStack(app,"DataLoadStack",env=env)

if app.node.try_get_context('text_search'):
    text_search_stack = TextSearchStack(app, "TextSearchStack",env=env)

if app.node.try_get_context('image_search'):
    image_search_stack = ImageSearchStack(app, "ImageSearchStack",env=env)
    
if app.node.try_get_context('bedrock_invoke'):
    bedrock_stack = BedrockStack(app, "BedrockStack",env=env)

if app.node.try_get_context('personalize'):
    personalize_stack = PersonalizeRankingStack(app, "PersonalizeRankingStack",env=env)


app.synth()
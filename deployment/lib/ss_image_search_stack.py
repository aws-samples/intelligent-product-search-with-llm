from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_iam as iam,
    aws_apigateway as apigw,
    aws_lambda as _lambda,
    RemovalPolicy,
    Duration
)
import os

class ImageSearchStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        # configure the lambda role
        _image_search_role_policy = iam.PolicyStatement(
            actions=[
                'sagemaker:InvokeEndpointAsync',
                'sagemaker:InvokeEndpoint',
                'sagemaker:ListEndpoints',
                'lambda:AWSLambdaBasicExecutionRole',
                'lambda:InvokeFunction',
                'secretsmanager:SecretsManagerReadWrite',
                'es:ESHttpPost',
                'bedrock:*',
                'execute-api:*'
            ],
            resources=['*']
        )
        image_search_role = iam.Role(
            self, 'image_search_role',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com')
        )
        image_search_role.add_to_policy(_image_search_role_policy)

        image_search_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )
        
        image_search_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite")
        )
        
        image_search_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess")
        )
        
        ACCOUNT = os.getenv('AWS_ACCOUNT_ID', '')
        REGION = os.getenv('AWS_REGION', '')
        AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
        AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
        _bucket_name = "intelligent-image-search-data" + "-" + ACCOUNT + "-" + REGION
        
        _bucket = s3.Bucket(self,
                            id=_bucket_name,
                            bucket_name=_bucket_name,
                            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                            encryption=s3.BucketEncryption.S3_MANAGED,
                            enforce_ssl=True,
                            versioned=False,
                            removal_policy=RemovalPolicy.DESTROY
                            )
                            
        _bucket.add_cors_rule(
            allowed_headers=["*"],
            allowed_methods=[
                             s3.HttpMethods.GET,
                             s3.HttpMethods.PUT,
                             s3.HttpMethods.POST
                             ],
            allowed_origins=["*"]
        )
        
        search_layer = _lambda.LayerVersion(
            self, 'SearchLayer',
            code=_lambda.Code.from_asset('../lambda/search_layer'),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_9],
            description='Search Library'
        )
        
        function_name = 'image_search'
        image_search_function = _lambda.Function(
            self, function_name,
            function_name=function_name,
            runtime=_lambda.Runtime.PYTHON_3_9,
            role=image_search_role,
            layers=[search_layer],
            code=_lambda.Code.from_asset('../lambda/' + function_name),
            handler='lambda_function' + '.lambda_handler',
            timeout=Duration.minutes(10),
            reserved_concurrent_executions=100
        )
        
        image_search_function.add_environment("account", ACCOUNT)
        image_search_function.add_environment("region", REGION) 
        image_search_function.add_environment("aws_access_key_id", AWS_ACCESS_KEY_ID)
        image_search_function.add_environment("aws_secret_access_key", AWS_SECRET_ACCESS_KEY)
        image_search_function.add_environment("bucket_name", _bucket_name) 
        
        image_search_api = apigw.RestApi(self, 'image-search-api',
                               default_cors_preflight_options=apigw.CorsOptions(
                                   allow_origins=apigw.Cors.ALL_ORIGINS,
                                   allow_methods=apigw.Cors.ALL_METHODS
                               ),
                               endpoint_types=[apigw.EndpointType.REGIONAL]
                               )
                               
        image_search_integration = apigw.LambdaIntegration(
            image_search_function,
            proxy=True,
            integration_responses=[
                apigw.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': "'*'"
                    }
                )
            ]
        )
        
        image_search_resource = image_search_api.root.add_resource(
            'image_search',
            default_cors_preflight_options=apigw.CorsOptions(
                allow_methods=['GET', 'OPTIONS'],
                allow_origins=apigw.Cors.ALL_ORIGINS)
        )

        image_search_resource.add_method(
            'GET',
            image_search_integration,
            method_responses=[
                apigw.MethodResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': True
                    }
                )
            ]
        )

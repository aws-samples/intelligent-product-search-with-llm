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

class DataLoadStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        _data_load_role_policy = iam.PolicyStatement(
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
        data_load_role = iam.Role(
            self, 'data_load_role',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com')
        )
        data_load_role.add_to_policy(_data_load_role_policy)

        data_load_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )
        
        data_load_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite")
        )
        
        data_load_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess")
        )
        
        ACCOUNT = os.getenv('AWS_ACCOUNT_ID', '')
        REGION = os.getenv('AWS_REGION', '')
        AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
        AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
        _bucket_name = "intelligent-search-data" + "-" + ACCOUNT + "-" + REGION
        
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
        
        function_name = 'data_load'
        data_load_function = _lambda.Function(
            self, function_name,
            function_name=function_name,
            runtime=_lambda.Runtime.PYTHON_3_9,
            role=data_load_role,
            layers=[search_layer],
            code=_lambda.Code.from_asset('../lambda/' + function_name),
            handler='lambda_function' + '.lambda_handler',
            timeout=Duration.minutes(10),
            reserved_concurrent_executions=100
        )
        data_load_function.add_environment("account", ACCOUNT)
        data_load_function.add_environment("region", REGION) 
        data_load_function.add_environment("aws_access_key_id", AWS_ACCESS_KEY_ID)
        data_load_function.add_environment("aws_secret_access_key", AWS_SECRET_ACCESS_KEY)
        data_load_function.add_environment("bucket_name", _bucket_name) 
        
        
        data_load_api = apigw.RestApi(self, 'search_data_load-api',
                               default_cors_preflight_options=apigw.CorsOptions(
                                   allow_origins=apigw.Cors.ALL_ORIGINS,
                                   allow_methods=apigw.Cors.ALL_METHODS
                               ),
                               endpoint_types=[apigw.EndpointType.REGIONAL]
                               )
                               
        data_load_integration = apigw.LambdaIntegration(
            data_load_function,
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
        
        data_load_resource = data_load_api.root.add_resource(
            'data_load',
            default_cors_preflight_options=apigw.CorsOptions(
                allow_methods=['GET', 'OPTIONS'],
                allow_origins=apigw.Cors.ALL_ORIGINS)
        )

        data_load_resource.add_method(
            'GET',
            data_load_integration,
            method_responses=[
                apigw.MethodResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': True
                    }
                )
            ]
        )

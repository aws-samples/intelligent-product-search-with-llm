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

class TextSearchStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        # configure the lambda role
        _text_search_role_policy = iam.PolicyStatement(
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
        text_search_role = iam.Role(
            self, 'text_search_role',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com')
        )
        text_search_role.add_to_policy(_text_search_role_policy)

        text_search_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )
        
        text_search_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite")
        )
        
        search_layer = _lambda.LayerVersion(
            self, 'SearchLayer',
            code=_lambda.Code.from_asset('../lambda/search_layer'),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_9],
            description='Search Library'
        )
        
        function_name = 'text_search'
        text_search_function = _lambda.Function(
            self, function_name,
            function_name=function_name,
            runtime=_lambda.Runtime.PYTHON_3_9,
            role=text_search_role,
            layers=[search_layer],
            code=_lambda.Code.from_asset('../lambda/' + function_name),
            handler='lambda_function' + '.lambda_handler',
            timeout=Duration.minutes(10),
            reserved_concurrent_executions=100
        )
        
        text_search_api = apigw.RestApi(self, 'text-search-api',
                               default_cors_preflight_options=apigw.CorsOptions(
                                   allow_origins=apigw.Cors.ALL_ORIGINS,
                                   allow_methods=apigw.Cors.ALL_METHODS
                               ),
                               endpoint_types=[apigw.EndpointType.REGIONAL]
                               )
                               
        text_search_integration = apigw.LambdaIntegration(
            text_search_function,
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
        
        text_search_resource = text_search_api.root.add_resource(
            'text_search',
            default_cors_preflight_options=apigw.CorsOptions(
                allow_methods=['GET', 'OPTIONS'],
                allow_origins=apigw.Cors.ALL_ORIGINS)
        )

        text_search_resource.add_method(
            'GET',
            text_search_integration,
            method_responses=[
                apigw.MethodResponse(
                    status_code="200",
                    response_parameters={
                        'method.response.header.Access-Control-Allow-Origin': True
                    }
                )
            ]
        )

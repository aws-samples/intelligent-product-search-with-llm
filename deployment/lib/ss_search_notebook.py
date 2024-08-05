from constructs import Construct
import os
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    CfnParameter,
    Aws,
    Duration,
    aws_secretsmanager,
    aws_sagemaker as _sagemaker,
    aws_iam as _iam
)
import sagemaker
import boto3
import json
from sagemaker.serializers import JSONSerializer
from sagemaker.deserializers import JSONDeserializer


region = os.getenv('AWS_REGION', '')

class SearchNotebookStack(cdk.Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # set role for sagemaker notebook       
        self.notebook_job_role =  _iam.Role(
            self,'SearchNotebookRole',
            assumed_by=_iam.ServicePrincipal('sagemaker.amazonaws.com'),
            description =' IAM role for notebook job',
        )
        self.notebook_job_role.add_managed_policy(_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'))
        self.notebook_job_role.add_managed_policy(_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSageMakerFullAccess'))
        self.notebook_job_role.add_managed_policy(_iam.ManagedPolicy.from_aws_managed_policy_name('IAMFullAccess'))

        print('Deploying SageMaker via Notebook...')
        self.createNotebookInstanceByCDK()         

    def createNotebookInstanceByCDK(self):
        notebook_lifecycle = _sagemaker.CfnNotebookInstanceLifecycleConfig(
            self, f'Search-LifeCycleConfig',
            notebook_instance_lifecycle_config_name='ss-config',
            on_create=[_sagemaker.CfnNotebookInstanceLifecycleConfig.NotebookInstanceLifecycleHookProperty(
                content=cdk.Fn.base64(f"""
                    #!/bin/bash
                    cd home/ec2-user/SageMaker
                    git clone -b main --single-branch https://github.com/aws-samples/intelligent-product-search-with-llm.git
                    chmod -R 777 ./

                """)
            )]
        )
        cfn_notebook_instance = _sagemaker.CfnNotebookInstance(self,"SearchGuideNotebook",
        notebook_instance_name="SearchGuideNotebook",
        role_arn=self.notebook_job_role.role_arn,
        instance_type="ml.t3.xlarge",
        lifecycle_config_name='ss-config',
        volume_size_in_gb=100)



    
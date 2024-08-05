# Welcome to your CDK Python project!

### 0. Precondition

Please make sure you have over 14 GB memory and Python 3 and npm installed on your environment. Linux or Mac OS preferred.

If there's no npm, install via nvm:
```
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash
source /home/ec2-user/.bashrc
```
Note the v0.39.3 is just an example, download your preferred version.Then close and reopen terminal, then

```
nvm install v16.15.1
```
or
```
nvm install node
```


### 1. Change directory to ./deployment folder

```
cd ./deployment
```


### 2. Install AWS CDK

```
npm install -g aws-cdk
```


### 3. Bootstrap the CDK to provision all the infrastructure needed for the CDK to make changes to your AWS account

```
sudo yum install python3-pip
pip install -r requirements.txt
```
(precondition: you have installed pip via "sudo apt install python3-pip")


### 4. export your account configuration to the environment
```
export AWS_ACCOUNT_ID=XXXXXXXXXXXX
export AWS_REGION=xx-xx-x
export AWS_ACCESS_KEY_ID=XXXXXX
export AWS_SECRET_ACCESS_KEY=XXXXXXX
```
```
cdk bootstrap aws://[your-account-id]/[your-region]
```
you can install the required dependencies.


### 5. Below command will validate the environment and generate CloudFormation.json 

```
cdk synth
```
If everything is good, then
```
cdk deploy --all --require-approval never
```

### 6. The CDK deployment will provide CloudFormation stacks with relevant resouces like Lambda, API Gateway and SageMaker notebook etc.

### Clean Up
When you don't need the environment and want to clean it up, run:

```
$ cdk destroy --all
```
Then resources which are not created by cdk, need to manually clean it up. Like SageMaker endpoints,endpoint configurations,models, pls go to AWS console SageMaker page and delete resources under the "Inference" part.

### Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation



## Architecture Overview
This project demonstrates a serverless architecture using AWS services to create an interactive AI chatbot. Here are a few key points about the architecture:

![steamlitapp](https://github.com/rahulsing/bedrock-streamlit-ecs-task/blob/main/StreamlitOnECS.PNG?raw=true)

1. **Streamlit Frontend**: A user-friendly web interface built with Streamlit, allowing users to input prompts and select AI models.
2. **Amazon Bedrock**: The backend AI service provided by AWS, which hosts various large language models.
3. **AWS SDK (Boto3)**: Used to interact with Amazon Bedrock's API, sending requests and receiving responses.
4. **Docker Container**: The application is containerized for easy deployment and scalability.
5. **Amazon Elastic Container Registry (ECR)**: Used to store and manage the Docker container image.
6. **Amazon Elastic Container Service (ECS)**: Manages and runs the containerized application, providing scalability and orchestration.

The application flow is as follows:
1. Users interact with the Streamlit interface hosted on ECS.
2. User inputs are sent to Amazon Bedrock via Boto3.
3. Bedrock processes the request and generates a response.
4. The response is streamed back to the Streamlit interface in real-time.
5. ECS manages the container.

## Prerequisites

Before running this project, ensure you have the following:

1. **AWS Account**: You need an active AWS account with access to Amazon Bedrock.
2. **AWS CLI**: Install and configure the AWS CLI with appropriate credentials.
3. **Docker**: Install Docker on your local machine or development environment.
4. **Python 3.7+**: The project is written in Python, ensure you have Python 3.7 or later installed.
5. **IAM Permissions**: Ensure your AWS user or role has the necessary permissions to:
- Access Amazon Bedrock
- Push/pull images to/from Amazon ECR
- (Optional) Deploy to other AWS services if you plan to host the application on AWS
6. **Amazon Bedrock Model Access**: Request access to the Bedrock models you plan to use (e.g., Claude models) through the AWS console.

## Git Clone : 
```
git clone https://github.com/rahulsing/bedrock-streamlit-ecs-task.git
```


## Step 1: Set the Enviroment Variable
```
ECR_REPOSITORY_NAME=mystreamlitapp
AWS_ACCOUNT_ID="<12345678910>"
AWS_REGION="us-west-2"
IMAGE_TAG="latest"
CLUSTER_NAME="MyECSCluster"

```

##  Step 2: Create ECR Repo

```
cd Project


aws ecr create-repository --repository-name $ECR_REPOSITORY_NAME --region $AWS_REGION
```

##  Step 3: Build and push the image to ECR

##### Authenticate Docker to ECR
```
aws ecr get-login-password --region "${AWS_REGION}" | \
    docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
```
##### Build Docker image
```
docker build -t "${ECR_REPOSITORY_NAME}" .
```
##### Tag image for ECR
```
docker tag "${ECR_REPOSITORY_NAME}:${IMAGE_TAG}" "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}:${IMAGE_TAG}"
```

##### Push image to ECR
```
docker push "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}:${IMAGE_TAG}"
```
-------------------------


## Step 4: Creating ECS Task Definitation, Cluster and required Role
#### Get your Default VPC and a Public Subnet
Set variable 
``` 
VPC_ID=<vpc-9cd2fee4>
PUBLIC_SUBNET_ID=<subnet-b050e9c8>
```

#### Below is the CLI Command to create the CloudFormation Stack
```
aws cloudformation create-stack \
  --stack-name my-ecs-streamlit-bedrock-stack \
  --template-body file://ecs-streamlit-bedrock-stack.yaml \
  --parameters ParameterKey=ImageName,ParameterValue=${ECR_REPOSITORY_NAME}:${IMAGE_TAG} \
    ParameterKey=VpcId,ParameterValue=$VPC_ID \
    ParameterKey=SubnetId,ParameterValue=$PUBLIC_SUBNET_ID \
  --capabilities CAPABILITY_IAM \
  --region $AWS_REGION
```

## Step 5: Run ECS task : 
##### From above CloudFromation output set the below value

```
TaskDefinitionArn=$(aws cloudformation describe-stacks --stack-name my-ecs-streamlit-bedrock-stack --query "Stacks[0].Outputs[?OutputKey=='TaskDefinitionArn'].OutputValue" --region $AWS_REGION --output text)
ECSSecurityGroup=$(aws cloudformation describe-stacks --stack-name my-ecs-streamlit-bedrock-stack --query "Stacks[0].Outputs[?OutputKey=='ECSSecurityGroup'].OutputValue" --region $AWS_REGION --output text)

echo $TaskDefinitionArn
echo $ECSSecurityGroup
```


Run the task  : 
```
aws ecs run-task \
  --cluster $CLUSTER_NAME \
  --task-definition $TaskDefinitionArn \
  --launch-type FARGATE \
  --count 1 \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={subnets=[$PUBLIC_SUBNET_ID],securityGroups=[$ECSSecurityGroup],assignPublicIp=ENABLED}" \
  --enable-ecs-managed-tags \
  --region $AWS_REGION
```

## Get the API URL 
```
TASK_ARN=$(aws ecs run-task \
  --cluster $CLUSTER_NAME \
  --task-definition $TaskDefinitionArn \
  --launch-type FARGATE \
  --count 1 \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={subnets=[$PUBLIC_SUBNET_ID],securityGroups=[$ECSSecurityGroup],assignPublicIp=ENABLED}" \
  --enable-ecs-managed-tags \
  --region $AWS_REGION \
  --query 'tasks[0].taskArn' \
  --output text)
```

##### Wait for status to change to running: 
```
aws ecs describe-tasks --cluster MyECSCluster --tasks $TASK_ARN --query 'tasks[0].lastStatus' --region $AWS_REGION --output text 

```

##### Once the ECS Task is in running state, get the URL for the Streamlit app: 

```
ENI_ID=$(aws ecs describe-tasks --cluster MyECSCluster --tasks $TASK_ARN \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
  --region $AWS_REGION \
  --output text)

PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID \
  --query 'NetworkInterfaces[0].Association.PublicIp' \
  --region $AWS_REGION \
  --output text)

EXTERNAL_LINK="http://$PUBLIC_IP:80"
echo $EXTERNAL_LINK
```



## Open the Streamlit app: 
![steamlitapp](https://github.com/rahulsing/bedrock-streamlit-ecs-task/blob/main/StreamlitApp.PNG?raw=true)


## CLEAN UP 

###  START DELETE TASK 

- List all tasks
```
TASK_ARNS=$(aws ecs list-tasks --cluster $CLUSTER_NAME --query 'taskArns[]' --output text --region $AWS_REGION )

# Stop each task
for TASK_ARN in $TASK_ARNS
do
    echo "Stopping task: $TASK_ARN"
    aws ecs stop-task --cluster $CLUSTER_NAME --task $TASK_ARN --query 'task.taskArn'  --region $AWS_REGION --output text 
done
```

## Delete the CloudFormation Stack : 
```
aws cloudformation delete-stack \
  --stack-name my-ecs-streamlit-bedrock-stack --region $AWS_REGION
```

## Delete the ECR Image: 
```
ECR_REPOSITORY_NAME=mystreamlitapp

aws ecr delete-repository --repository-name $ECR_REPOSITORY_NAME --region us-west-2 --force 
```

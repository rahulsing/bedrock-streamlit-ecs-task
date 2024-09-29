
## Git Clone : 



## Step 1: Set the Enviroment Variablea  
```
ECR_REPOSITORY_NAME=mystreamlitapp
AWS_ACCOUNT_ID="12345678910"
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
VPC_ID=vpc-9cd2fee4
PUBLIC_SUBNET_ID=subnet-b050e9c8
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
aws cloudformation describe-stacks --stack-name  my-ecs-streamlit-bedrock-stack --query 'Stacks[0].Outputs[].{Key:OutputKey,Value:OutputValue}' --output json --region $AWS_REGION
```

Set variable 
```
TaskDefinitionArn=arn:aws:ecs:us-west-2:12345678910:task-definition/from-cloudformation:1
ECSSecurityGroup=sg-01cd84ab7d48bc240
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

```
aws ecs describe-tasks --cluster MyECSCluster --tasks $TASK_ARN --query 'tasks[0].lastStatus' --region $AWS_REGION --output text 

```

```
ENI_ID=$(aws ecs describe-tasks --cluster MyECSCluster --tasks $TASK_ARN \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
  --region $AWS_REGION \
  --output text)
```

```
PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID \
  --query 'NetworkInterfaces[0].Association.PublicIp' \
  --region $AWS_REGION \
  --output text)
```

```
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

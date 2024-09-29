#!/bin/bash

# Create ECR repository if it doesn't exist
aws ecr describe-repositories --repository-names "${ECR_REPOSITORY_NAME}" || \
    aws ecr create-repository --repository-name "${ECR_REPOSITORY_NAME}"

# Authenticate Docker to ECR
aws ecr get-login-password --region "${AWS_REGION}" | \
    docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Build Docker image
docker build -t "${ECR_REPOSITORY_NAME} .

# Tag image for ECR
docker tag "${ECR_REPOSITORY_NAME}:${IMAGE_TAG}" "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}:${IMAGE_TAG}"

# Push image to ECR
docker push "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}:${IMAGE_TAG}"

echo "Image pushed successfully to ${ECR_REPOSITORY_NAME}"


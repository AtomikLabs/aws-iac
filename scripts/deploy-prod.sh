#!/bin/bash
# Prod deployment script

# Set AWS profile and region
AWS_PROFILE="atomiklabs"
AWS_REGION="us-east-1"
CONFIG_BUCKET="./"
PROD_CONFIG_FILE="prod.json"

# Deploy the CloudFormation stack for production
aws cloudformation deploy \
    --template-file ${PROD_CONFIG_FILE} \
    --stack-name prod-stack \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides file://${PROD_CONFIG_FILE} \
    --profile ${AWS_PROFILE} \
    --region ${AWS_REGION}

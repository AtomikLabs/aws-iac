#!/bin/bash
# Dev deployment script

# Set AWS profile and region
AWS_PROFILE="atomiklabs"
AWS_REGION="us-east-1"
CONFIG_BUCKET="./"
DEV_CONFIG_FILE="dev.json"

# Deploy the CloudFormation stack for dev
aws cloudformation deploy \
    --template-file ${DEV_CONFIG_FILE} \
    --stack-name dev-stack \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides file://${DEV_CONFIG_FILE} \
    --profile ${AWS_PROFILE} \
    --region ${AWS_REGION}

#!/bin/bash
# Stage deployment script

# Set AWS profile and region
AWS_PROFILE="atomiklabs"
AWS_REGION="us-east-1"
CONFIG_BUCKET="./"
STAGE_CONFIG_FILE="stage.json"

# Deploy the CloudFormation stack for staging
aws cloudformation deploy \
    --template-file ${STAGE_CONFIG_FILE} \
    --stack-name stage-stack \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides file://${STAGE_CONFIG_FILE} \
    --profile ${AWS_PROFILE} \
    --region ${AWS_REGION}

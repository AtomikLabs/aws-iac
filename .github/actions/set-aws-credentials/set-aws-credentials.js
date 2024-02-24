// src/set-aws-credentials.js
const core = require('@actions/core');
const github = require('@actions/github');

permittedEnvironments = ['prod', 'stage', 'dev'];

function setAwsCredentials() {
  try {
    const environmentName = core.getInput('environment_name');
    const awsRegion = core.getInput('aws_region');
    let awsAccessKeyId = '';
    let awsSecretAccessKey = '';

    switch(environmentName) {
      case 'prod':
        awsAccessKeyId = process.env.PROD_AWS_ACCESS_KEY_ID;
        awsSecretAccessKey = process.env.PROD_AWS_SECRET_ACCESS_KEY;
        break;
      case 'stage':
        awsAccessKeyId = process.env.STAGE_AWS_ACCESS_KEY_ID;
        awsSecretAccessKey = process.env.STAGE_AWS_SECRET_ACCESS_KEY;
        break;
      case 'dev':
        awsAccessKeyId = process.env.DEV_AWS_ACCESS_KEY_ID;
        awsSecretAccessKey = process.env.DEV_AWS_SECRET_ACCESS_KEY;
        break;
      default:
        throw new Error(`Unsupported environment name: ${environmentName}`);
    }

    core.setSecret(awsAccessKeyId);
    core.setSecret(awsSecretAccessKey);
    core.exportVariable('AWS_ACCESS_KEY_ID', awsAccessKeyId);
    core.exportVariable('AWS_SECRET_ACCESS_KEY', awsSecretAccessKey);

    console.log(`AWS credentials configured for environment: ${environmentName}`);
  } catch (error) {
    core.setFailed(error.message);
  }
}

module.exports = { setAwsCredentials };

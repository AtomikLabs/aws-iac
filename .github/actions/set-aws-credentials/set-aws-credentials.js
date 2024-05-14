// src/set-aws-credentials.js
const core = require('@actions/core');
const github = require('@actions/github');

permittedEnvironments = ['prod', 'stage', 'dev'];

function setAwsCredentials() {
  console.log('Setting AWS credentials...');
  try {
    const environmentName = core.getInput('ENVIRONMENT_NAME');
    const DEV_AWS_ACCESS_KEY_ID = core.getInput('DEV_AWS_ACCESS_KEY_ID');
    const DEV_AWS_SECRET_ACCESS_KEY = core.getInput('DEV_AWS_SECRET_ACCESS_KEY');
    const PROD_AWS_ACCESS_KEY_ID = core.getInput('PROD_AWS_ACCESS_KEY_ID');
    const PROD_AWS_SECRET_ACCESS_KEY = core.getInput('PROD_AWS_SECRET_ACCESS_KEY');
    const STAGE_AWS_ACCESS_KEY_ID = core.getInput('STAGE_AWS_ACCESS_KEY_ID');
    const STAGE_AWS_SECRET_ACCESS_KEY = core.getInput('STAGE_AWS_SECRET_ACCESS_KEY');
    let awsAccessKeyId = '';
    let awsSecretAccessKey = '';

    switch(environmentName) {
      case 'dev':
        awsAccessKeyId = DEV_AWS_ACCESS_KEY_ID;
        awsSecretAccessKey = DEV_AWS_SECRET_ACCESS_KEY;
        break;
      case 'prod':
        awsAccessKeyId = PROD_AWS_ACCESS_KEY_ID;
        awsSecretAccessKey = PROD_AWS_SECRET_ACCESS_KEY;
        break;
      case 'stage':
        awsAccessKeyId = STAGE_AWS_ACCESS_KEY_ID;
        awsSecretAccessKey = STAGE_AWS_SECRET_ACCESS_KEY;
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

if (require.main === module) {
  setAwsCredentials();
}

module.exports = { setAwsCredentials };
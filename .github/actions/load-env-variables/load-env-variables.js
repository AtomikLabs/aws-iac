const core = require('@actions/core');
const github = require('@actions/github');
const fs = require('fs');

async function loadEnvironmentVariables() {
  try {
    const eventName = github.context.eventName;
    const refName = eventName === 'pull_request' ? github.context.payload.pull_request.base.ref : github.context.ref_name;
    const envName = refName.replace(/\//g, '-');

    core.exportVariable('ENV_NAME', envName);
    const envFile = `infra/core/environments/env.${envName}.json`;
    core.exportVariable('ENV_FILE', envFile);

    if (!fs.existsSync(envFile)) {
      throw new Error(`Environment file ${envFile} does not exist`);
    }

    const data = fs.readFileSync(envFile, { encoding: 'utf8', flag: 'r' });
    const jsonData = JSON.parse(data);
    const iamUserName = jsonData.iam_user_name;

    core.exportVariable('IAM_USER_NAME', iamUserName);

    console.log(`Environment variables set for environment: ${envName}`);
  } catch (error) {
    core.setFailed(`Action failed with error: ${error}`);
  }
}

if (require.main === module) {
    loadEnvironmentVariables();
}

module.exports = { loadEnvironmentVariables };

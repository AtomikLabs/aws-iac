const core = require("@actions/core");
const github = require("@actions/github");
const fs = require("fs");

async function loadEnvironmentVariables() {
  try {
    const eventName = github.context.eventName;
    let refName;

    if (eventName === "pull_request") {
      refName = github.context.payload.pull_request.base.ref;
    } else if (eventName === "push") {
      const refParts = github.context.ref.split("/");
      refName = refParts.length > 2 ? refParts[2] : "";
    } else {
      throw new Error(
        "Unsupported GitHub event. Only pull_request and push events are supported."
      );
    }

    if (!["dev", "stage", "prod"].includes(refName)) {
      throw new Error(
        `The branch ${refName} does not map to a supported environment.`
      );
    }

    const envName = refName.replace(/\//g, "-");
    core.exportVariable("ENV_NAME", envName);

    console.log(`Environment variables set for environment: ${envName}`);
  } catch (error) {
    core.setFailed(`Action failed with error: ${error}`);
  }
}

if (require.main === module) {
  loadEnvironmentVariables();
}

module.exports = {
  loadEnvironmentVariables,
};

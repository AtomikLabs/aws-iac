const core = require('@actions/core');

function setRabbitMQCredentials() {
  try {
    const username = process.env.RABBITMQCTL_USERNAME;
    const password = process.env.RABBITMQCTL_PASSWORD;

    if (!username || !password) {
      throw new Error('RabbitMQ credentials not provided');
    }

    core.exportVariable('RABBITMQCTL_USERNAME', username);
    core.exportVariable('RABBITMQCTL_PASSWORD', password);
  } catch (error) {
    core.setFailed(`Action failed with error: ${error}`);
  }
}

module.exports = setRabbitMQCredentials;

if (require.main === module) {
  setRabbitMQCredentials();
}
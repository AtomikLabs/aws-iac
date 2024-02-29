const core = require('@actions/core');
const setRabbitMQCredentials = require('../set-rabbitmq-credentials');

jest.mock('@actions/core');

describe('Set RabbitMQ Credentials Action', () => {
  beforeEach(() => {
    process.env.RABBITMQCTL_USERNAME = 'testUser';
    process.env.RABBITMQCTL_PASSWORD = 'testPass';
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('successfully exports RabbitMQ credentials', () => {
    setRabbitMQCredentials();

    expect(core.exportVariable).toHaveBeenCalledWith('RABBITMQCTL_USERNAME', 'testUser');
    expect(core.exportVariable).toHaveBeenCalledWith('RABBITMQCTL_PASSWORD', 'testPass');
  });

  test('fails when credentials are not provided', () => {
    delete process.env.RABBITMQCTL_USERNAME;
    delete process.env.RABBITMQCTL_PASSWORD;

    setRabbitMQCredentials();

    expect(core.setFailed).toHaveBeenCalled();
  });
});

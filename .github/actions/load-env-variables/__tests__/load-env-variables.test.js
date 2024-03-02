
const core = require('@actions/core');
const source_path = '../load-env-variables.js';
const github = require('@actions/github');
const fs = require('fs');
const { loadEnvironmentVariables } = require(source_path);


jest.mock('@actions/core');
jest.mock('@actions/github');
jest.mock('fs');

describe('GitHub Action Tests', () => {
  beforeEach(() => {
    github.context.eventName = 'push';
    github.context.ref_name = 'main';
    github.context.payload.pull_request = { base: { ref: 'develop' } };

    fs.existsSync.mockImplementation(() => true);

    fs.readFileSync.mockImplementation(() => JSON.stringify({ iam_user_name: 'test-iam-user' }));
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('Sets ENV_NAME and ENV_FILE for push event', async () => {
    await loadEnvironmentVariables();

    expect(core.exportVariable).toHaveBeenCalledWith('ENV_NAME', 'main');
    expect(core.exportVariable).toHaveBeenCalledWith('ENV_FILE', expect.stringContaining('env.main.json'));
  });

  test('Sets ENV_NAME and ENV_FILE for pull_request event', async () => {
    github.context.eventName = 'pull_request';

    await loadEnvironmentVariables();

    expect(core.exportVariable).toHaveBeenCalledWith('ENV_NAME', 'develop');
    expect(core.exportVariable).toHaveBeenCalledWith('ENV_FILE', expect.stringContaining('env.develop.json'));
  });

  test('Reads IAM_USER_NAME from JSON file and sets environment variable', async () => {
    await loadEnvironmentVariables();

    expect(core.exportVariable).toHaveBeenCalledWith('IAM_USER_NAME', 'test-iam-user');
  });

  test('Handles missing env file gracefully', async () => {
    fs.existsSync.mockImplementation(() => false);

    await loadEnvironmentVariables();

    expect(core.setFailed).toHaveBeenCalledWith(expect.stringContaining('does not exist'));
  });
});

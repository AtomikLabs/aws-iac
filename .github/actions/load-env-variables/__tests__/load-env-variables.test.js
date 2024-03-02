const core = require('@actions/core');
const github = require('@actions/github');
const fs = require('fs');
const { loadEnvironmentVariables } = require('../load-env-variables.js');

jest.mock('@actions/core');
jest.mock('@actions/github');
jest.mock('fs');

describe('Load Environment Variables Action', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    github.context.eventName = 'push';
    github.context.ref = 'refs/heads/main';
    github.context.payload = { pull_request: { base: { ref: 'develop' } } };
    
    fs.existsSync.mockReturnValue(true);
    fs.readFileSync.mockReturnValue(JSON.stringify({ iam_user_name: 'testIamUser' }));
  });

  test('correctly sets environment variables for push event', async () => {
    await loadEnvironmentVariables();

    expect(core.exportVariable).toHaveBeenCalledWith('ENV_NAME', 'main');
    expect(core.exportVariable).toHaveBeenCalledWith('ENV_FILE', 'infra/core/environments/env.main.json');
    expect(core.exportVariable).toHaveBeenCalledWith('IAM_USER_NAME', 'testIamUser');
  });

  test('correctly sets environment variables for pull request event', async () => {
    github.context.eventName = 'pull_request';

    await loadEnvironmentVariables();

    expect(core.exportVariable).toHaveBeenCalledWith('ENV_NAME', 'develop');
    expect(core.exportVariable).toHaveBeenCalledWith('ENV_FILE', 'infra/core/environments/env.develop.json');
    expect(core.exportVariable).toHaveBeenCalledWith('IAM_USER_NAME', 'testIamUser');
  });

  test('throws error if environment file does not exist', async () => {
    fs.existsSync.mockReturnValue(false);

    await loadEnvironmentVariables();

    expect(core.setFailed).toHaveBeenCalledWith(expect.stringContaining('does not exist'));
  });

  test('handles missing iam_user_name gracefully', async () => {
    fs.readFileSync.mockReturnValue(JSON.stringify({}));

    await loadEnvironmentVariables();

    expect(core.exportVariable).not.toHaveBeenCalledWith('IAM_USER_NAME', expect.anything());
    expect(core.setFailed).not.toHaveBeenCalled();
  });
});

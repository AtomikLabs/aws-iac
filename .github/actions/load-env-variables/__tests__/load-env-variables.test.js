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
    github.context.ref = 'refs/heads/feature/new-feature';
    github.context.payload = { pull_request: { base: { ref: 'dev' } } };
    
    fs.existsSync.mockReturnValue(true);
    fs.readFileSync.mockReturnValue(JSON.stringify({ iam_user_name: 'testIamUser' }));
  });

  test('sets environment variables correctly for push event to allowed branch', async () => {
    github.context.ref = 'refs/heads/dev';

    await loadEnvironmentVariables();

    expect(core.exportVariable).toHaveBeenCalledWith('ENV_NAME', 'dev');
    expect(core.exportVariable).toHaveBeenCalledWith('ENV_FILE', 'infra/core/environments/env.dev.json');
    expect(core.exportVariable).toHaveBeenCalledWith('IAM_USER_NAME', 'testIamUser');
  });

  test('sets environment variables correctly for pull request event', async () => {
    github.context.eventName = 'pull_request';

    await loadEnvironmentVariables();

    expect(core.exportVariable).toHaveBeenCalledWith('ENV_NAME', 'dev');
    expect(core.exportVariable).toHaveBeenCalledWith('ENV_FILE', 'infra/core/environments/env.dev.json');
    expect(core.exportVariable).toHaveBeenCalledWith('IAM_USER_NAME', 'testIamUser');
  });

  test('fails when triggered by unsupported event', async () => {
    github.context.eventName = 'issue_comment';

    await loadEnvironmentVariables();

    expect(core.setFailed).toHaveBeenCalledWith(expect.stringContaining('Unsupported GitHub event'));
  });

  test('fails if environment file does not exist', async () => {
    github.context.ref = 'refs/heads/dev';
  
    fs.existsSync.mockReturnValue(false);
  
    await loadEnvironmentVariables();
  
    expect(core.setFailed).toHaveBeenCalledWith(expect.stringContaining('does not exist'));
  });

  test('does not set IAM_USER_NAME if missing in environment file', async () => {
    fs.readFileSync.mockReturnValue(JSON.stringify({}));

    await loadEnvironmentVariables();

    expect(core.exportVariable).not.toHaveBeenCalledWith('IAM_USER_NAME', expect.anything());
  });
});

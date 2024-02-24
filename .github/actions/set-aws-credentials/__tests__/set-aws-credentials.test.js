const core = require('@actions/core');
const { setAwsCredentials } = require('../set-aws-credentials');

process.env.PROD_AWS_ACCESS_KEY_ID = 'prodAccessKeyId';
process.env.PROD_AWS_SECRET_ACCESS_KEY = 'prodSecretAccessKey';
process.env.STAGE_AWS_ACCESS_KEY_ID = 'stageAccessKeyId';
process.env.STAGE_AWS_SECRET_ACCESS_KEY = 'stageSecretAccessKey';
process.env.DEV_AWS_ACCESS_KEY_ID = 'devAccessKeyId';
process.env.DEV_AWS_SECRET_ACCESS_KEY = 'devSecretAccessKey';

describe('Set AWS Credentials', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('sets production credentials correctly', () => {
    core.getInput.mockReturnValueOnce('prod');
    setAwsCredentials();
    expect(core.exportVariable).toHaveBeenCalledWith('AWS_ACCESS_KEY_ID', 'prodAccessKeyId');
    expect(core.exportVariable).toHaveBeenCalledWith('AWS_SECRET_ACCESS_KEY', 'prodSecretAccessKey');
    expect(core.setSecret).toHaveBeenCalledWith('prodAccessKeyId');
    expect(core.setSecret).toHaveBeenCalledWith('prodSecretAccessKey');
  });

  test('sets stage credentials correctly', () => {
    core.getInput.mockReturnValueOnce('stage');
    setAwsCredentials();
  });

  test('sets development credentials correctly', () => {
    core.getInput.mockReturnValueOnce('dev');
    setAwsCredentials();
  });

  test('throws error on unsupported environment', () => {
    core.getInput.mockReturnValueOnce('unsupported');
    setAwsCredentials();
    expect(core.setFailed).toHaveBeenCalledWith('Unsupported environment name: unsupported');
  });
});

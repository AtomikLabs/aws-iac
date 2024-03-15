jest.mock('@actions/core');
const source_path = '../set-aws-credentials';
const { it } = require('@jest/globals');
const { setAwsCredentials } = require(source_path);

const core = require('@actions/core');

describe('setAwsCredentials', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    core.getInput.mockImplementation((name) => {
      switch (name) {
        case 'ENVIRONMENT_NAME':
          return process.env['INPUT_ENVIRONMENT_NAME'];
        case 'DEV_AWS_ACCESS_KEY_ID':
          return 'devAccessKeyId';
        case 'DEV_AWS_SECRET_ACCESS_KEY':
          return 'devSecretAccessKey';
        case 'PROD_AWS_ACCESS_KEY_ID':
          return 'prodAccessKeyId';
        case 'PROD_AWS_SECRET_ACCESS_KEY':
          return 'prodSecretAccessKey';
        case 'STAGE_AWS_ACCESS_KEY_ID':
          return 'stageAccessKeyId';
        case 'STAGE_AWS_SECRET_ACCESS_KEY':
          return 'stageSecretAccessKey';
        default:
          return '';
      }
    });
  });

  it('should set AWS credentials for dev environment', () => {
    process.env['INPUT_ENVIRONMENT_NAME'] = 'dev';

    setAwsCredentials();

    expect(core.setSecret).toHaveBeenCalledWith('devAccessKeyId');
    expect(core.setSecret).toHaveBeenCalledWith('devSecretAccessKey');
    expect(core.exportVariable).toHaveBeenCalledWith('AWS_ACCESS_KEY_ID', 'devAccessKeyId');
    expect(core.exportVariable).toHaveBeenCalledWith('AWS_SECRET_ACCESS_KEY', 'devSecretAccessKey');
  });

  it('should set AWS credentials for prod environment', () => {
    process.env['INPUT_ENVIRONMENT_NAME'] = 'prod';

    setAwsCredentials();

    expect(core.setSecret).toHaveBeenCalledWith('prodAccessKeyId');
    expect(core.setSecret).toHaveBeenCalledWith('prodSecretAccessKey');
    expect(core.exportVariable).toHaveBeenCalledWith('AWS_ACCESS_KEY_ID', 'prodAccessKeyId');
    expect(core.exportVariable).toHaveBeenCalledWith('AWS_SECRET_ACCESS_KEY', 'prodSecretAccessKey');
  });

  it('should set AWS credentials for stage environment', () => {
    process.env['INPUT_ENVIRONMENT_NAME'] = 'stage';

    setAwsCredentials();

    expect(core.setSecret).toHaveBeenCalledWith('stageAccessKeyId');
    expect(core.setSecret).toHaveBeenCalledWith('stageSecretAccessKey');
    expect(core.exportVariable).toHaveBeenCalledWith('AWS_ACCESS_KEY_ID', 'stageAccessKeyId');
    expect(core.exportVariable).toHaveBeenCalledWith('AWS_SECRET_ACCESS_KEY', 'stageSecretAccessKey');
  });

  it('should set core.setFailed when environment name is not supported', () => {
    process.env['INPUT_ENVIRONMENT_NAME'] = 'unsupported';

    setAwsCredentials();

    expect(core.setFailed).toHaveBeenCalledWith('Unsupported environment name: unsupported');
  });
});

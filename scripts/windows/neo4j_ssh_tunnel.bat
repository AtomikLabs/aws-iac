@echo off
setlocal

if "%~2"=="" (
    echo Usage: %0 PrivateIP BastionIP
    exit /b 1
)

set "PrivateIP=%~1"
set "BastionIP=%~2"

set "sshKeyPath=%USERPROFILE%\.ssh\dev-atomiklabs-bastion-keypair.pem"
set "sshUser=ec2-user"

if not exist "%sshKeyPath%" (
    echo SSH key not found at path: %sshKeyPath%
    exit /b 1
)

ssh -NfL localhost:7474:%PrivateIP%:7474 -L localhost:7687:%PrivateIP%:7687 -i "%sshKeyPath%" %sshUser%@%BastionIP%
echo SSH tunnel established to %PrivateIP% via %BastionIP%.

endlocal

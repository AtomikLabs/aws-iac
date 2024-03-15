@echo off
setlocal

:: Check if 2 arguments are passed (PrivateIP and BastionIP)
if "%~2"=="" (
    echo Usage: %0 PrivateIP BastionIP
    exit /b 1
)

:: Assign passed arguments to variables
set "PrivateIP=%~1"
set "BastionIP=%~2"

:: Define SSH key path and user
set "sshKeyPath=%USERPROFILE%\.ssh\dev-atomiklabs-bastion-keypair.pem"
set "sshUser=ec2-user"

:: Check if SSH key exists
if not exist "%sshKeyPath%" (
    echo SSH key not found at path: %sshKeyPath%
    exit /b 1
)

:: Execute SSH command
ssh -NfL localhost:7474:%PrivateIP%:7474 -L localhost:7687:%PrivateIP%:7687 -i "%sshKeyPath%" %sshUser%@%BastionIP%
echo SSH tunnel established to %PrivateIP% via %BastionIP%.

:: End of script
endlocal

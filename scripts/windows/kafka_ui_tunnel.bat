@echo off
setlocal

if "%~2"=="" (
    echo Usage: %0 PrivateIP OrchestrationIP
    exit /b 1
)

set "PrivateIP=%~1"
set "OrchestrationIP=%~2"

set "sshKeyPath=%USERPROFILE%\.ssh\dev-atomiklabs-bastion-keypair.pem"
set "sshUser=ec2-user"

if not exist "%sshKeyPath%" (
    echo SSH key not found at path: %sshKeyPath%
    exit /b 1
)

ssh -NfL localhost:8000:%PrivateIP%:8000 -i "%sshKeyPath%" %sshUser%@%OrchestrationIP%
echo SSH tunnel established to %PrivateIP% via %OrchestrationIP%.

endlocal

# PowerShell

param (
    [Parameter(Mandatory=$true)][string]$PrivateIP,
    [Parameter(Mandatory=$true)][string]$BastionIP
)

$sshKeyPath = "$HOME\.ssh\dev-atomiklabs-bastion-keypair.pem"
$sshUser = "ec2-user"

if ((Test-Path -Path $sshKeyPath) -eq $false) {
    Write-Error "SSH key not found at path: $sshKeyPath"
    exit 1
}

ssh -vvv -NfL 127.0.0.1:7474:$PrivateIP:7474 -L 127.0.0.1:7687:$PrivateIP:7687 -i $sshKeyPath $sshUser@$BastionIP
Write-Output "SSH tunnel established to $PrivateIP via $BastionIP."
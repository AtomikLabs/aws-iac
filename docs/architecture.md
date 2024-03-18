# Architecture

![Architecture](images/architecture_V2.gif)

## Overview

The application was original developed as a Jupyter notebook and then ported to a Python script and integrated with a RDS database, S3, SecretsManager, and Lambda. The code is stored in a GitHub repository and the CI/CD pipeline is managed using GitHub Actions. The application is deployed to AWS using CloudFormation.
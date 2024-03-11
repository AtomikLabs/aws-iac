[![Infrastructure CI/CD](https://github.com/AtomikLabs/atomiklabs/actions/workflows/infra.yaml/badge.svg)](https://github.com/AtomikLabs/atomiklabs/actions/workflows/infra.yaml)
[![Tests](https://github.com/AtomikLabs/atomiklabs/actions/workflows/tests.yaml/badge.svg)](https://github.com/AtomikLabs/atomiklabs/actions/workflows/tests.yaml)
[![Lint and Format](https://github.com/AtomikLabs/atomiklabs/actions/workflows/lint_and_format.yaml/badge.svg)](https://github.com/AtomikLabs/atomiklabs/actions/workflows/lint_and_format.yaml)

I want to model AI and computer science and build tools that augment anyone who wants to understand, build, or research in the field.

It started as a project to help me stay current as I move through grad school. Now it supports about ~800 subscribers to daily TechcraftingAI research summary newsletters and TTS podcasts.

# Current Status

I am building the data pipeline and populating the graph database that will support all future development. The next major step is a research news site that will host the podcasts, showcase the latest research, and allow users to sign up for customized research newsletters.

# Thanks to arXiv and Cornell University
None of this would be possible without [arXiv](https://arxiv.org/). It's easy to take that resource for granted, but the contribution it makes to open science is immeasurable.

# Tech Stack

- GitHub Actions and Workflows for CI/CD
- Terraform
- AWS
  - Lambda
  - ECR
  - EC2
  - DynamoDB
  - s3
  - Polly
  - EventBridge
  - VPC
  - SecretsManager
  - IAM
  - SessionManager
  - CloudWatch
  - Route53
- Neo4j Community (self-hosted)
- Languages: Python, JavaScript, HCL

[Help keep the lights on the coder caffeinated](patreon.com/AtomikLabs).

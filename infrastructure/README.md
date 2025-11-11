# Infrastructure

This directory contains Terraform configuration for provisioning AWS infrastructure supporting
the monorepo. Secrets are managed via AWS Secrets Manager to centralize credential storage.

Apply the infrastructure with:

```bash
cd infrastructure/terraform
terraform init
terraform apply
```

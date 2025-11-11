# The Socratic Method Monorepo

This repository hosts a multi-service workspace exploring the Socratic method with a Python
backend, TypeScript frontend, shared packages, and Terraform infrastructure code.

## Structure

- `backend/` – FastAPI service managed via Poetry with Celery for background tasks.
- `frontend/` – Next.js application with TypeScript and Tailwind CSS for workspace UIs.
- `packages/common/` – Shared Python models distributed across services.
- `infrastructure/` – Terraform configuration for AWS networking and secrets management.

## Getting Started

Refer to the README in each subdirectory for environment-specific setup instructions.

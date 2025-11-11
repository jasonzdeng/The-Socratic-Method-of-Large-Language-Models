terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "network" {
  source = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "socratic-network"
  cidr = var.vpc_cidr

  azs             = var.availability_zones
  public_subnets  = var.public_subnets
  private_subnets = var.private_subnets

  enable_nat_gateway = true
}

resource "aws_secretsmanager_secret" "backend_celery" {
  name        = "socratic/backend/celery"
  description = "Celery broker credentials"
}

resource "aws_secretsmanager_secret_version" "backend_celery" {
  secret_id     = aws_secretsmanager_secret.backend_celery.id
  secret_string = jsonencode({
    broker_url  = var.celery_broker_url,
    result_backend = var.celery_result_backend,
  })
}

output "vpc_id" {
  description = "Identifier for the created VPC"
  value       = module.network.vpc_id
}

output "celery_secret_arn" {
  description = "ARN of the secrets manager secret that stores Celery credentials"
  value       = aws_secretsmanager_secret.backend_celery.arn
}

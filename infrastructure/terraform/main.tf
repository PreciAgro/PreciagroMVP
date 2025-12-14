# =============================================================================
# PreciAgro Infrastructure - Terraform Configuration
# =============================================================================
# This is the root configuration for environment-specific deployments.
# Each environment (dev, staging, production) should have its own directory
# with a main.tf that references shared modules.
# =============================================================================

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }
}

# =============================================================================
# Variables
# =============================================================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "Primary region for resources"
  type        = string
  default     = "europe-west1"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}

variable "engines" {
  description = "Map of engines to deploy"
  type = map(object({
    replicas      = number
    port          = number
    cpu_request   = string
    memory_request = string
    cpu_limit     = string
    memory_limit  = string
  }))
  default = {
    crop-intelligence = {
      replicas       = 2
      port           = 8082
      cpu_request    = "100m"
      memory_request = "256Mi"
      cpu_limit      = "500m"
      memory_limit   = "512Mi"
    }
    data-integration = {
      replicas       = 2
      port           = 8101
      cpu_request    = "100m"
      memory_request = "256Mi"
      cpu_limit      = "500m"
      memory_limit   = "512Mi"
    }
    geo-context = {
      replicas       = 2
      port           = 8102
      cpu_request    = "100m"
      memory_request = "256Mi"
      cpu_limit      = "500m"
      memory_limit   = "512Mi"
    }
  }
}

# =============================================================================
# Locals
# =============================================================================

locals {
  common_labels = {
    project     = "preciagro"
    environment = var.environment
    managed_by  = "terraform"
  }
}

# =============================================================================
# Outputs
# =============================================================================

output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "Primary region"
  value       = var.region
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

# PreciAgro Infrastructure

This directory contains Infrastructure as Code (IaC) for PreciAgro.

## Structure

```
infrastructure/
├── terraform/
│   ├── main.tf              # Root configuration
│   ├── environments/
│   │   ├── dev/             # Development environment
│   │   ├── staging/         # Staging environment
│   │   └── production/      # Production environment
│   └── modules/
│       ├── gke/             # GKE cluster module
│       ├── database/        # Cloud SQL module
│       ├── networking/      # VPC and networking
│       └── monitoring/      # Observability stack
├── kubernetes/
│   ├── base/                # Base manifests
│   └── overlays/            # Environment-specific overlays
└── docker/
    └── compose/             # Docker Compose files
```

## Quick Start

### Prerequisites

- Terraform >= 1.6.0
- GCloud CLI configured
- kubectl configured

### Deploy Development Environment

```bash
cd infrastructure/terraform/environments/dev
terraform init
terraform plan
terraform apply
```

### Deploy Staging Environment

```bash
cd infrastructure/terraform/environments/staging
terraform init
terraform plan
terraform apply
```

## Security

- All secrets managed via External Secrets Operator
- No secrets stored in Terraform state
- State files stored in encrypted GCS buckets
- RBAC enforced via Kubernetes RBAC

## Compliance

- GDPR: EU region deployment (europe-west1)
- SOC 2: Audit logging enabled
- Zimbabwe Data Protection: Africa region option

## Modules

### GKE Cluster
Provisions GKE cluster with:
- Private nodes
- Workload identity
- Cluster autoscaling
- Node auto-repair/upgrade

### Database
Provisions Cloud SQL with:
- PostgreSQL 15
- Automated backups
- High availability (production)
- Private IP only

### Networking
Provisions VPC with:
- Private subnets
- Cloud NAT for egress
- Cloud Armor for ingress protection

### Monitoring
Provisions observability stack:
- Prometheus (via Helm)
- Grafana (via Helm)
- Custom dashboards

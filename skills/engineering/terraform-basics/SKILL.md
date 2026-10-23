---
name: terraform-basics
description: Use when writing or operating Terraform infrastructure as
  code on an authorized engineering task. Covers init plan apply workflow,
  HCL resource and variable syntax, outputs, state management and locking,
  remote backends, modules, workspaces, fmt and validate checks, and safe
  destroy procedures. Use when provisioning cloud resources
  reproducibly, reviewing Terraform code, or recovering from a broken
  state file.
version: 1.0.0
domain: engineering
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [cloud-security-basics, git-workflows]
tools:
  - name: Terraform
    version: 1.9
---

Terraform declares infrastructure in HCL files and converges real cloud
resources to match. This skill covers the safe operating loop
(init, plan, apply), the HCL building blocks, state handling (the part
that bites everyone eventually), modules for reuse, and the checks
that keep `apply` from surprising you. All examples use Terraform 1.9
syntax.

## Quick Workflow

1. Write HCL in a versioned directory: providers, variables,
   resources, outputs.
2. Run `terraform fmt` and `terraform validate` before every plan.
3. Run `terraform plan -out=tfplan` and read the whole plan: every
   create, update, and destroy must be expected.
4. Apply the saved plan file, never re-plan at apply time.
5. Store state in a remote backend with locking; never commit
   `*.tfstate` to git.
6. Reuse code with modules; pin module sources to versions or
   commits.
7. Separate environments with workspaces or, better, separate state
   per environment.
8. Destroy deliberately: plan the destroy, confirm the blast radius,
   then run it.

## 1. First configuration

```bash
terraform version

mkdir tf-demo && cd tf-demo
cat > main.tf <<'EOF'
terraform {
  required_version = ">= 1.9.0"
  required_providers {
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

resource "random_pet" "name" {
  length = 2
}

resource "random_password" "db" {
  length  = 24
  special = true
}
EOF

cat > outputs.tf <<'EOF'
output "pet_name" {
  value = random_pet.name.id
}

output "db_password" {
  value     = random_password.db.result
  sensitive = true
}
EOF

terraform init
terraform fmt
terraform validate
terraform plan -out=tfplan
terraform apply tfplan
terraform output pet_name
```

`init` downloads providers, `validate` checks syntax without cloud
access, `plan -out` freezes the exact change set, and `apply tfplan`
executes exactly that. Mark secret outputs `sensitive = true` so they
do not print in logs.

## 2. Variables and configuration

```bash
cat > variables.tf <<'EOF'
variable "environment" {
  description = "Deployment environment"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod."
  }
}

variable "instance_count" {
  description = "Number of instances"
  type        = number
  default     = 2
}

variable "tags" {
  description = "Tags applied to all resources"
  type        = map(string)
  default     = {}
}
EOF

# Supply values without editing files
cat > dev.tfvars <<'EOF'
environment    = "dev"
instance_count = 1
tags = { team = "platform", costcenter = "eng" }
EOF

terraform plan -var-file=dev.tfvars -out=tfplan
```

Variables with `validation` blocks reject bad input at plan time.
Pass secrets via `TF_VAR_` environment variables or a secrets
manager, never in committed `.tfvars` files:

```bash
export TF_VAR_db_password="$(openssl rand -hex 24)"
terraform plan -out=tfplan
```

## 3. State and remote backends

State maps your HCL to real resource IDs. Lose it and Terraform
forgets what it manages; corrupt it and Terraform fights reality.

```bash
# Local state exists after apply: inspect, do not hand-edit
ls -la *.tfstate*
terraform state list
terraform show -json | head -c 500; echo

# Move a resource to a new address after refactoring (no recreation)
terraform state mv 'random_pet.name' 'random_pet.service_name'

# Remove something from management WITHOUT deleting the real resource
terraform state rm 'random_password.db'
```

Configure a remote backend before a team touches the project:

```hcl
terraform {
  backend "s3" {
    bucket         = "myorg-tfstate"
    key            = "demo/terraform.tfstate"
    region         = "eu-west-1"
    encrypt        = true
    dynamodb_table = "tfstate-locks"
  }
}
```

```bash
# Migrate local state into the backend (answers yes to copy)
terraform init -migrate-state
```

Remote state with locking (S3 plus DynamoDB, or Terraform Cloud)
stops two applies from corrupting state concurrently. State files
contain secrets in plain text: encrypt the backend and restrict who
can read it.

## 4. Modules for reuse

```bash
mkdir -p modules/network
cat > modules/network/main.tf <<'EOF'
variable "name" {
  type = string
}
variable "cidr" {
  type = string
}

resource "random_pet" "net" {
  length = 2
}

output "network_name" {
  value = "${var.name}-${random_pet.net.id}"
}
output "cidr" {
  value = var.cidr
}
EOF

cat > main.tf <<'EOF'
module "network" {
  source = "./modules/network"
  name   = "demo"
  cidr   = "10.0.0.0/16"
}
EOF

terraform init   # installs local modules too
terraform plan -out=tfplan
```

Pin remote modules to a version or commit: `source =
"git::https://example.com/mod.git?ref=v2.1.0"`. Unpinned modules
change under you. Keep modules small and single-purpose; a module
that provisions a network, a database, and monitoring is three
modules wearing a trench coat.

## 5. Workspaces and environments

```bash
# Workspaces give each environment its own state in one backend
terraform workspace new dev
terraform workspace new prod
terraform workspace list
terraform workspace select dev
terraform plan -var-file=dev.tfvars -out=tfplan

# The workspace name is available in configuration
# terraform.workspace == "dev"
```

For serious setups, prefer completely separate directories or
backend keys per environment over workspaces: a mistaken `workspace
select` has destroyed production before. Either way, production
applies happen from CI with approvals, not from laptops.

## 6. Importing existing resources

```bash
# Bring a manually created resource under management
cat > import.tf <<'EOF'
import {
  to = random_pet.legacy
  id = "existing-id-here"
}
EOF

terraform plan -generate-config-out=generated.tf
# Review generated.tf, move the resource block where it belongs,
# delete import.tf, then apply
terraform apply -auto-approve
```

`plan -generate-config-out` drafts the HCL for you; always review it
before applying, because generated config may include defaults you do
not want.

## 7. Safe destroy

```bash
# See exactly what destroy would remove, first
terraform plan -destroy -out=destroy.plan

# Then destroy only after reading it
terraform apply destroy.plan

# Remove one resource without touching the rest
terraform plan -destroy -target=random_pet.name -out=one.plan
terraform apply one.plan
```

Protect critical resources from accidental deletion in HCL:

```hcl
resource "random_pet" "important" {
  length = 2
  lifecycle {
    prevent_destroy = true
  }
}
```

`prevent_destroy` makes `terraform destroy` fail rather than delete
the resource; removing the protection is a deliberate code change.

## Edge cases

- `terraform init` fails with provider checksum mismatch. A proxy
  or mirror served a different binary; verify network trust, pin
  provider versions, and consider a provider mirror you control.
- State lock stuck after a crashed apply. Confirm no apply is
  running, then `terraform force-unlock <lock-id>`; the lock ID is
  in the error message. Never force-unlock while an apply is alive.
- Plan wants to recreate a resource you did not touch. Usually a
  provider upgrade changed defaults, or someone edited the resource
  in the cloud console; use `terraform plan -refresh-only` to see
  drift, then decide whether to import the drift or revert it.
- Secrets appear in plan output or logs. Mark outputs sensitive,
  avoid `TF_LOG=DEBUG` on shared CI, and remember state files hold
  secrets: encrypt backends and limit read access.
- `apply` partially fails halfway. Fix the root cause and re-run
  `plan` plus `apply`; Terraform resumes from state. Do not hand-edit
  cloud resources to "help", that widens the drift.
- Module update changes everything. Pin `?ref=` on git sources and
  version constraints on registry modules; review the plan diff of
  module upgrades like code review.
- Two engineers apply at once without a backend lock. One state
  wins and resources orphan; this is why remote backends with
  locking are mandatory for teams, not optional.

## Detection and defender view

For engineering skills this section covers detecting misuse and
misconfiguration. Terraform misconfiguration shows up as state files
committed to git (grep for `*.tfstate` in repos), backends without
encryption, `0.0.0.0/0` security group rules declared in HCL, and
providers configured with long-lived admin keys instead of short
lived credentials. Detect misuse by scanning plans in CI for
destructive changes (`terraform plan -detailed-exitcode` plus a
policy check), requiring plan review before apply, and alerting on
applies run outside the approved pipeline. Drift between state and
reality (`plan -refresh-only` showing unexpected changes) can
indicate manual console changes or compromise; investigate before
re-applying. Publicly readable state backends leak secrets and full
infrastructure maps, so audit bucket policies on every state bucket.

## Key references

- Terraform 1.9 documentation: https://developer.hashicorp.com/terraform/docs
- HCL language syntax: https://developer.hashicorp.com/terraform/language/syntax
- State management: https://developer.hashicorp.com/terraform/language/state
- Backends: https://developer.hashicorp.com/terraform/language/backend
- CIS Terraform benchmarks (cloud-specific): https://www.cisecurity.org/benchmarks
- CWE-798 (Use of Hard-coded Credentials): secrets in HCL and state.
- CWE-732 (Incorrect Permission Assignment for Critical Resource):
  world-readable state backends.

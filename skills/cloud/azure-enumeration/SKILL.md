---
name: azure-enumeration
description: Use when enumerating a Microsoft Azure tenant or subscription
  during an authorized cloud assessment, bug bounty engagement, or lab
  exercise. Covers subscription and identity context, Microsoft Entra ID
  users, groups and service principals, Azure RBAC role assignments,
  virtual machines, storage accounts, Key Vaults, networking, and Azure
  Policy with Azure CLI 2.65 and Python 3.12. Use when you hold Azure
  credentials for a test tenant and need to map what the principal can
  reach, or when the scope permits unauthenticated checks of public
  storage endpoints.
version: 1.0.0
domain: cloud
lifecycle: stable
last_verified: 2026-10-23
requires: []
extends: []
relates: [cloud-security-basics, recon-passive]
tools:
  - name: Azure CLI
    version: 2.65
  - name: Python
    version: 3.12
---

Azure enumeration maps what an identity can see and touch inside a
tenant and its subscriptions: who you are, which Entra ID objects
exist, which RBAC roles you hold, and which resources are deployed.
This skill covers the authorized operator workflow with the Azure CLI:
identity context, Entra ID, RBAC assignments, compute, storage, Key
Vaults, networking, and policy, plus safe unauthenticated checks of
public storage. Use it against your own tenants, in-scope bug bounty
targets, and lab environments only. Never enumerate tenants you do not
have written permission to test.

## Quick Workflow

1. Confirm identity and subscription: `az account show`, tenant ID,
   user type, and login method.
2. List all subscriptions and tenants the principal can reach, then
   set the working subscription explicitly.
3. Enumerate Microsoft Entra ID: users, groups, service principals,
   and app registrations.
4. Enumerate Azure RBAC: role assignments scoped to the principal,
   then widen to subscription scope if readable.
5. Survey compute: virtual machines, VM extensions, disks, and
   snapshots.
6. Survey storage accounts: containers, public access settings, and
   keys only if the scope allows.
7. Survey Key Vaults: vault list, then keys, secrets, and certificates
   metadata (values only with explicit permission).
8. Survey networking: virtual networks, public IPs, network security
   groups, and load balancers.
9. Check Azure Policy assignments and Defender for Cloud posture.
10. Run safe unauthenticated checks: public blob containers and static
    websites inside the scope.
11. Save every command and its raw JSON output for the report.

## 1. Identity and subscription context

```bash
# Who am I, which subscription and tenant are active
az account show --query '{user:name, tenant:tenantId, sub:name, subId:id}'

# Every subscription and tenant reachable with these credentials
az account list --query '[].{name:name, id:id, tenant:tenantId, state:state}' \
  --output table

# Work explicitly: never rely on the default subscription
az account set --subscription "<SUBSCRIPTION-ID-OR-NAME>"

# Login method and active cloud (AzureCloud vs national clouds)
az account show --query '{cloud:environmentName}' --output text
az ad signed-in-user show --query '{upn:userPrincipalName, id:id}' 2>/dev/null
```

If `az ad` commands are deprecated in your CLI build, the same data is
available through Microsoft Graph with `az rest`; the queries below show
both where it matters.

## 2. Microsoft Entra ID enumeration

Entra ID (formerly Azure AD) holds the identities. Read users, groups,
service principals, and the apps behind them.

```bash
# Users: UPN, display name, type (member vs guest)
az ad user list --query '[].{upn:userPrincipalName, name:displayName, type:userType}' \
  --output table

# Groups and their membership
az ad group list --query '[].{name:displayName, id:id}' --output table
az ad group member list --group "<GROUP-ID-OR-NAME>" \
  --query '[].{name:displayName, upn:userPrincipalName}' --output table

# Service principals (managed identities and app identities)
az ad sp list --all --query '[].{name:displayName, appId:appId, type:servicePrincipalType}' \
  --output table

# App registrations behind the service principals
az ad app list --all --query '[].{name:displayName, appId:appId}' \
  --output table
```

Graph fallback when `az ad` is unavailable:

```bash
az rest --method get \
  --url 'https://graph.microsoft.com/v1.0/users?$select=userPrincipalName,displayName,userType' \
  --query 'value[].[userPrincipalName,displayName,userType]' --output table
```

## 3. Azure RBAC role assignments

RBAC decides what the principal can do at each scope (management
group, subscription, resource group, resource).

```bash
# Role assignments for the signed-in principal at subscription scope
MY_ID=$(az ad signed-in-user show --query id -o tsv 2>/dev/null)
az role assignment list --assignee "$MY_ID" --all \
  --query '[].{role:roleDefinitionName, scope:scope}' --output table

# All assignments in the subscription (needs read permission)
az role assignment list --all \
  --query '[].{principal:principalName, role:roleDefinitionName, scope:scope}' \
  --output table | head -40

# What a specific role definition actually grants
az role definition list --name "Contributor" \
  --query '[].{name:roleName, actions:permissions[0].actions, notActions:permissions[0].notActions}'

# Custom role definitions (often over-permissive)
az role definition list --custom-role-only true \
  --query '[].{name:roleName, actions:permissions[0].actions}' --output table
```

High-value roles to flag: Owner, Contributor, User Access
Administrator, Key Vault Secrets Officer, Storage Blob Data
Contributor, and any custom role with wildcard actions.

## 4. Compute enumeration

```bash
# Virtual machines: name, size, OS, power state, resource group
az vm list --query '[].{name:name, rg:resourceGroup, size:hardwareProfile.vmSize, os:storageProfile.osDisk.osType}' \
  --output table
az vm list -d --query '[].{name:name, power:powerState, publicIp:publicIps, privateIp:privateIps}' \
  --output table

# VM extensions (custom scripts and agents are interesting)
az vm extension list --vm-name <VM> --resource-group <RG> \
  --query '[].{name:name, publisher:publisher, type:virtualMachineExtensionType}' \
  --output table

# Managed disks and snapshots (may contain copies of data)
az disk list --query '[].{name:name, rg:resourceGroup, size:diskSizeGb}' \
  --output table
az snapshot list --query '[].{name:name, rg:resourceGroup}' --output table
```

## 5. Storage account enumeration

Storage accounts hold blobs, files, queues, and tables. Public blob
access at the account level is the first thing to check.

```bash
# Storage accounts and their public access posture
az storage account list \
  --query '[].{name:name, rg:resourceGroup, publicBlob:allowBlobPublicAccess, httpsOnly:enableHttpsTrafficOnly}' \
  --output table

# Containers inside one account (needs data-plane permission or key)
az storage container list --account-name <ACCOUNT> \
  --query '[].{name:name, public:properties.publicAccess}' --output table

# Static website hosting flag
az storage blob service-properties show --account-name <ACCOUNT> \
  --query 'staticWebsite'
```

Only list storage account KEYS when the scope allows it; keys are
full-control credentials:

```bash
az storage account keys list --account-name <ACCOUNT> \
  --query '[].{name:keyName}' --output table
```

## 6. Key Vault enumeration

```bash
# Vaults: name, SKU, network posture
az keyvault list --query '[].{name:name, rg:resourceGroup}' --output table
az keyvault show --name <VAULT> \
  --query '{sku:properties.sku.name, publicNet:properties.publicNetworkAccess}'

# Object names only (metadata pass; values need explicit permission)
az keyvault secret list --vault-name <VAULT> \
  --query '[].{name:name, enabled:attributes.enabled}' --output table
az keyvault key list --vault-name <VAULT> \
  --query '[].{name:name}' --output table
az keyvault certificate list --vault-name <VAULT> \
  --query '[].{name:name}' --output table
```

Read a secret VALUE only when the rules of engagement allow it, and
record exactly which secrets you touched.

## 7. Network enumeration

```bash
# Virtual networks, subnets, and peerings
az network vnet list \
  --query '[].{name:name, rg:resourceGroup, cidr:addressSpace.addressPrefixes}' \
  --output table

# Public IPs and what they attach to
az network public-ip list \
  --query '[].{ip:ipAddress, name:name, rg:resourceGroup}' --output table

# NSG rules: open inbound rules are the interesting part
az network nsg list --query '[].{name:name, rg:resourceGroup}' --output table
az network nsg rule list --nsg-name <NSG> --resource-group <RG> \
  --query '[?direction==`Inbound`].{name:name, prio:priority, port:destinationPortRange, src:sourceAddressPrefix, access:access}' \
  --output table

# Load balancers and application gateways
az network lb list --query '[].{name:name, rg:resourceGroup}' --output table
```

## 8. Policy and Defender posture

```bash
# Policy assignments that constrain the subscription
az policy assignment list \
  --query '[].{name:name, display:displayName, scope:scope}' --output table

# Microsoft Defender for Cloud pricing tiers (on = monitored)
az security pricing list --query '[].{name:name, tier:pricingTier}' \
  --output table 2>/dev/null
```

## 9. Unauthenticated checks

Some storage endpoints answer without credentials. Test only
in-scope accounts and stay read-only.

```bash
# Anonymous container listing (works only if public access is on)
curl -s "https://<ACCOUNT>.blob.core.windows.net/<CONTAINER>?restype=container&comp=list" \
  | head -c 600

# Static website endpoint
curl -s -o /dev/null -w '%{http_code}\n' \
  "https://<ACCOUNT>.z1.web.core.windows.net/"
```

## 10. Subscription sweep

```bash
for sub in $(az account list --query '[].id' -o tsv); do
  echo "=== $sub ==="
  az account set --subscription "$sub"
  az vm list --query '[].{name:name, rg:resourceGroup}' -o table
  az storage account list --query '[].name' -o tsv
  az keyvault list --query '[].name' -o tsv
done
```

## Edge cases

- `az ad` commands print deprecation warnings or fail on new CLI
  builds: use the `az rest` Microsoft Graph calls from section 2.
- Guest users (`userType == Guest`) have limited directory read by
  default; many list calls return partial results or 403.
- Role assignment list at subscription scope needs
  `Microsoft.Authorization/roleAssignments/read`; without it, fall
  back to assignments for your own principal only.
- Multiple tenants: `az account list` shows them all, but `az ad`
  queries run against the home tenant of the active subscription.
  Set the subscription first, then query.
- National clouds (Azure Government, Azure China) use different
  endpoints: log in with `az cloud set --name <CLOUD>` first.
- Storage data-plane calls fail without the right RBAC data role
  even when you can list the account; keys or SAS tokens may be the
  intended path, subject to scope.
- Output pagination: large tenants truncate lists; add `--all` where
  supported and follow `nextLink` in `az rest` calls.

## Escalation

- Directory reads are denied: query your own user and your own role
  assignments only, then pivot through group memberships you can
  see.
- No subscription read: try resource-group scope
  (`az group list`) and per-resource `az resource show --ids`.
- Look for privilege paths: User Access Administrator or Owner
  assignments let you grant yourself more; service principals with
  secrets you can read may hold higher roles.
- Check automation: `az automation account list` and runbooks,
  plus Logic Apps, often run as powerful managed identities.
- Managed identity on a VM you can reach: query the instance
  metadata token endpoint from inside the VM
  (`http://169.254.169.254/metadata/identity/oauth2/token`) to get
  tokens for the attached identity, only on in-scope VMs.
- Subscription has no permissions at all: enumerate the tenant-level
  surface (users, groups, apps) which often uses different
  permissions than subscription RBAC.

## Detection and defender view

Defenders see Azure enumeration in the Azure Activity Log and in
Microsoft Entra audit and sign-in logs: `List Role Assignments`,
`List Storage Accounts`, and directory read bursts from one
principal. Microsoft Defender for Cloud and Entra ID Protection
raise alerts on anomalous token use, impossible travel, and
unfamiliar locations. Key Vault and Storage diagnostic logs record
each data-plane access with caller identity. Durable defenses are
least-privilege RBAC (Reader instead of Contributor for humans who
only need visibility), Conditional Access policies blocking legacy
auth and risky sign-ins, and alerts on bulk directory reads or
role assignment changes. As the tester, keep call volume
reasonable, stay inside the agreed window, and never read secret
values or customer data beyond what the scope allows.

## Key references

- MITRE ATT&CK T1580 (Cloud Infrastructure Discovery): the tenant
  survey itself.
- MITRE ATT&CK T1526 (Cloud Service Discovery): per-service
  enumeration.
- MITRE ATT&CK T1087.004 (Account Discovery: Cloud Account):
  listing Entra ID users and groups.
- MITRE ATT&CK T1530 (Data from Cloud Storage): storage account
  inventory and reads.
- Azure CLI reference: https://learn.microsoft.com/cli/azure/
- Microsoft Graph API reference:
  https://learn.microsoft.com/graph/api/overview
- Azure RBAC documentation:
  https://learn.microsoft.com/azure/role-based-access-control/

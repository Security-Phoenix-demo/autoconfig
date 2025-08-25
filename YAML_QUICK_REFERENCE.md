# Phoenix Security YAML Quick Reference

## Configuration File Structure (Updated v4.8.3)

### run-config.yaml Options

```yaml
ConfigFiles:
  - /bv/core-structure-bv-7.yaml      # Config files to process

# User Management (NEW in v4.8.3)
CreateUsersForApplications: true        # Auto-create users from Responsable field

# Team Configuration
TeamsFolder: /bv/bv-Teams              # Custom teams folder path

# Hives Configuration  
EnableHives: false                      # Enable/disable hives system
HivesFile: bv/bv-hives.yaml            # Custom hives file path

# GitHub Integration
GitHubRepositories: []                  # GitHub repo URLs
GitHubRepoFolder: /path/to/repos       # Local clone folder
ConfigFileName: assetconfig.phoenix     # Config file name in repos
```

## Essential Structure

```yaml
# User Creation Control (NEW)
AllAccessAccounts: []                   # List of admin users
CreateUsersForApplications: true        # Auto-create users (optional)

DeploymentGroups:
  - AppName: "MyApp"                    # Required
    ReleaseDefinitions: []              # Required (can be empty)
    Responsable: "owner@company.com"    # Required - User auto-created if missing
    TeamNames: ["Team1"]                # Optional
    Tier: 2                             # Optional (1-10)
    Components:
      - ComponentName: "my-component"   # Required
        # ... component fields

Environment Groups:
  - Name: "Production"                  # Required
    Type: "CLOUD"                       # Required (CLOUD/INFRA)
    Status: "Production"                # Required
    Responsable: "owner@company.com"    # Required - User auto-created if missing
    Tier: 1                             # Required (1-10)
    Services:
      - Service: "my-service"           # Required
        Type: "Cloud"                   # Required (Cloud/Container/Infra)
        # ... service fields
```

## Asset Matching Fields

| Field | Format | Example |
|-------|--------|---------|
| `RepositoryName` | String or List | `"repo-name"` or `["repo1", "repo2"]` |
| `SearchName` | String | `"search-term"` |
| `AssetType` | String | See AssetType table below |
| `Tags` | List | `["tag1", "tag2"]` |
| `Cidr` | String | `"10.1.1.0/24"` |
| `ProviderAccountId` | **List** | `["12345678-1234-1234-1234-123456789012"]` |

## Supported AssetType Values

| AssetType | Purpose | When to Use |
|-----------|---------|-------------|
| `REPOSITORY` | Source code repos | GitHub, GitLab repositories |
| `SOURCE_CODE` | Source files | Code files, source artifacts |
| `BUILD` | Build artifacts | JAR files, executables |
| `WEBSITE_API` | Web apps & APIs | REST APIs, web services |
| `CONTAINER` | Containers | Docker, Kubernetes pods |
| `INFRA` | Infrastructure | Servers, networks |
| `CLOUD` | Cloud resources | AWS/Azure/GCP services |
| `WEB` | Web assets | Websites, web apps |
| `FOSS` | Open source | Third-party libraries |
| `SAST` | Security scans | Static analysis results |

## Tag Types

### Asset Matching Tags (for rules)
```yaml
Tags:
  - "environment:production"
  - "team:webdev"
  - "critical"
```

### Component Metadata Tags (for labels)
```yaml
Tags_label:
  - "Environment: Production"
  - "ComponentType: service"
```

## Multi-Condition Rules

```yaml
# Single rule
MultiConditionRule:
  AssetType: "REPOSITORY"
  RepositoryName: "my-repo"
  Tags: ["production"]

# Multiple rules
MULTI_MultiConditionRules:
  - AssetType: "CONTAINER"
    SearchName: "web-app"
    Tags: ["web"]
  - AssetType: "REPOSITORY"
    RepositoryName: "api-repo"
    Tags: ["api"]
```

## Integrations

```yaml
Ticketing:
  - TIntegrationName: "Jira-prod"
    Backlog: "PROJECT-KEY"

Messaging:
  - MIntegrationName: "Slack-prod"
    Channel: "alerts-channel"
```

## Common Patterns

### Simple Component
```yaml
- ComponentName: "web-frontend"
  TeamNames: ["WebTeam"]
  RepositoryName: "company/frontend-repo"
  Tags: ["frontend", "web"]
  Tags_label: ["Environment: Production"]
```

### Component with Cloud Resources
```yaml
- ComponentName: "api-service"
  AssetType: "CONTAINER"
  SearchName: "api-container"
  ProviderAccountId: ["12345678-1234-1234-1234-123456789012"]
  Tags: ["api", "backend"]
```

### Infrastructure Service
```yaml
- Service: "database"
  Type: "Cloud"
  AssetType: "INFRA"
  Cidr: "10.1.0.0/16"
  Tags: ["database", "storage"]
```

## Running the Linter

```bash
# Quick validation check
cd "Python script"
python3 -c "
from providers.Linter import *
import yaml
with open('Resources/core-structure.yaml', 'r') as f:
    config = yaml.safe_load(f)
for app in config.get('DeploymentGroups', []):
    valid, errors = validate_application(app)
    print(f'{app.get(\"AppName\")}: {\"✅\" if valid else \"❌\" + str(errors)}')
"
```

## Validation Checklist

- [ ] `ProviderAccountId` is a **list**, not a string
- [ ] Required fields are present (`AppName`, `ReleaseDefinitions`, `Responsable`)
- [ ] Email addresses are valid format
- [ ] Asset types use **only** allowed values from the table above
- [ ] Tier values are 1-10 (higher = more critical)
- [ ] Team names match existing teams
- [ ] Tags use consistent format
- [ ] Multi-condition rules have proper indentation (no extra dashes)
- [ ] YAML structure is valid (spaces, not tabs)

## Common Mistakes & Fixes

### **ProviderAccountId Format**
❌ **Wrong**: `ProviderAccountId: "12345678-1234-1234-1234-123456789012"`  
✅ **Right**: `ProviderAccountId: ["12345678-1234-1234-1234-123456789012"]`

### **Multi-Condition Rule Structure**
❌ **Wrong**: 
```yaml
MULTI_MultiConditionRules:
- AssetType: CLOUD
  - ProviderAccountId:  # Extra dash breaks YAML
    - "uuid"
```
✅ **Right**: 
```yaml
MULTI_MultiConditionRules:
- AssetType: CLOUD
  ProviderAccountId:    # No dash - it's a key-value pair
    - "uuid"
```

### **AssetType Values**
❌ **Wrong**: `AssetType: "WEBAPP"` or `AssetType: "API"`  
✅ **Right**: `AssetType: "WEBSITE_API"`

❌ **Wrong**: `AssetType: "Container"` (wrong case)  
✅ **Right**: `AssetType: "CONTAINER"`

### **Required Fields**
❌ **Wrong**: Missing required fields  
✅ **Right**: Always include `AppName`, `ReleaseDefinitions: []`, `Responsable`

### **Tag Purposes**
❌ **Wrong**: Mixing tag types  
✅ **Right**: Use `Tags` for asset matching, `Tags_label` for component metadata

## Recent Updates ✨

- ✅ **New AssetTypes**: Added `CLOUD`, `WEB`, `FOSS`, `SAST` support
- ✅ **YAML Parsing**: Fixed multi-condition rule indentation issues  
- ✅ **Validation**: Enhanced linter validation and error reporting
- ✅ **API Sync**: AssetType values now match Phoenix Security API 
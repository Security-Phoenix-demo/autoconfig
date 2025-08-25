# Phoenix Security YAML Configuration Guide

## Table of Contents
1. [Overview](#overview)
2. [File Structure](#file-structure)
3. [DeploymentGroups (Applications)](#deploymentgroups-applications)
4. [Components](#components)
5. [Environment Groups](#environment-groups)
6. [Services](#services)
7. [Multi-Condition Rules](#multi-condition-rules)
8. [Field Reference](#field-reference)
9. [Examples](#examples)
10. [Best Practices](#best-practices)
11. [Validation](#validation)

## Overview

The Phoenix Security YAML configuration file defines applications, components, environments, and services within your security infrastructure. It supports asset matching rules, team assignments, integrations, and hierarchical organization.

## File Structure

```yaml
# Optional: Global access accounts
AllAccessAccounts:
 - ciso@company.com

# Main application definitions
DeploymentGroups:
  - AppName: MyApplication
    # ... application configuration

# Environment and service definitions  
Environment Groups:
  - Name: Production
    # ... environment configuration
```

## Configuration File Organization

The Phoenix Security system supports organizing configuration files using the `run-config.yaml` file, which can now reference files in subfolders for better organization.

### run-config.yaml Structure

```yaml
# Configuration files to load (supports subfolders)
ConfigFiles:
  - core-structure.yaml                     # Direct file in Resources/
  - /mimecast/mimecast-core-structure.yaml  # Subfolder path
  - /q2/q2_container_services_config.yaml   # Another subfolder
  - /client1/client1-applications.yaml      # Client-specific config

# GitHub repository configurations (optional)
GitHubRepositories:
  - https://github.com/org/config-repo

# GitHub configuration settings
GitHubRepoFolder: /path/to/local/repos
ConfigFileName: assetconfig.phoenix
promptOnDuplicate: false
```

### Subfolder Organization Examples

#### Multi-Client Setup
```yaml
ConfigFiles:
  - /acme-corp/acme-applications.yaml
  - /beta-inc/beta-infrastructure.yaml
  - /gamma-ltd/gamma-services.yaml
  - shared-resources.yaml
```

#### Environment-Based Organization
```yaml
ConfigFiles:
  - /production/prod-apps.yaml
  - /staging/staging-apps.yaml
  - /development/dev-apps.yaml
  - /shared/common-infrastructure.yaml
```

#### Domain-Based Structure
```yaml
ConfigFiles:
  - /security/security-services.yaml
  - /finance/finance-applications.yaml
  - /hr/hr-systems.yaml
  - core-infrastructure.yaml
```

### Path Syntax Rules

- **Subfolder paths**: Start with `/` (e.g., `/mimecast/config.yaml`)
- **Direct files**: No leading `/` (e.g., `core-structure.yaml`)
- **Case sensitive**: Use exact folder and file names
- **Supported extensions**: `.yaml` and `.yml`
- **Relative to Resources**: All paths are relative to the `Resources/` directory

## DeploymentGroups (Applications)

Applications are the top-level containers that group related components together.

### Required Fields
- `AppName`: Unique application name
- `ReleaseDefinitions`: List of release definitions (can be empty: `[]`)
- `Responsable`: Email of the application owner (must exist in Phoenix)

### Optional Fields
- `AppID`: Numeric application identifier
- `Status`: Application status (e.g., "Production", "NotStarted")
- `TeamNames`: List of responsible teams
- `Domain`: Business domain classification
- `SubDomain`: Business subdomain classification
- `Tier`: Criticality level (1-10, higher = more critical, default: 5)
- `Deployment_set`: Deployment grouping identifier
- `Ticketing`: Ticketing system integration
- `Messaging`: Messaging system integration
- `Components`: List of application components

### Example Application
```yaml
DeploymentGroups:
  - AppName: MyWebApplication
    Status: Production
    TeamNames:
      - WebTeam
      - SecurityTeam
    Domain: E-Commerce
    SubDomain: Customer Portal
    ReleaseDefinitions: []
    Responsable: owner@company.com
    Tier: 2
    Deployment_set: web-services
    Ticketing:
      - TIntegrationName: Jira-prod
        Backlog: WEB-PROJECT
    Messaging:
      - MIntegrationName: Slack-prod
        Channel: web-alerts
    Components:
      # ... component definitions
```

## Components

Components are the building blocks within applications that represent specific services, repositories, or assets.

### Required Fields
- `ComponentName`: Unique component name within the application

### Optional Fields
- `Status`: Component status
- `AppID`: Application ID (auto-assigned)
- `Type`: Component type
- `TeamNames`: Responsible teams (inherits from application if not specified)
- `Tier`: Criticality level (1-10)
- `Domain`: Business domain
- `SubDomain`: Business subdomain
- `AutomaticSecurityReview`: Enable/disable automatic security reviews
- `Deployment_set`: Deployment grouping
- `Ticketing`: Component-specific ticketing integration
- `Messaging`: Component-specific messaging integration

### Asset Matching Fields
Components can match assets using various criteria:

- `RepositoryName`: Repository name(s) - string or list
- `SearchName`: General search term
- `AssetType`: Asset type (`REPOSITORY`, `SOURCE_CODE`, `BUILD`, `WEBSITE_API`, `CONTAINER`, `INFRA`)
- `Tags`: List of tag values for asset matching rules
- `Tag_label`/`Tags_label`: Component metadata tags (not for asset matching)
- `Cidr`: Network CIDR block
- `Fqdn`: List of fully qualified domain names
- `Netbios`: List of NetBIOS names
- `OsNames`: List of operating system names
- `Hostnames`: List of hostnames
- `ProviderAccountId`: List of cloud provider account IDs
- `ProviderAccountName`: List of cloud provider account names
- `ResourceGroup`: List of resource group names

### Example Component
```yaml
Components:
  - ComponentName: user-authentication-service
    Status: Production
    Type: Microservice
    TeamNames:
      - AuthTeam
    Tier: 1
    Domain: Security
    SubDomain: Identity Management
    RepositoryName: company/auth-service
    AssetType: REPOSITORY
    Tags:
      - "auth"
      - "critical"
    Tags_label:  # Metadata tags for the component itself
      - "Environment: Production"
      - "ComponentType: service"
    Cidr: 10.1.1.0/24
    ProviderAccountId:
      - "12345678-1234-1234-1234-123456789012"
```

## Environment Groups

Environment Groups define operational environments and their associated services.

### Required Fields
- `Name`: Environment name
- `Type`: Environment type (`CLOUD`, `INFRA`)
- `Status`: Environment status
- `Responsable`: Environment owner email
- `Tier`: Criticality level (1-10)

### Optional Fields
- `TeamName`: Responsible team
- `Services`: List of services in this environment
- `Ticketing`: Environment-level ticketing integration
- `Messaging`: Environment-level messaging integration

### Example Environment Group
```yaml
Environment Groups:
  - Name: Production-Cloud
    Type: CLOUD
    Status: Production
    Responsable: cloudops@company.com
    Tier: 1
    TeamName: CloudOps
    Services:
      # ... service definitions
```

## Services

Services are operational units within environments that handle specific functions.

### Required Fields
- `Service`: Service name
- `Type`: Service type (`Cloud`, `Container`, `Infra`)

### Optional Fields
- `Tier`: Criticality level
- `TeamName`: Responsible team
- `Deployment_set`: Deployment grouping
- `Deployment_tag`: Deployment tag for asset matching
- `Ticketing`: Service-specific ticketing
- `Messaging`: Service-specific messaging

### Asset Matching (same as Components)
Services support the same asset matching fields as components.

### Example Service
```yaml
Services:
  - Service: web-frontend
    Type: Cloud
    Tier: 2
    TeamName: WebTeam
    SearchName: frontend-app
    AssetType: CONTAINER
    Tags:
      - "frontend"
      - "public"
    ProviderAccountId:
      - "12345678-1234-1234-1234-123456789012"
```

## Multi-Condition Rules

Multi-condition rules allow complex asset matching using multiple criteria.

### Types of Multi-Condition Rules
1. `MultiConditionRule`: Single rule (dictionary)
2. `MULTI_MultiConditionRules`: Multiple rules (list of dictionaries)
3. `MultiConditionRules`: Alternative format for multiple rules
4. `MultiMultiConditionRules`: Alternative format for multiple rules

### Available Fields in Rules
All asset matching fields can be used:
- `RepositoryName`
- `SearchName` 
- `AssetType`
- `Tags` / `Tag` / `Tag_rule` / `Tags_rule`
- `Cidr`
- `Fqdn`
- `Netbios`
- `OsNames`
- `Hostnames`
- `ProviderAccountId`
- `ProviderAccountName`
- `ResourceGroup`

### Example Multi-Condition Rules
```yaml
Components:
  - ComponentName: complex-component
    # Single rule
    MultiConditionRule:
      AssetType: REPOSITORY
      RepositoryName: my-repo
      Tags:
        - "production"
        - "critical"
      ProviderAccountId:
        - "12345678-1234-1234-1234-123456789012"
    
    # Multiple rules
    MULTI_MultiConditionRules:
      - AssetType: CONTAINER
        SearchName: web-container
        Tags:
          - "web"
        ProviderAccountId:
          - "12345678-1234-1234-1234-123456789012"
      - AssetType: REPOSITORY
        RepositoryName: api-repo
        Tags:
          - "api"
```

## Field Reference

### Data Types and Formats

#### String Fields
```yaml
ComponentName: "my-component"
SearchName: "search-term"
Cidr: "10.1.1.0/24"
```

#### List Fields
```yaml
TeamNames:
  - "Team1"
  - "Team2"

ProviderAccountId:
  - "12345678-1234-1234-1234-123456789012"
  - "87654321-4321-4321-4321-210987654321"
```

#### Mixed String/List Fields
```yaml
# As string
RepositoryName: "single-repo"

# As list
RepositoryName:
  - "repo1"
  - "repo2"
```

#### Integer Fields
```yaml
Tier: 3
AppID: 12345
```

#### Boolean Fields
```yaml
AutomaticSecurityReview: true
```

#### Dictionary Fields (Integrations)
```yaml
Ticketing:
  - TIntegrationName: "Jira-prod"
    Backlog: "PROJECT-KEY"

Messaging:
  - MIntegrationName: "Slack-prod" 
    Channel: "alerts-channel"
```

### Asset Types

#### **✅ Supported AssetType Values (API-Validated)**
| AssetType | Purpose | Use Cases |
|-----------|---------|-----------|
| `REPOSITORY` | Source code repositories | GitHub repos, GitLab repos, version control |
| `SOURCE_CODE` | Source code assets | Code files, source artifacts |
| `BUILD` | Build artifacts | JAR files, executables, build outputs |
| `WEBSITE_API` | Web applications & APIs | Web services, REST APIs, web apps |
| `CONTAINER` | Container images/instances | Docker containers, Kubernetes pods |
| `INFRA` | Infrastructure components | Servers, networks, infrastructure |
| `CLOUD` | Cloud resources | AWS/Azure/GCP resources, cloud services |
| `WEB` | Web assets | Websites, web applications |
| `FOSS` | Open source components | Third-party libraries, dependencies |
| `SAST` | Static analysis assets | Code analysis results, security scans |

**Note**: These values are synchronized with the Phoenix Security API and validated by the linter.

### Tag Formats

#### Asset Matching Tags (Tags field)
```yaml
Tags:
  - "environment:production"
  - "team:webdev"
  - "critical"
```

#### Component Metadata Tags (Tags_label field)
```yaml
Tags_label:
  - "Environment: Production"
  - "ComponentType: service"
  - "Owner: WebTeam"
```

## Examples

### Complete Application Example
```yaml
DeploymentGroups:
  - AppName: E-Commerce-Platform
    Status: Production
    TeamNames:
      - ECommerceTeam
      - DevOpsTeam
    Domain: E-Commerce
    SubDomain: Online Store
    ReleaseDefinitions: []
    Responsable: ecommerce-owner@company.com
    Tier: 1
    Deployment_set: ecommerce
    
    Components:
      - ComponentName: product-catalog-service
        Status: Production
        Type: Microservice
        TeamNames:
          - ECommerceTeam
        Tier: 2
        Domain: E-Commerce
        SubDomain: Product Management
        RepositoryName: company/product-catalog
        AssetType: REPOSITORY
        Tags:
          - "microservice"
          - "product"
        Tags_label:
          - "Environment: Production"
          - "ComponentType: service"
        
        MULTI_MultiConditionRules:
          - AssetType: CONTAINER
            SearchName: product-catalog-container
            Tags:
              - "product-catalog"
            ProviderAccountId:
              - "12345678-1234-1234-1234-123456789012"
          - AssetType: REPOSITORY
            RepositoryName: company/product-catalog-tests
            Tags:
              - "testing"
```

### Complete Environment Example
```yaml
Environment Groups:
  - Name: Production-Environment
    Type: CLOUD
    Status: Production
    Responsable: production-owner@company.com
    Tier: 1
    TeamName: ProductionOps
    
    Services:
      - Service: load-balancer
        Type: Cloud
        Tier: 1
        TeamName: NetworkTeam
        SearchName: prod-lb
        AssetType: INFRA
        Tags:
          - "loadbalancer"
          - "production"
        ProviderAccountId:
          - "12345678-1234-1234-1234-123456789012"
        
        MULTI_MultiConditionRules:
          - AssetType: INFRA
            SearchName: lb-instance-1
            Tags:
              - "lb-primary"
          - AssetType: INFRA
            SearchName: lb-instance-2
            Tags:
              - "lb-backup"
```

## Best Practices

### 1. Naming Conventions
- Use descriptive, consistent names
- Follow your organization's naming standards
- Use hyphens or underscores consistently

### 2. Team Management
- Define teams in your organization first
- Use consistent team names across applications
- Assign appropriate teams to components

### 3. Criticality Levels (Tier)
- 1-3: Critical systems (production, customer-facing)
- 4-6: Important systems (internal tools, development)
- 7-10: Low priority systems (experimental, deprecated)

### 4. Asset Matching Strategy
- Use specific matching criteria to avoid conflicts
- Combine multiple fields for precise matching
- Test rules to ensure they match intended assets

### 5. Tag Organization
- Use consistent tag formats
- Separate metadata tags (`Tags_label`) from matching tags (`Tags`)
- Use key:value format for structured tags

### 6. Multi-Condition Rules
- Use when simple field matching isn't sufficient
- Keep rules as simple as possible while meeting requirements
- Document complex rule logic

## Validation

The system validates YAML structure and field formats using an integrated linter.

### Running the Linter

#### **Method 1: Direct Python Execution**
```bash
cd "Python script"
python3 -c "
from providers.Linter import *
import yaml

# Load and validate configuration
with open('Resources/core-structure.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Validate applications
for app in config.get('DeploymentGroups', []):
    valid, errors = validate_application(app)
    print(f'App {app.get(\"AppName\")}: {\"✅ VALID\" if valid else \"❌ ERRORS: \" + str(errors)}')
"
```

#### **Method 2: Through Main Script**
```bash
python3 run.py --validate-only
```

### Common Validation Errors
1. **Required field missing**: Ensure all required fields are present
2. **Invalid field type**: Check data types (string vs list vs integer)
3. **Invalid asset type**: Use only allowed asset type values (see AssetType table above)
4. **Invalid email format**: Ensure responsible person emails are valid
5. **Invalid ProviderAccountId format**: Must be a list, not a string
6. **YAML parsing errors**: Check indentation and structure
7. **Multi-condition rule errors**: Validate rule structure and field types

### Format Requirements
- `ProviderAccountId`: Must be a list of strings
  ```yaml
  # ✅ Correct
  ProviderAccountId:
    - "12345678-1234-1234-1234-123456789012"
  
  # ❌ Incorrect
  ProviderAccountId: "12345678-1234-1234-1234-123456789012"
  ```

- `Tags_label` vs `Tags`: Different purposes
  ```yaml
  # For component metadata
  Tags_label:
    - "Environment: Production"
  
  # For asset matching
  Tags:
    - "production"
    - "critical"
  ```

### Testing Your Configuration
1. Run the linting function to validate structure
2. Test with a small subset first
3. Verify asset matching works as expected
4. Check that teams and integrations are properly configured

### Troubleshooting YAML Issues

#### **YAML Parsing Errors**
If you get YAML parsing errors, check for:

1. **Incorrect Multi-Condition Rule Indentation**
   ```yaml
   # ❌ WRONG (extra dashes cause parsing errors)
   MULTI_MultiConditionRules:
   - AssetType: CLOUD
     - ProviderAccountId:  # ← Extra dash here breaks YAML
       - "uuid-here"
   
   # ✅ CORRECT
   MULTI_MultiConditionRules:
   - AssetType: CLOUD
     ProviderAccountId:    # ← No dash, it's a key-value pair
       - "uuid-here"
   ```

2. **Missing AssetType in Multi-Condition Rules**
   ```yaml
   # ❌ WRONG (standalone ProviderAccountId without AssetType)
   MULTI_MultiConditionRules:
   - AssetType: CLOUD
     ProviderAccountId:
       - "uuid-1"
   ProviderAccountId:        # ← Missing AssetType parent
     - "uuid-2"
   
   # ✅ CORRECT
   MULTI_MultiConditionRules:
   - AssetType: CLOUD
     ProviderAccountId:
       - "uuid-1"
   - AssetType: CLOUD      # ← Each rule needs AssetType
     ProviderAccountId:
       - "uuid-2"
   ```

3. **Inconsistent Indentation**
   - Use spaces, not tabs
   - Maintain consistent indentation levels
   - Check for mixed indentation

#### **Validation Failures**
- **AssetType Rejection**: Ensure you're using values from the supported list above
- **ProviderAccountId Format**: Must always be a list, even for single values
- **Required Fields**: Applications need `AppName`, `ReleaseDefinitions`, `Responsable`
- **Email Validation**: Responsible person emails must be valid format

#### **Recent Fixes Applied (v4.8.3)**
- ✅ **Script Hanging**: Fixed teams loading path issue that caused hanging
- ✅ **API Compatibility**: Added graceful handling for ENVIRONMENT_CLOUD enum errors
- ✅ **User Creation**: Enhanced automatic user creation from Responsable field
- ✅ **Hang Prevention**: Added timeout protection for user fetching operations
- ✅ **YAML Structure**: Fixed multi-condition rule indentation issues
- ✅ **AssetType Support**: Added `CLOUD`, `WEB`, `FOSS`, `SAST` support  
- ✅ **Validation Sync**: Linter now matches Phoenix Security API requirements
- ✅ **Multi-Condition Rules**: Enhanced validation and error reporting

#### **Troubleshooting Common Issues**

**Script Hanging Issues:**
- ✅ **FIXED**: Teams folder path handling (leading slash issue)
- ✅ **FIXED**: User creation hanging during API calls
- ✅ **FIXED**: API compatibility errors causing crashes

**User Creation Problems:**
- Use `--create_users_from_responsable=true` for automatic user creation
- Check that Responsable emails are valid format
- Script now prevents duplicate user creation automatically

**API Compatibility Issues:**
- Script now handles ENVIRONMENT_CLOUD enum errors gracefully
- Continues execution despite API version mismatches
- Clear error messages explain compatibility issues

---

For additional support or questions about specific use cases, consult your Phoenix Security administrator or refer to the Phoenix Security documentation. 
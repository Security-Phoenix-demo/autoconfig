## Versioning

V 4.8.3
Date - 25 August 2025

### Recent Versions
- **V 4.8.2** (25 August 2025): Configurable Hives folder support for flexible organization
- **V 4.8.1** (16 August 2025): Configurable Teams folder support for flexible organization
- **V 4.5.2** (August 2025): Comprehensive execution reporting system
- **V 4.5.1** (August 2025): Configuration file organization with subfolder support

## 🎉 Recent Updates & Improvements

### **🆕 Version 4.8.1 Features** ⭐ **LATEST**
- ✅ **Configurable Teams Folder**: New `TeamsFolder` configuration option in `run-config.yaml` for flexible team organization
- ✅ **Configurable Hives System**: New `EnableHives` and `HivesFile` options for organizational hierarchy management
- ✅ **Multi-Client Support**: Support for different team folder structures and hives configurations per client
- ✅ **Optional Hives**: Ability to completely disable hives with `EnableHives: false` for simplified setups
- ✅ **Flexible File Locations**: Support for custom hives file paths including subfolder organization
- ✅ **Backward Compatibility**: Zero breaking changes - existing configurations work unchanged
- ✅ **Enhanced Loading**: Clear logging showing which folders/files are used and counts loaded
- ✅ **Improved Error Handling**: Graceful handling of missing files with helpful configuration hints

### **🆕 Version 4.5.2 Features**
- ✅ **Comprehensive Execution Reporting**: New detailed reporting system that tracks success/failure of all operations
- ✅ **Component Creation Tracking**: Individual component creation success/failure tracking with detailed error reporting
- ✅ **Application-Level Tag Support**: Full support for Tag_label processing at application level in Phoenix API
- ✅ **Enhanced Error Analysis**: Integration of both real-time tracking and historical error log analysis
- ✅ **Visual Progress Indicators**: Clear status indicators (✅ ⚠️ ❌) for easy identification of issues
- ✅ **Detailed Error Tracking**: Comprehensive error logging with context for troubleshooting
- ✅ **Performance Metrics**: Execution time tracking and success rate calculations
- ✅ **Operation Categorization**: Reports organized by teams, applications, deployments, environments, components, etc.

### **🆕 Version 4.5.1 Features**
- ✅ **Subfolder Support**: `run-config.yaml` now supports subfolder paths like `/mimecast/config.yaml` for better organization
- ✅ **Enhanced Path Resolution**: Improved configuration file discovery and validation
- ✅ **Multi-Client Support**: Organize configurations by client, environment, or team in subfolders
- ✅ **Backward Compatibility**: All existing configurations continue to work without changes

### **📋 Documentation**
- **[YAML Configuration Guide](YAML_CONFIGURATION_GUIDE.md)** - Comprehensive 500+ line guide with examples, validation, and troubleshooting
- **[YAML Quick Reference](YAML_QUICK_REFERENCE.md)** - Concise reference card for quick lookups during configuration
- **[Release Notes](RELEASE_NOTES.md)** - Detailed information about version 4.5.2 reporting features and 4.5.1 subfolder support

### **🔧 Recent Critical Fixes**
- ✅ **Application Tag Processing**: Fixed missing Tag_label support in application creation API calls
- ✅ **Component Integration Errors**: Added automatic retry mechanism for "Integration not found" errors
- ✅ **RiskFactor Tag Parsing**: Fixed multi-colon tag processing (e.g., RiskFactor:authenticated_access: false)
- ✅ **YAML Syntax Validation**: Enhanced mimecast_translator.py with proper indentation handling
- ✅ **Linter Schema Updates**: Added Tag_label support to application and component validation schemas
- ✅ **AssetType Validation**: Added missing `CLOUD`, `WEB`, `FOSS`, `SAST` support (synchronized with Phoenix Security API)

### **🛠️ Validation & Linter**
To validate your YAML configuration:
```bash
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

# Introduction

This [repo](xxx) provides a method of getting data from your organization's repos, teams, and domains to [Phoenix](https://demo2.appsecphx.io/) using
** [Python] (https://github.com/Security-Phoenix-demo/autoconfig/tree/main/Python%20script) 
** [Powershell] (https://github.com/Security-Phoenix-demo/autoconfig/tree/main/Power%20Shell%20script)

The following API credentials are required:

1. Phoenix  API Client ID and Client Secret.

## How to run

For Powershell, use [this.](https://github.com/Security-Phoenix-demo/autoconfig/tree/main/Power%20Shell%20script)

For Python, there is [legacy mode](https://github.com/Security-Phoenix-demo/autoconfig-priv/blob/main/README.md#basic-usage) and [new mode.](https://github.com/Security-Phoenix-demo/autoconfig-priv/blob/main/README.md#using-run-phxpy-new-version)



## Customization

The API and @company.com present in various parts of the script for override should be changed with your company name and domain. 
this parameters is parametrizable 

## Schedule

The service support flags run key functions to help avoid exceeding the 60 min cron limit.

- teams - Creates new teams, assigns members to teams, removes members from teams they should no longer have access to (Defaults to true)
- code - Creates applications (subdomains) and the associated components (repos) and rules (Defaults to true)
- cloud - Create Cloud Environments and services (Subdomains) along with associated rules (Defaults to false)

As the job typically takes between 50 and 59 minutes to complete (depending on the size of your org, it might take less), it is only run once a day to prevent blocking other pipelines using the release agent.

## Obtaining Phoenix API Credentials

**Note:** This is for testing, hence the use of separate credentials; for BAU, the Credentials Called "API" in Phoenix are used.

When you run Run.ps1 locally, it will prompt you for the

- ClientID
- Client Secret

**Never check in to code the credentials.**

1. Logon to [Phoenix] *your Phoenix Domain using SSO/Direct auth
2. Click Settings.
3. Click Organization.
4. Click API Access.
5. Click Create API credential.
6. Take a copy of the key and keep it secret.

## API endpoint

The Phoenix-based endpoint for API requests is: [https://api.YOURDOMAIN.securityphoenix.cloud](https://api.YOURDOMAIN.securityphoenix.cloud)

## Supported AssetType Values

The following AssetType values are supported and validated by the Phoenix Security API:

| AssetType | Purpose | Use Cases |
|-----------|---------|-----------|
| `REPOSITORY` | Source code repositories | GitHub repos, GitLab repos |
| `SOURCE_CODE` | Source code assets | Code files, source artifacts |
| `BUILD` | Build artifacts | JAR files, executables |
| `WEBSITE_API` | Web applications & APIs | REST APIs, web services |
| `CONTAINER` | Container images/instances | Docker, Kubernetes pods |
| `INFRA` | Infrastructure components | Servers, networks |
| `CLOUD` | Cloud resources | AWS/Azure/GCP services |
| `WEB` | Web assets | Websites, web applications |
| `FOSS` | Open source components | Third-party libraries |
| `SAST` | Static analysis assets | Security scan results |

**Note**: These values are case-sensitive and must be used exactly as shown. For detailed usage examples, see the [YAML Configuration Guide](YAML_CONFIGURATION_GUIDE.md).

## Versioning

V 4.5.2
Date - January 2025

### Recent Versions
- **V 4.5.2** (January 2025): Comprehensive execution reporting system
- **V 4.5.1** (August 2025): Configuration file organization with subfolder support  
- **V 4.3** (March 2025): Tag logic overhaul and repository path optimization

# Quick Start Guide

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Security-Phoenix-demo/autoconfig.git
cd autoconfig/Python\ script
```

2. Install dependencies:
```bash
pip install -r providers/requirements.txt
```

## Basic Usage

The script can be run with different combinations of flags to perform specific operations:

```bash
python run.py <client_id> <client_secret> <teams> <code> <cloud> <deployment> <autolink> <autocreate_teams> <create_components> <api_domain>
```

### Minimal Example

```bash
python run.py your_client_id your_client_secret True False False False False False False api.yourdomain.securityphoenix.cloud
```

## Using run-phx.py (New Version)

The new version of the script (`run-phx.py`) uses a more modern argument parser with named parameters for better clarity and usability. 

### **📊 Comprehensive Execution Reporting** ⭐ **NEW IN v4.5.2**

The script now includes automatic execution reporting that provides complete visibility into the configuration process. After each run, you'll receive a detailed report showing:

- **📅 Execution Summary**: Start time, duration, and configuration files processed
- **📊 Success Rates**: Visual indicators (✅ ⚠️ ❌) with percentage success rates for each category
- **📋 Detailed Breakdown**: Success/failure details for teams, applications, deployments, environments, etc.
- **❌ Error Analysis**: Comprehensive error tracking with context for quick troubleshooting
- **🎯 Overall Metrics**: Total operations performed and overall success rate

**Example Report Output:**
```
================================================================================
PHOENIX AUTOCONFIG EXECUTION REPORT
================================================================================

📅 Execution Time: 2024-01-15 10:30:00 - 2024-01-15 10:32:45
⏱️  Total Duration: 0:02:45

📂 Configuration Files Processed: 2
   • mimecast-core-structure.yaml
   • core-structure.yaml

🔧 Actions Performed: Teams, Cloud, Code, Deployment

📊 OPERATION SUMMARY
--------------------------------------------------
✅ TEAMS: 5/5 successful (100.0%)
✅ APPLICATIONS: 12/12 successful (100.0%)
✅ COMPONENTS: 18/20 successful (90.0%)
⚠️ ENVIRONMENTS: 8/10 successful (80.0%)
❌ DEPLOYMENTS: 3/8 successful (37.5%)

🎯 OVERALL SUCCESS RATE: 46/55 (83.6%)

❌ COMPREHENSIVE ERROR SUMMARY (7 total)
--------------------------------------------------

COMPONENTS Errors (2):
  1. create_component - mimecast-admin-console -> Mimecast Administration Console
     Error: Integration not found, retried successfully without ticketing
  2. create_component - dmarc-customer-service -> DMARC Customer Service  
     Error: Failed to create component even without ticketing: 400 Client Error
     Time: 2024-01-15 10:31:45
```

This reporting feature is **automatically enabled** for all script executions and requires no additional configuration.

### Basic Command Structure

```bash
python run-phx.py <client_id> <client_secret> [options]
```

### Required Arguments

1. `client_id` (positional, required)
   - Your Phoenix API Client ID
   - Must be provided as the first argument

2. `client_secret` (positional, required)
   - Your Phoenix API Client Secret
   - Must be provided as the second argument
   - Example: `your-secret-key`

### Optional Arguments

| Parameter | Description | Default | Example |
|-----------|-------------|---------|----------|
| `--api_domain` | Override the default Phoenix API domain | https://api.demo.appsecphx.io | `--api_domain=https://api.custom.appsecphx.io` |
| `--action_teams` | Create and manage teams | false | `--action_teams=true` |
| `--action_create_users_from_teams` | Automatically create users from team configuration | false | `--action_create_users_from_teams=true` |
| `--create_users_from_responsable` | **NEW**: Auto-create users from Responsable field | **true** | `--create_users_from_responsable=true` |
| `--action_code` | Create applications and components | false | `--action_code=true` |
| `--action_cloud` | Create environments and services | false | `--action_cloud=true` |
| `--action_deployment` | Create deployments | false | `--action_deployment=true` |
| `--action_autolink_deploymentset` | Auto-create deployments based on name similarity | false | `--action_autolink_deploymentset=true` |
| `--action_autocreate_teams_from_pteam` | Create teams from pteam tags | false | `--action_autocreate_teams_from_pteam=true` |
| `--action_create_components_from_assets` | Create components from discovered assets (name-based) | false | `--action_create_components_from_assets=true` |
| `--action_create_components_from_assets_tag` | Create components from discovered assets (tag-based) | false | `--action_create_components_from_assets_tag=true` |
| `--type` | Asset type to process (all, cloud, code, infrastructure, web) | none | `--type=infrastructure` |
| `--tag-base` | Base tag key for tag-based grouping | none | `--tag-base=team-name` |
| `--tag-alternative` | Alternative tag keys (comma-separated) | none | `--tag-alternative=pteam,owner` |
| `--create_automatically_groups` | Create automatically groups - full Phoenix structure (environments, services, applications, components) | no | `--create_automatically_groups=yes` |
| `--silent` | Skip confirmation prompts for automated runs | false | `--silent` |
| `--verbose` | Enable detailed debug output for troubleshooting | false | `--verbose` |
| `--clear-logs` | Clear all error logs and exit | false | `--clear-logs` |

### Team Configuration and User Management

The script supports two types of automatic user creation:

1. **NEW in v4.8.3**: From `Responsable` field in applications/environments (enabled by default)
2. From team configuration files with specific roles

### Automatic User Creation from Responsable Field 🆕

**NEW FEATURE**: The script automatically creates users from the `Responsable` field in your YAML configuration files.

#### Configuration Options:

**Command Line (Recommended):**
```bash
# Enable user creation (default)
--create_users_from_responsable=true

# Disable user creation  
--create_users_from_responsable=false
```

**Configuration File (Alternative):**
```yaml
# In your core-structure.yaml file
CreateUsersForApplications: true
```

#### Features:
- ✅ **Enabled by default** - No configuration needed
- ✅ **Hang prevention** - 30-second timeout protection
- ✅ **Duplicate prevention** - Smart checking against existing users
- ✅ **Progress tracking** - Shows processing status for each user
- ✅ **Error resilience** - Continues even if some users fail
- ✅ **Efficient processing** - Only processes unique emails

#### Example Usage:
```bash
# Basic usage (user creation enabled by default)
python run-phx.py CLIENT_ID CLIENT_SECRET --action_code=true

# Explicitly enable user creation
python run-phx.py CLIENT_ID CLIENT_SECRET --action_code=true --create_users_from_responsable=true

# Disable user creation
python run-phx.py CLIENT_ID CLIENT_SECRET --action_code=true --create_users_from_responsable=false
```

### User Creation from Team Configuration

The script also supports automatic user creation from team configuration files. Users can be created with specific roles based on their `EmployeeRole` in the team configuration.

#### Team Member Configuration Format

Team configuration files should be placed in the `Resources/Teams` directory with the following format:

```yaml
TeamName: "Example Team"
TeamMembers:
  - Name: "John Smith"  # Required, must have first and last name
    EmailAddress: "john.smith@company.com"  # Required
    EmployeeRole: "Engineering User"  # Optional, maps to Phoenix roles
```

#### Supported Employee Roles

The following `EmployeeRole` values are mapped to Phoenix roles:

| Team Config Role | Phoenix Role |
|-----------------|--------------|
| Security Champion | SECURITY_CHAMPION |
| Engineering User | ENGINEERING_USER |
| Application Admin | APPLICATION_ADMIN |
| *(any other value)* | ORG_USER |

#### Example: Creating Users from Team Configuration

```bash
# Create teams and users
python run-phx.py your_client_id your_client_secret \
  --action_teams=true \
  --action_create_users_from_teams=true

# Verify user creation first
python run-phx.py your_client_id your_client_secret \
  --action_teams=true \
  --action_create_users_from_teams=true \
```

#### User Creation Process

When `--action_create_users_from_teams` is enabled:
1. Validates team member data (name format, required fields)
2. Checks for existing users to avoid duplicates
3. Creates users with appropriate roles based on `EmployeeRole`
4. Automatically adds users to their respective teams
5. Logs all operations and any errors

#### Requirements for User Creation

1. Team member must have:
   - Full name (first and last name) in the `Name` field
   - Valid email address in the `EmailAddress` field
2. Optional `EmployeeRole` field determines Phoenix role
3. Team configuration must be in the correct YAML format

#### Error Handling

The script will:
- Skip users with missing or invalid names
- Skip users that already exist
- Log detailed error messages for troubleshooting
- Continue processing other users if one fails

### Log Management

**Clear Error Logs**
```bash
# Clear all error logs and exit
python run-phx.py --clear-logs
```
This command clears all error logs (errors.log and other *.log files) and exits immediately. Useful for:
- Starting with clean logs for debugging
- Maintenance operations
- Automated script cleanup

### Common Usage Patterns

1. **Complete Setup**
```bash
python run-phx.py your_client_id your_client_secret \
  --action_teams=true \
  --action_code=true \
  --action_cloud=true \
  --action_deployment=true
```
This will perform a full setup including teams, applications, environments, and deployments.

2. **Team Management Only**
```bash
python run-phx.py your_client_id your_client_secret --action_teams=true
```
This will only handle team creation and management.

3. **Environment and Service Setup**
```bash
python run-phx.py your_client_id your_client_secret \
  --action_cloud=true \
  --action_create_components_from_assets=true
```
This will create environments and services, and automatically discover and create components from assets.

4. **Custom API Domain**
```bash
python run-phx.py your_client_id your_client_secret \
  --api_domain=https://api.custom.appsecphx.io \
  --action_code=true
```
This will use a custom API domain for the operations.

### Action Combinations

Different actions can be combined based on your needs. Here are some useful combinations:

1. **Initial Setup**
```bash
python run-phx.py your_client_id your_client_secret \
  --action_teams=true \
  --action_code=true \
  --action_cloud=true
```

2. **Regular Update**
```bash
python run-phx.py your_client_id your_client_secret \
  --action_teams=true \
  --action_code=true \
  --action_cloud=true \
  --action_deployment=true
```

3. **Asset Discovery and Component Creation**
```bash
python run-phx.py your_client_id your_client_secret \
  --action_cloud=true \
  --action_create_components_from_assets=true \
  --action_autolink_deploymentset=true
```

4. **Full Asset Creation Mode** ⭐ **NEW FEATURE**
```bash
# Create complete Phoenix structure with preview and confirmation
python run-phx.py your_client_id your_client_secret \
  --action_create_components_from_assets=true \
  --type=infrastructure \
  --create_automatically_groups=yes

# Automated mode for CI/CD pipelines
python run-phx.py your_client_id your_client_secret \
  --action_create_components_from_assets=true \
  --type=cloud \
  --create_automatically_groups=yes \
  --silent
```

5. **Team and Deployment Management**
```bash
python run-phx.py your_client_id your_client_secret \
  --action_teams=true \
  --action_deployment=true \
  --action_autocreate_teams_from_pteam=true
```

### Best Practices

1. **Incremental Updates**
   - Run specific actions rather than all at once
   - Makes troubleshooting easier
   ```bash
   python run-phx.py your_client_id your_client_secret --action_teams=true
   python run-phx.py your_client_id your_client_secret --action_code=true
   ```

2. **Regular Maintenance**
   - Schedule regular runs for team updates
   - Keep deployments in sync
   ```bash
   # Example daily update
   python run-phx.py your_client_id your_client_secret \
     --action_teams=true \
     --action_deployment=true
   ```

3. **Error Handling**
   - Monitor the error log file
   - Check specific action results

### Troubleshooting

The new reporting feature provides comprehensive error tracking and performance metrics to help identify and resolve issues quickly.

1. **Using the Execution Report**
   ```bash
   # Run with verbose output for detailed debugging
   python run-phx.py your_client_id your_client_secret \
     --action_teams=true \
     --verbose
   ```
   
   The execution report will show:
   - Overall success rates for each operation category
   - Detailed error messages with context
   - Performance metrics and timing information
   - Specific items that failed with reasons

2. **API Connection Issues**
   ```bash
   # Test API connection
   python run-phx.py your_client_id your_client_secret \
     --api_domain=https://api.custom.appsecphx.io
   ```

3. **Team Creation Issues**
   ```bash
   # Verify team configuration with detailed reporting
   python run-phx.py your_client_id your_client_secret \
     --action_teams=true \
     --verbose
   ```

4. **Deployment Problems**
   ```bash
   # Check deployment configuration with comprehensive reporting
   python run-phx.py your_client_id your_client_secret \
     --action_deployment=true \
     --verbose
   ```

5. **Interpreting Success Rates**
   - ✅ **80-100%**: Excellent - Most operations completed successfully
   - ⚠️ **50-79%**: Warning - Some issues that may need attention
   - ❌ **<50%**: Critical - Significant problems requiring investigation

# Examples and Detailed Usage

## Command Line Usage

### New Format (Recommended)
Using `run-phx.py` with named arguments:

```bash
# Basic structure
python run-phx.py <client_id> <client_secret> [options]

# Complete example with all options
python run-phx.py your_client_id your_client_secret \
  --api_domain=https://api.demo.appsecphx.io \
  --action_teams=true \
  --action_code=true \
  --action_cloud=true \
  --action_deployment=true \
  --action_autolink_deploymentset=true \
  --action_autocreate_teams_from_pteam=true \
  --action_create_components_from_assets=true
```

### Common Use Cases

1. **Team Management Only**
```bash
python run-phx.py your_client_id your_client_secret --action_teams=true
```

2. **Full Application Setup**
```bash
python run-phx.py your_client_id your_client_secret \
  --action_code=true \
  --action_cloud=true \
  --action_deployment=true
```

## Configuration Examples

### 1. Environment Configuration

#### Basic Environment
```yaml
Environment Groups:
  - Name: Production
    Type: CLOUD
    Status: Production
    Responsable: ops@company.com
    Tier: 1
    TeamName: DevOps
```

#### Environment with Services
```yaml
Environment Groups:
  - Name: Production
    Type: CLOUD
    Status: Production
    Responsable: ops@company.com
    Tier: 1
    TeamName: DevOps
    Services:
      - Service: WebAPI
        Type: Cloud
        Tier: 1
        TeamName: APITeam
        SearchName: web-api-*
        Tag: environment:production
```

#### Environment with Multiple Services and Rules
```yaml
Environment Groups:
  - Name: Production
    Type: CLOUD
    Status: Production
    Responsable: ops@company.com
    Services:
      - Service: DatabaseService
        Type: Cloud
        Tier: 1
        TeamName: DBTeam
        MultiConditionRules:
          - RepositoryName: company/db-repo
            SearchName: db-*
            Tag: type:database
          - RepositoryName: company/cache-repo
            SearchName: cache-*
            Tag: type:cache
      - Service: WebService
        Type: Cloud
        Tier: 2
        TeamName: WebTeam
        SearchName: web-*
        Tag: type:web
```

### 2. Application Configuration

#### Basic Application
```yaml
DeploymentGroups:
  - AppName: MyWebApp
    TeamNames:
      - WebTeam
    Responsable: lead@company.com
    Tier: 2
```

#### Application with Components
```yaml
DeploymentGroups:
  - AppName: MyWebApp
    TeamNames:
      - WebTeam
      - APITeam
    Responsable: lead@company.com
    Tier: 2
    Components:
      - ComponentName: Frontend
        TeamNames:
          - WebTeam
        RepositoryName: company/frontend-repo
        Type: Web
      - ComponentName: Backend
        TeamNames:
          - APITeam
        RepositoryName: company/backend-repo
        Type: API
```

#### Complex Application with Rules
```yaml
DeploymentGroups:
  - AppName: EnterpriseApp
    TeamNames:
      - CoreTeam
    Responsable: architect@company.com
    Tier: 1
    Components:
      - ComponentName: APIGateway
        TeamNames:
          - GatewayTeam
        MultiConditionRule:
          RepositoryName: company/gateway
          SearchName: gateway-*
          AssetType: CONTAINER
        MULTI_MultiConditionRules:
          - RepositoryName: company/auth
            SearchName: auth-*
            Tag: component:auth
          - RepositoryName: company/routing
            SearchName: routing-*
            Tag: component:routing
```

### 3. Team Configuration

#### Basic Team
```yaml
TeamName: DevTeam
AzureDevopsAreaPath: company\DevTeam
TeamMembers:
  - Name: John Smith
    EmailAddress: john.smith@company.com
    EmployeeType: Employee
```

#### Team with Multiple Members and Roles
```yaml
TeamName: SecurityTeam
AzureDevopsAreaPath: company\SecurityTeam
RecreateTeamAssociations: True
TeamMembers:
  - Name: Alice Johnson
    EmailAddress: alice.j@company.com
    EmployeeType: Employee
    Level: Lead
  - Name: Bob Wilson
    EmailAddress: bob.w@company.com
    EmployeeType: Contractor
    Level: Senior
```

### 4. Integration Examples

#### Ticketing Integration
```yaml
Environment Groups:
  - Name: Production
    Type: CLOUD
    Ticketing:
      - TIntegrationName: JIRA
        Backlog: PROD-BACKLOG
    Messaging:
      - MIntegrationName: SLACK
        Channel: prod-alerts
```

#### Cloud Asset Rules
```yaml
Services:
  - Service: CloudInfra
    Type: Cloud
    MultiConditionRules:
      - AssetType: CLOUD
        ProviderAccountId: ["123456789"]
        ResourceGroup: ["prod-rg"]
        Tag: environment:production
```

## Advanced Usage Examples

### 1. Deployment Configuration

#### Simple Deployment
```yaml
DeploymentGroups:
  - AppName: WebApp
    Deployment_set: prod-web
    
Environment Groups:
  - Name: Production
    Services:
      - Service: WebService
        Deployment_set: prod-web
```

#### Tag-Based Deployment
```yaml
DeploymentGroups:
  - AppName: MicroService
    Deployment_set: service-tag

Environment Groups:
  - Name: Production
    Services:
      - Service: ServiceInstance
        Deployment_tag: service-tag
```

### 2. Asset Management

#### Component Creation from Assets
```yaml
Components:
  - ComponentName: DatabaseCluster
    AssetType: CLOUD
    Tags:
      - "type:database"
      - "env:prod"
    ProviderAccountId: 
      - "123456789"
```

### 3. Security Integration

#### CIDR-Based Rules
```yaml
Services:
  - Service: NetworkService
    Type: Infra
    Cidr: 10.0.0.0/16
    MultiConditionRules:
      - Cidr: 172.16.0.0/12
        Tag: network:internal
```

## Configuration Files

### Core Structure (core-structure.yaml)

The main configuration file that defines your organization's structure:

```yaml
DeploymentGroups:
  - AppName: MyApp
    TeamNames:
      - DevTeam
    Responsable: admin@company.com
    Tier: 3
    Components:
      - ComponentName: Frontend
        TeamNames:
          - FrontendTeam
        RepositoryName: company/frontend-repo

Environment Groups:
  - Name: Production
    Type: CLOUD
    Tier: 1
    Responsable: ops@company.com
    Services:
      - Service: WebService
        Type: Cloud
        TeamName: WebTeam
```

### Teams Configuration (Teams/*.yaml)

Individual team configurations in the teams directory. The location of the teams folder can be configured in `run-config.yaml`:

#### **Configurable Teams Folder** 📁 **NEW in v4.8.1**

You can now specify which folder contains your team configuration files:

```yaml
# In run-config.yaml
ConfigFiles:
  - /mimecast/phoenix_autoconfig_infra_alt.yaml

# Folder containing team configuration files (relative to Resources folder)
TeamsFolder: Teams_bv  # Default: Teams

## Config for GitHub repos that will serve the config
GitHubRepositories:
  # - https://github.com/example/config-repo
```

#### **Usage Examples:**

**Default Configuration (Backward Compatible):**
```yaml
TeamsFolder: Teams  # Uses existing Teams folder
```

**Custom Teams Folder:**
```yaml
TeamsFolder: Teams_bv        # For specific business unit
TeamsFolder: Teams_enterprise # For enterprise clients  
TeamsFolder: Teams_staging   # For staging environment
```

#### **Team File Format:**

Individual team configurations in your specified teams directory:

```yaml
TeamName: DevTeam
AzureDevopsAreaPath: company\DevTeam
TeamMembers:
  - Name: John Doe
    EmailAddress: john.doe@company.com
    EmployeeType: Employee
```

#### **Benefits:**
- ✅ **Multi-Client Support**: Different team structures per client or business unit
- ✅ **Organizational Flexibility**: Easy migration between team structures
- ✅ **Zero Breaking Changes**: Existing configurations continue working unchanged
- ✅ **Clear Logging**: Shows which teams folder is used and how many teams were loaded

### Hives Configuration (hives.yaml)

#### **Configurable Hives System** 🏢 **NEW in v4.8.1**

Hives define organizational hierarchy and leadership structure. The hives system is now fully configurable:

```yaml
# In run-config.yaml
ConfigFiles:
  - /mimecast/phoenix_autoconfig_infra_alt.yaml

# Folder containing team configuration files (relative to Resources folder)
TeamsFolder: Teams_bv  # Default: Teams

# Hives configuration (organizational hierarchy and leadership)
EnableHives: true  # Set to false to disable hives completely
HivesFile: bv/bv-hives.yaml  # Default: hives.yaml (relative to Resources folder)
```

#### **Configuration Options:**

**Enable/Disable Hives:**
```yaml
EnableHives: false  # Completely disables hives functionality
```

**Custom Hives File Location:**
```yaml
EnableHives: true
HivesFile: client-specific/hives.yaml  # Custom file location
HivesFile: environments/prod-hives.yaml  # Environment-specific
HivesFile: bv/bv-hives.yaml  # Business unit specific
```

#### **Hives File Format:**

Define team hierarchies and leadership:

```yaml
CustomEmail: false
CompanyEmailDomain: company.com
Hives:
  - Name: Development
    Teams:
      - Name: DevTeam
        Lead: jane.smith
        Product: john.doe
```

#### **Benefits:**
- ✅ **Optional Hierarchy**: Completely disable hives for simplified team-only setups
- ✅ **Flexible Locations**: Support for subfolder organization and custom file names
- ✅ **Multi-Client Support**: Different hives files per client or environment
- ✅ **Graceful Fallback**: Continues operation even when hives file is missing
- ✅ **Independent Operation**: Teams work perfectly whether hives are enabled or disabled

## Advanced Configuration

### Service Configuration Options

1. **Basic Service**:
```yaml
Services:
  - Service: MyService
    Type: Cloud
    Tier: 3
    TeamName: DevTeam
```

2. **Service with Tags**:
```yaml
Services:
  - Service: MyService
    Type: Cloud
    Tag: environment:production
    SearchName: my-service-*
```

3. **Service with Multiple Rules**:
```yaml
Services:
  - Service: MyService
    MultiConditionRules:
      - RepositoryName: repo1
        SearchName: service1
      - RepositoryName: repo2
        SearchName: service2
```

### Component Configuration Options

1. **Basic Component**:
```yaml
Components:
  - ComponentName: MyComponent
    TeamNames:
      - DevTeam
    RepositoryName: company/repo
```

2. **Component with Multiple Rules**:
```yaml
Components:
  - ComponentName: MyComponent
    MultiConditionRule:
      RepositoryName: repo1
      SearchName: component1
    MULTI_MultiConditionRules:
      - RepositoryName: repo2
        SearchName: component2
```

## Environment Variables

Optional environment variables for configuration:

```bash
export PHOENIX_DEBUG=True           # Enable debug logging
export PHOENIX_MAX_RETRIES=5       # Set max retry attempts
export PHOENIX_BASE_DELAY=3        # Set base delay for retries
```

## Script Modes

### 1. Team Management Mode
```bash
python run.py client_id client_secret True false false false false false false api_domain
```
- Creates and updates teams
- Assigns members to teams
- Updates team permissions

### 2. Code Management Mode
```bash
python run.py client_id client_secret false True false false false false false api_domain
```
- Creates applications and components
- Sets up repository associations
- Configures code-related rules

### 3. Cloud Infrastructure Mode
```bash
python run.py client_id client_secret false false True false false false false api_domain
```
- Sets up cloud environments
- Creates service definitions
- Configures cloud asset rules

### 4. Deployment Management Mode
```bash
python run.py client_id client_secret false false false True false false false api_domain
```
- Creates deployment associations
- Links applications to services
- Sets up deployment rules

## Performance Optimization

### Batch Operations
For large deployments, use batch operations:
```yaml
batch_size: 10           # Number of operations per batch
delay_between_batches: 1 # Delay in seconds between batches
```

### Retry Configuration
Customize retry behavior:
```python
max_retries = 5      # Maximum retry attempts
base_delay = 3       # Base delay between retries
max_delay = 60       # Maximum delay for exponential backoff
```

## Monitoring and Maintenance

### Health Checks
Monitor script health:
1. Check `errors.log` for failures
2. Monitor API response times
3. Track resource creation success rates

### Regular Maintenance
Maintain script health:
1. Rotate log files weekly
2. Clean up old error logs
3. Update API credentials regularly
4. Review and update team configurations

## Security Considerations

1. **API Credentials**:
   - Store credentials securely
   - Rotate credentials regularly
   - Use environment variables for sensitive data

2. **Access Control**:
   - Review team permissions regularly
   - Audit team membership changes
   - Monitor service access patterns

3. **Data Protection**:
   - Validate input data
   - Sanitize configuration files
   - Encrypt sensitive information

## Troubleshooting Guide

### Common Issues

1. **Service Creation Fails**
```
Issue: 404 Not Found after service creation
Solution: Increase verification retries and delays
```

2. **Rule Creation Fails**
```
Issue: 400 Bad Request for rule creation
Solution: Check field names and case sensitivity
```

3. **Team Assignment Fails**
```
Issue: User cannot be assigned to team
Solution: Verify user has logged in to Phoenix portal
```

### Debug Steps

1. Enable debug mode:
```python
DEBUG = True
```

2. Check API responses:
```python
print(f"Response content: {response.content}")
```

3. Verify configurations:
```bash
python run.py --validate-config
```

## Integration Examples

### CI/CD Pipeline Integration

```yaml
# GitHub Actions Example
name: Phoenix Configuration
on:
  push:
    branches: [ main ]

jobs:
  configure:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Configuration
        run: |
          python run.py ${{ secrets.PHOENIX_CLIENT_ID }} \
                       ${{ secrets.PHOENIX_CLIENT_SECRET }} \
                       true false false false false false false \
                       ${{ secrets.PHOENIX_API_DOMAIN }}
```

### Automation Scripts

```bash
#!/bin/bash
# Daily update script
python run.py $CLIENT_ID $CLIENT_SECRET true true true true false false false $API_DOMAIN
```

## Best Practices

1. **Configuration Management**:
   - Use version control for configurations
   - Document all configuration changes
   - Validate configurations before deployment

2. **Error Handling**:
   - Implement proper error logging
   - Use retries with exponential backoff
   - Handle API rate limits

3. **Performance**:
   - Use batch operations when possible
   - Implement caching for frequent operations
   - Monitor execution times

4. **Maintenance**:
   - Regular configuration reviews
   - Periodic credential rotation
   - Log file management

# Introduction

This [repo](xxx) provides a method of getting data from your organization's repos, teams, and domains to [Phoenix](https://demo2.appsecphx.io/) using
** [Python] (https://github.com/Security-Phoenix-demo/autoconfig/tree/main/Python%20script) 
** [Powershell] (https://github.com/Security-Phoenix-demo/autoconfig/tree/main/Power%20Shell%20script)

The following API credentials are required:

1. Phoenix  API Client ID and Client Secret.

## Customization

The API and @company.com present in various parts of the script for override should be changed with your company name and domain. 
this parameters is parametrizable 

## Schedule

The service support flags run key functions to help avoid exceeding the 60 min cron limit.

- teams - Creates new teams, assigns members to teams, removes members from teams they should no longer have access to (Defaults to true)
- code - Creates applications (subdomains) and the associated components (repos) and rules (Defaults to true)
- cloud - Create Cloud Environments and services (Subdomains) along with associated rules (Defaults to false)

As the job typically takes between 50 and 59 minutes to complete (depending on the size of your org, it might take less), it is only run once a day to prevent blocking other pipelines using the release agent.

## Obtaining Phoenix API Credentials

**Note:** This is for testing, hence the use of separate credentials; for BAU, the Credentials Called "API" in Phoenix are used.

When you run Run.ps1 locally, it will prompt you for the

- ClientID
- Client Secret

**Never check in to code the credentials.**

1. Logon to [Phoenix] *your Phoenix Domain using SSO/Direct auth
2. Click Settings.
3. Click Organization.
4. Click API Access.
5. Click Create API credential.
6. Take a copy of the key and keep it secret.

## API endpoint

The Phoenix-based endpoint for API requests is: [https://api.YOURDOMAIN.securityphoenix.cloud](https://api.YOURDOMAIN.securityphoenix.cloud)

## Obtaining an Access token

Using the Phoenix API Credentials you must obtain an Access token that is only valid for a limited amount of time to invoke the Phoenix API's.

This is done via making an HTTP GET call to [v1/auth/access_token](https://YOURDOMAIN.securityphoenix.cloud/v1/auth/access_token).

See function `GetAuthToken`.

The response will contain the access token.

The request to the API will contain a **Authorization** header with a basic base64 encoded byte array.

The byte array is "ClientId : clientSecret."

## Local Debugging

To make the sctipt work the core-structure.yaml, teams (individual teams like axalot and lima) and hives.yaml needs to be customized; don't use those as is

When running the code locally you will need to download `core-structure.yaml` and `hives.yaml` from Release data to a folder called `Resources`.

You will also need a copy of the `Teams` folder and its yaml 

## Local Testing (optional) - Powershell

The project uses Pester for testing. From a PowerShell command prompt, type: `invoke-pester`.

## Hives

A member of your org maybe responsible for one or more team teams. This is currently configured via the (hives.yaml) file.

## Teams

Teams are created by the entries within the team data structure

The teams have component association rules based on the tag pteam `pteam` tag to the API request to Phoenix.

Example `pteam:axelot`.

In case there is an issue with team associations, new flag is introduced to recreate the associations.
`RecreateTeamAssociations` is the team property, and when set to `True`, then the associations are recreated for that team.

Example configuration:

```
TeamName: SP_axelot20
AzureDevopsAreaPath: company\SP_axelot20
TeamWikiLocation: 
RecreateTeamAssociations: False
TeamMembers:
- Name: james terry
  EmailAddress: James.terry@company.com
  EmployeeType: Employee
  Level: M6 
```

The function [CreateTeams] Phoenix.ps1

## Team Assignment

Staff need to first login to the [Phoenix portal](https://YOURDOMAIN.securityphoenix.cloud/) using SSO before they can be assigned to a team.

The assignment should be run once a day (at least) 

The [Teams Yaml] Teams files are used as a source of truth of who belongs to which team.

The function [AssignUsersToTeam] Phoenix.ps1



## Hive Leaders

The [Hives Yaml] hives.yaml contains a list of leaders who are responsible for 1 or more teams.

The function [AssignUsersToTeam] Phoenix.ps1

## Coud subscriptions
in the main run.ps1, the subscriptions are assigned a criticality level and grouped from production to development, use the Azure or AWS subscription ID in this specification

The association of assets to subdomains is done via rules and looking up the pipeline tag against each deployed cloud asset / for AWS. Those can be cloud formation ID

The cloud environment and application can be created using either tag (Phoenix security canary tags) or specific networks

By grouping assets by subdomains (services) they can then be associated to the code that is using them.

## Environments

Environments in Phoenix are groupings of one or more cloud environments that can be logically grouped together.

The currently defined environments are:

- Production
- Staging
- Development

The function that create the environments is [CreateEnvironments] Phoenix.ps1

If you want to create users from Environment Group.Responsable field, set the variable in core-structure.yaml file

```
CreateUsersForApplications: True 
```

Example core-structure.yaml file

```
CreateUsersForApplications: True
Environment Groups:
  - Name: TST_Production
    Type: CLOUD
    Status: Production
    Responsable: ciso6.ttt@company.com
```

In the example above, user `ciso6.ttt@company.com` will be
created if not present in Phoenix. User first and last name are deduced from the first part of the email 

(`ciso6.ttt`) -> first name = ciso6; last name = ttt

If `Responsable` value is not valid email, user won't be created.

## Services

Services are the cloud resources that are used by different applications. These are typically grouped by the `subdomain` or a similar data grouping function  that uses the services.

A rule is created to use the Azure `pipeline` tag to associate it back to the `core-structure.yaml`.

This allows the resource allocation to remain up-to-date if the owner of the resource changes.

THe function is called [AddEnvironmentServices](Phoenix.ps1).

Mapping assets with services is done via:
1. RepositoryName, SearchName, AssetType, Tag, Cidr, Fqdn, Netbios, OsNames, Hostnames, ProviderAccountId, ProviderAccountName, ResourceGroup - creates individual component for each property 
Example config with all possible options listed:

~~~
Environment Groups:
  - Name: TST_Production
    Type: CLOUD
    Status: Production
    Responsable: frankadm@admin.com
    Tier: 2 #importance from 1-10
    TeamName: SP_lima20 #name of the team as it appears in hives and teams 
    Status: Production
    Services:
      - Service: stefan_service
        Type: Infra
        Tier: 8
        TeamName: SP_lima20
        SearchName: search_item
        AssetType: REPOSITORY #Look up possible values in the documentation
        Tag: tag1:tagv1
        Cidr: 10.1.1.0/24
        Fqdn: 
          - testfqdn
        Netbios: 
          - testbios
        OsNames: 
          - testosnames
        Hostnames: 
          - testhostnames
        ProviderAccountId: 
          - testaccountid
        ProviderAccountName: 
          - testaccountname
        ResourceGroup: 
          - testresourcegroup
~~~

2. MultiConditionRules - can combine repos, search, tags etc in one rule. Suppport for multiple multicondition rule is 
done through MULTI_MultiConditionRules key.

~~~

Environment Groups:
  - Name: TST_Production
    Type: CLOUD
    Status: Production
    Responsable: frankadm@admin.com
    Tier: 2 #importance from 1-10
    TeamName: SP_lima20 #name of the team as it appears in hives and teams 
    Status: Production
    Tag: 
    Team:
    Services:
      - Service: stefan_service
        Type: Infra
        Tier: 8
        TeamName: SP_lima20
        MultiConditionRule:
          AssetType: REPOSITORY #Look up possible values in the documentation
          RepositoryName: testrepo2
          SearchName: testsearch4
          Tag: key10:value10
          Cidr: 10.1.2.0/24 # multiple cidrs are not supported in MultiConditionRule
          Fqdn: 
            - testfqdn3
          Netbios: 
            - testbios3
          OsNames: 
            - testosnames3
          Hostnames: 
            - testhostnames3
          ProviderAccountId: 
            - testaccountid3
          ProviderAccountName: 
            - testaccountname3
          ResourceGroup: 
            - testresourcegroup3
        MULTI_MultiConditionRules:
          - AssetType: REPOSITORY #Look up possible values in the documentation
            RepositoryName: testrepo
            SearchName: testsearch2
            Tag: key1:value1
            Cidr: 10.1.1.0/24 # multiple cidrs are not supported in MultiConditionRule
            Fqdn: 
              - testfqdn
            Netbios: 
              - testbios
            OsNames: 
              - testosnames
            Hostnames: 
              - testhostnames
            ProviderAccountId: 
              - testaccountid
            ProviderAccountName: 
              - testaccountname
            ResourceGroup: 
              - testresourcegroup
          - AssetType: REPOSITORY #Look up possible values in the documentation
            RepositoryName: testrepo2
            SearchName: testsearch3
            Tag: key2:value2
            Cidr: 10.1.2.0/24 # multiple cidrs are not supported in MultiConditionRule
            Fqdn: 
              - testfqdn2
            Netbios: 
              - testbios2
            OsNames: 
              - testosnames2
            Hostnames: 
              - testhostnames2
            ProviderAccountId: 
              - testaccountid2
            ProviderAccountName: 
              - testaccountname2
            ResourceGroup: 
              - testresourcegroup2

~~~

3. Combining single rule with multicondition rule is also supported

~~~

Environment Groups:
  - Name: TST_Production
    Type: CLOUD
    Status: Production
    Responsable: frankadm@admin.com
    Tier: 2 #importance from 1-10
    TeamName: SP_lima20 #name of the team as it appears in hives and teams 
    Status: Production
    Services: 
      - Service: stefan_service9
        Type: Infra
        Tier: 8
        TeamName: SP_lima20
        SearchName: search_item
        AssetType: REPOSITORY #Look up possible values in the documentation
        Tag: tag1:tagv1
        Cidr: 10.1.1.0/24
        Fqdn: 
          - testfqdn
        Netbios: 
          - testbios
        OsNames: 
          - testosnames
        Hostnames: 
          - testhostnames
        ProviderAccountId: 
          - testaccountid
        ProviderAccountName: 
          - testaccountname
        ResourceGroup: 
          - testresourcegroup
        MultiConditionRule:
          AssetType: REPOSITORY #Look up possible values in the documentation
          RepositoryName: testrepo2
          SearchName: testsearch4
          Tag: key10:value10
          Cidr: 10.1.2.0/24 # multiple cidrs are not supported in MultiConditionRule
          Fqdn: 
            - testfqdn3
          Netbios: 
            - testbios3
          OsNames: 
            - testosnames3
          Hostnames: 
            - testhostnames3
          ProviderAccountId: 
            - testaccountid3
          ProviderAccountName: 
            - testaccountname3
          ResourceGroup: 
            - testresourcegroup3

~~~


The function for Component creation is [CreateRepositories](Phoenix.ps1).

## Deployed Applications

Deployed applications is the association of Applications to the Service.

This is based on the logic that Applications (subdomains) are the same as the Service(subdomain).

This association is achieved via `Deployment_set` element in Application and Service.
Application and Service that have the same value of `Deployment_set` element will be included in the deployment. 
Deployment is done by application and service names.

Example:

```
DeploymentGroups:
  - AppName: TST_TestApp10915 #name of the application
    Domain: Security
    SubDomain: Simplified Access Management
    Responsable: ciso4.test@company.com
```

In the example above, user `ciso4.test@company.com` will be
created if not present in Phoenix. User first and last name are deduced from the first part of the email 

(`ciso4.test`) -> first name = ciso4; last name = test

If `Responsable` value is not valid email, user won't be created.

## Components

Component can be create using one or more repositories, web apps, the guidance should be using one subdomain/component per team managing it. 
`core-structure.yaml` contains these definitions from which rules are generated.

in `core-structure.yaml` there is the specific declaration of application and components 

Tiering from release data is used to help highlight important repositories.

The tiering in Phoenix work 1 - 10 (10 being most important).

Team allocation is performed by added a `pteam` tag to the API request to Phoenix.

Example `pteam:axelot`.

Mapping assets with components is done via:
1. RepositoryName, SearchName, AssetType, Tags, Cidr, Fqdn, Netbios, OsNames, Hostnames, ProviderAccountId, ProviderAccountName, ResourceGroup - creates individual component for each property 
Example config with all possible options listed:

~~~
DeploymentGroups:
  - AppName: TST_TestApp109 #name of the application
    #Status: NotStarted #Status tags optionals (get added as tags)
    TeamNames: #names of the team responsble, can be a team responsible for the whole app or a specific component , this creates pteam tags
      - SP_lima20
      - SP_axelot20
    Domain: Security  #domain = component or application can be used to group by bysiness unit
    SubDomain: Simplified Access Management  #sub-domain = component or application can be used to group by busienss unit
    ReleaseDefinitions: []
    Responsable: frankadm@admin.com #owner of the application mandatory, needs to be one of the user already created in the phoenix security
    Tier: 4 #importance from 1-10 higher -> more critical , 5 default = neutral
    Components:
      - ComponentName: product106-repo10 #name of the component 
        Status: Production #Tag Optional
        Type: Release #Tag Optional
        TeamNames:  #names of the team as it appears in hives and teams
          - SP_axelot20
          - SP_lima20
        RepositoryName: Phoenix-ent-demo/Damn-Vulnerable-Source-Code  #name of the repo as appears in phoenix ,can be more than one
        SearchName: search_item
        AssetType: REPOSITORY #Look up possible values in the documentation
        Tags:
          - "123"
          - "1235"
        Cidr: 10.1.1.0/24
        Fqdn: 
          - testfqdn
        Netbios: 
          - testbios
        OsNames: 
          - testosnames
        Hostnames: 
          - testhostnames
        ProviderAccountId: 
          - testaccountid
        ProviderAccountName: 
          - testaccountname
        ResourceGroup: 
          - testresourcegroup
~~~

2. MultiConditionRules - can combine repos, search, tags etc in one rule. Suppport for multiple multicondition rule is 
done through MULTI_MultiConditionRules key.

~~~

DeploymentGroups:
  - AppName: TST_TestApp109 #name of the application
    #Status: NotStarted #Status tags optionals (get added as tags)
    TeamNames: #names of the team responsble, can be a team responsible for the whole app or a specific component , this creates pteam tags
      - SP_lima20
      - SP_axelot20
    Domain: Security  #domain = component or application can be used to group by bysiness unit
    SubDomain: Simplified Access Management  #sub-domain = component or application can be used to group by busienss unit
    ReleaseDefinitions: []
    Responsable: frankadm@admin.com #owner of the application mandatory, needs to be one of the user already created in the phoenix security
    Tier: 4 #importance from 1-10 higher -> more critical , 5 default = neutral
    Components:
      - ComponentName: product106-repo10 #name of the component 
        Status: Production #Tag Optional
        Type: Release #Tag Optional
        TeamNames:  #names of the team as it appears in hives and teams
          - SP_axelot20
          - SP_lima20
        MultiConditionRule:
          AssetType: REPOSITORY #Look up possible values in the documentation
          RepositoryName: testrepo5
          SearchName: testsearch25
          Tags:
            - "1235"
            - "12355"
          Cidr: 10.1.5.0/24
          Fqdn: 
            - testfqdn5
          Netbios: 
            - testbios5
          OsNames: 
            - testosnames5
          Hostnames: 
            - testhostnames5
          ProviderAccountId: 
            - testaccountid5
          ProviderAccountName: 
            - testaccountname5
          ResourceGroup: 
            - testresourcegroup5
        MULTI_MultiConditionRules:
          - AssetType: REPOSITORY #Look up possible values in the documentation
            RepositoryName: testrepo7
            SearchName: testsearch27
            Tags:
              - "1237"
              - "12357"
            Cidr: 10.1.7.0/24
            Fqdn: 
              - testfqdn7
            Netbios: 
              - testbios7
            OsNames: 
              - testosnames7
            Hostnames: 
              - testhostnames7
            ProviderAccountId: 
              - testaccountid7
            ProviderAccountName: 
              - testaccountname7
            ResourceGroup: 
              - testresourcegroup7
          - AssetType: REPOSITORY #Look up possible values in the documentation
            RepositoryName: testrepo2
            SearchName: testsearch3
            Tags:
              - "1234"
              - "12356"
            Cidr: 10.1.2.0/24
            Fqdn: 
              - testfqdn2
            Netbios: 
              - testbios2
            OsNames: 
              - testosnames2
            Hostnames: 
              - testhostnames2
            ProviderAccountId: 
              - testaccountid2
            ProviderAccountName: 
              - testaccountname2
            ResourceGroup: 
              - testresourcegroup2

~~~

3. Combining single rule with multicondition rules is also supported

~~~

DeploymentGroups:
  - AppName: TST_TestApp109 #name of the application
    #Status: NotStarted #Status tags optionals (get added as tags)
    TeamNames: #names of the team responsble, can be a team responsible for the whole app or a specific component , this creates pteam tags
      - SP_lima20
      - SP_axelot20
    Domain: Security  #domain = component or application can be used to group by bysiness unit
    SubDomain: Simplified Access Management  #sub-domain = component or application can be used to group by busienss unit
    ReleaseDefinitions: []
    Responsable: frankadm@admin.com #owner of the application mandatory, needs to be one of the user already created in the phoenix security
    Tier: 4 #importance from 1-10 higher -> more critical , 5 default = neutral
    Components:
      - ComponentName: product106-repo10 #name of the component 
        Status: Production #Tag Optional
        Type: Release #Tag Optional
        TeamNames:  #names of the team as it appears in hives and teams
          - SP_axelot20
          - SP_lima20
        RepositoryName: Phoenix-ent-demo/Damn-Vulnerable-Source-Code  #name of the repo as appears in phoenix ,can be more than one
        SearchName: search_item
        AssetType: REPOSITORY #Look up possible values in the documentation
        Tags:
          - "123"
          - "1235"
        Cidr: 10.1.1.0/24
        Fqdn: 
          - testfqdn
        Netbios: 
          - testbios
        OsNames: 
          - testosnames
        Hostnames: 
          - testhostnames
        ProviderAccountId: 
          - testaccountid
        ProviderAccountName: 
          - testaccountname
        ResourceGroup: 
          - testresourcegroup
        MultiConditionRule:
          AssetType: REPOSITORY #Look up possible values in the documentation
          RepositoryName: testrepo5
          SearchName: testsearch25
          Tags:
            - "1235"
            - "12355"
          Cidr: 10.1.5.0/24
          Fqdn: 
            - testfqdn5
          Netbios: 
            - testbios5
          OsNames: 
            - testosnames5
          Hostnames: 
            - testhostnames5
          ProviderAccountId: 
            - testaccountid5
          ProviderAccountName: 
            - testaccountname5
          ResourceGroup: 
            - testresourcegroup5

~~~


The function for Component creation is [CreateRepositories](Phoenix.ps1).

## Ticketing integration

Any environment/application/service/component can have a Ticketing integration. Just add this configuration to the respected item that you want to integrate:
``
Ticketing:
  - TIntegrationName: IAS-Jira # optional
    Backlog: abinitio - mandatory
``

Example config for application:
``
DeploymentGroups:
  - AppName: TST_TestApp10915 #name of the application
    Domain: Security  #domain = component or application can be used to group by bysiness unit
    SubDomain: Simplified Access Management  #sub-domain = component or application can be used to group by busienss unit
    ReleaseDefinitions: []
    Responsable: ciso4.test@company.com #owner of the application mandatory, needs to be one of the user already created in the phoenix security
    Tier: 4 #importance from 1-10 higher -> more critical , 5 default = neutral
    Deployment_set: Service1
    Ticketing:
      - TIntegrationName: IAS-Jira
        Backlog: abinitio
``

## Messaging integration

Any environment/application/service/component can have a Messaging integration. Just add this configuration to the respected item that you want to integrate:
``
Messaging:
  - MIntegrationName: IAS-Slack # optional
    Channel: abinitio # mandatory
``

Example config for application:
``
DeploymentGroups:
  - AppName: TST_TestApp10915 #name of the application
    Domain: Security  #domain = component or application can be used to group by bysiness unit
    SubDomain: Simplified Access Management  #sub-domain = component or application can be used to group by busienss unit
    ReleaseDefinitions: []
    Responsable: ciso4.test@company.com #owner of the application mandatory, needs to be one of the user already created in the phoenix security
    Tier: 4 #importance from 1-10 higher -> more critical , 5 default = neutral
    Deployment_set: Service1
    Messaging:
      - MIntegrationName: IAS-Slack
        Channel: abinitio
``

## Deployed Applications

Deployed applications is the association of Applications to the Service.

This is based on the logic that Applications (subdomains) are the same as the Service(subdomain).

This association is achieved via `Deployment_set` element in Application and Service.
Application and Service that have the same value of `Deployment_set` element will be included in the deployment. 
Deployment is done by application and service names.

Example:

```
DeploymentGroups:
  - AppName: TST_TestApp109 #name of the application
    AppID: 123444
    #Status: NotStarted #Status tags optionals (get added as tags)
    TeamNames: #names of the team responsble, can be a team responsible for the whole app or a specific component , this creates pteam tags
      - SP_lima20
      - SP_axelot20
    Domain: Security  #domain = component or application can be used to group by bysiness unit
    SubDomain: Simplified Access Management  #sub-domain = component or application can be used to group by busienss unit
    ReleaseDefinitions: []
    Responsable: frankadm@admin.com #owner of the application mandatory, needs to be one of the user already created in the phoenix security
    Tier: 4 #importance from 1-10 higher -> more critical , 5 default = neutral
    Deployment_set: Service1


Environment Groups:
  - Name: TST_Production
    Type: CLOUD
    Status: Production
    Responsable: frankadm@admin.com
    Tier: 2 #importance from 1-10
    TeamName: SP_lima20 #name of the team as it appears in hives and teams 
    Status: Production
    Tag: 
    Team:
    Services:
      - Service: Damn-Vulnerable-Source-Code_service
        Type: Cloud
        SearchName: Damn-Vulnerable-Source-Code
        Tag: issue:issue-test-asset3
        Tier: 2 #importance from 1-10
        Deployment_set: Service1
        # Deployment_tag: tag_123 #alternative tag to match the assets that are associated with this id 
        TeamName: SP_lima20 #name of the team as it appears in hives and teams 
```

Other way to create deployment is by using `Deployment_tag` on `Service` level. 
This approach matches values of application `Deployment_set` with service `Deployment_tag` and links them using the 
serviceSelector tags.

Example configuration:

```
DeploymentGroups:
  - AppName: TST_TestApp10910 #name of the application
    AppID: 123444
    #Status: NotStarted #Status tags optionals (get added as tags)
    TeamNames: #names of the team responsble, can be a team responsible for the whole app or a specific component , this creates pteam tags
      - SP_lima20
      - SP_axelot20
    Domain: Security  #domain = component or application can be used to group by bysiness unit
    SubDomain: Simplified Access Management  #sub-domain = component or application can be used to group by busienss unit
    ReleaseDefinitions: []
    Responsable: frankadm@admin.com #owner of the application mandatory, needs to be one of the user already created in the phoenix security
    Tier: 4 #importance from 1-10 higher -> more critical , 5 default = neutral
    Deployment_set: Service1

Environment Groups:
  - Name: TST_Infra
    Type: INFRA
    Tier: 2 #importance from 1-10
    Responsable: admin@admin.com
    TeamName: SP_axelot20 #name of the team as it appears in hives and teams 
    Status: Production
    Tag: infra
    Services:
    - Service: InfraGRP1
      Type: Infra
      Cidr: 10.1.1.0/24 #can be a /xx cidr
      Tier: 2 #importance from 1-10
      TeamName: SP_axelot20 #name of the team as it appears in hives and teams
      Tag: asset:Service1 
      Deployment_tag: Service1
```

## Auto-linking deployment sets

This action compares application names with service names, and if they are the same, or similar, deployment set is created.
Similarity is computed with Levenshtein ratio, equal names have ratio of 1.
Similarity is configurable through SIMILARITY_THRESHOLD in Phoenix.py script.
Deployment sets are created for Levenshtein ratio greater than SIMILARITY_THRESHOLD.


## Auto create teams from pteams

This action goes through all environments, services, applications and components, checks which teams are mentioned and 
automatically creates them if they are missing.
It will also create auto-link rules based on pteam tag.


## Create components from environment assets

This action will iterate over all environments, and then for each environment:
- fetch assets for configurable types (CLOUD, CODE, INFRASTRUCTURE, WEB, or ALL)
- group assets per name similarity or tag-based grouping (configurable via config.ini and autogroup.ini)
- for each asset group containing enough similar assets, suggest to user to create a component (component name can be overridden in console)
- if user confirms the component creation, component is created in that environment

### **🚀 Enhanced Component Creation Features**

#### **Full Asset Creation Mode** ⭐ **NEW**
When using `--create_automatically_groups=yes`, the system creates a complete Phoenix structure:
- **Environments**: Creates missing environments automatically
- **Services**: Creates services for CLOUD/CONTAINER/INFRA assets
- **Applications**: Creates applications for CODE/WEB/BUILD assets  
- **Components**: Creates components with proper asset assignment

#### **Preview & Confirmation System**
Before creating any resources, the system shows:
```
🔍 CREATION PREVIEW
==================
Will create:
📱 2 Applications (web-application, database-infrastructure)
🌍 3 Environments (prod-infra, prod-cloud, web-application)
🔧 4 Services (prod-db-mysql, prod-cache-redis, ...)
📦 2 Components (web-frontend, api-backend)

Proceed with creation? [Y=yes, N=no]: 
```

#### **Silent Mode for Automation**
Use `--silent` to skip all prompts for CI/CD integration:
```bash
# Fully automated asset creation
python run-phx.py client_id client_secret \
  --action_create_components_from_assets=true \
  --type=all \
  --create_automatically_groups=yes \
  --silent
```

#### **Asset Assignment Strategy**
The system intelligently routes assets based on type:
- **CODE/WEB/BUILD** → **Application Components**
- **CLOUD/CONTAINER** → **Environment Services** (Cloud type)
- **INFRA** → **Environment Services** (Infrastructure type)

### Configuration Options

You can customize the behavior by creating a `config.ini` file in the `Python script/Resources/` folder:

```ini
[asset_component_creation]
# Asset name similarity threshold (0.0 to 1.0)
# 1.0 = exact match required, 0.8 = 80% similarity, etc.
asset_name_similarity_threshold = 1.0

# Minimum number of assets with similar names to suggest component creation
asset_group_min_size_for_component_creation = 5
```

**Parameters:**
- `asset_name_similarity_threshold`: Controls how similar asset names must be to group together (default: 1.0 = exact match)
- `asset_group_min_size_for_component_creation`: Minimum number of assets needed to suggest component creation (default: 5)

Copy `Python script/Resources/config.ini.example` to `config.ini` and customize as needed.

### YAML Export Feature

When components are auto-created, they are saved to both:
1. **Phoenix Security Platform** (via API)
2. **Local YAML file** in `Python script/Resources/phx-auto-components_YYYYMMDD_HHMMSS.yaml`

The YAML file contains:
- All auto-created components with `phx-auto-` prefix
- Component metadata (team assignments, asset counts, etc.)
- Structured by Application → Environment → Components
- Can be used for backup, review, or re-importing components

Example YAML structure:
```yaml
Applications:
  WebApplication:
    Environments:
      production:
        Components:
          phx-auto-web-server:
            Status: null
            Type: null
            TeamNames: ["web-team"]
            auto_created: true
            original_name: web-server
            asset_count: 25
            asset_type: CONTAINER
```


## Overview of commands to run autoconfig, with examples

### LEGACY MODE - NOT MAINTAINED ANYMORE

| Command to run                                                                    | Example command                                                                                                                    | action_teams | action_code | action_cloud | action_deployment | action_autolink_deploymentset | action_autocreate_teams_from_pteams | action_create_components_from_assets |
|-----------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|--------------|-------------|--------------|-------------------|-------------------------------|-------------------------------------|--------------------------------------|
| create teams                                                                      | <span style="white-space:nowrap;">python run.py client_id client_secret True false false false false false false api_domain</span> | True         | false       | false        | false             | false                         | false                               | false                                |
| create applications and components                                                | <nobr>python run.py client_id client_secret false True false false false false false api_domain</nobr>                             | false        | True        | false        | false             | false                         | false                               | false                                |
| create environments and services                                                  | <nobr>python run.py client_id client_secret false false True false false false false api_domain</nobr>                             | false        | false       | True         | false             | false                         | false                               | false                                |
| Deployment by 'Deployment_set' or 'Deployment_tag'                                | <nobr>python run.py client_id client_secret false false false True false false false api_domain</nobr>                             | false        | false       | false        | True              | false                         | false                               | false                                |
| Auto create deployments based on application name <br>and service name similarity | <nobr>python run.py client_id client_secret false false false false True false false api_domain</nobr>                             | false        | false       | false        | false             | True                          | false                               | false                                |
| Auto create teams from pteam tags in config                                       | <nobr>python run.py client_id client_secret false false false false false True false api_domain</nobr>                             | false        | false       | false        | false             | false                         | True                                | false                                |
| Create assets from components/services<br> with similar name                      | <nobr>python run.py client_id client_secret false false false false false false True api_domain</nobr>                             | false        | false       | false        | false             | false                         | false                               | True                                 |

### NEW MODE

Command to run was updated to use different format:

python run-phx.py < clientId > < clientSecret > --api_domain=https://api.demo.appsecphx.io --action_autocreate_teams_from_pteam=true

It takes two positional arguments (clientId and clientSecret) right after the run.py
After that, you may specify any of these items listed:

| Option                                 | Description                                                                | Example                                     |
|----------------------------------------|----------------------------------------------------------------------------|---------------------------------------------|
| --api_domain                           | to override the value in Phoenix.py file                                   | --api_domain=https://api.demo.appsecphx.io  |
| --action_teams                         | Trigger teams action                                                       | --action_teams=true                         |
| --action_code                          | Trigger code action                                                        | --action_code=true                          |
| --action_cloud                         | Trigger cloud action                                                       | --action_cloud=true                         |
| --action_deployment                    | Trigger deployment action                                                  | --action_deployment=true                    |
| --action_autolink_deploymentset        | Trigger autolink deploymentset action                                      | --action_autolink_deploymentset=true        |
| --action_autocreate_teams_from_pteam   | Trigger autocreate teams from pteam action                                 | --action_autocreate_teams_from_pteam=true   |
| --action_create_components_from_assets | Trigger create components from assets action                               | --action_create_components_from_assets=true |

#### Examples of common usecases

Running actions (code + cloud + deployment)

```
python run-phx.py < clientId > < clientSecret > --action_code=true --action_cloud=true --action_deployment=true
```

Running actions (teams + code + cloud + deployment)

```
python run-phx.py < clientId > < clientSecret > --action_teams=true --action_code=true --action_cloud=true --action_deployment=true
```

If you want to override the API domain from Phoenix.py file, use this option:
```
--api_domain=https://newapi.appsecphx.io (or whatever is the domain)
```

## Error Handling and Logging

The script includes comprehensive error logging functionality that tracks failures in service creation, rule creation, and other operations. All errors are logged to an `errors.log` file in the same directory as the script.

### Error Log Format

Each error entry in the log file contains:
```
TIME: [Timestamp]
OPERATION: [Type of Operation]
NAME: [Name of Service/Component/Rule]
ENVIRONMENT: [Environment Name]
ERROR: [Error Message]
DETAILS: [Additional Context]
--------------------------------------------------------------------------------
```

### Types of Logged Errors

1. Service Creation Failures:
   - Failed service verifications
   - API errors during service creation
   - Timeout errors
   - Authentication failures

2. Rule Creation Failures:
   - Invalid rule configurations
   - Missing service errors
   - API validation errors
   - Case sensitivity issues

3. Component Creation Failures:
   - Component validation errors
   - Duplicate component errors
   - Missing required fields

### Example Error Log Entries

```
TIME: 2024-03-21 14:30:45
OPERATION: Service Creation
NAME: my-service
ENVIRONMENT: production
ERROR: Service creation verification failed after maximum retries
DETAILS: Team: dev-team, Tier: 3
--------------------------------------------------------------------------------

TIME: 2024-03-21 14:31:12
OPERATION: Rule Creation
NAME: repository-rule
ENVIRONMENT: staging
ERROR: Service not found after 3 attempts
DETAILS: Component: my-component, Filter: repository=repo-name
--------------------------------------------------------------------------------
```

### Using the Error Log

1. **Monitoring Failed Operations**:
   - Check `errors.log` after script execution to identify any failures
   - Each error entry includes timestamp and context for debugging
   - Failed operations are logged but don't stop script execution

2. **Debugging Common Issues**:
   - Service creation failures often indicate API timing issues
   - Rule creation failures may indicate missing or invalid configurations
   - Component failures usually relate to validation or duplicate entries

3. **Error Resolution**:
   - Review error details for specific failure reasons
   - Check component and service names for case sensitivity
   - Verify API credentials and permissions
   - Ensure all required fields are properly configured

### Error Log Location

The `errors.log` file is created in the same directory as the script. Each run appends new errors to the existing log file.

### Debug Mode

Set `DEBUG = True` in `Phoenix.py` to enable additional logging:
- Detailed API request payloads
- Response content for failed requests
- Verification attempt details
- Rule creation debugging information

### Common Error Types and Solutions

1. **Service Not Found (404)**:
   - Cause: Service creation succeeded but verification failed
   - Solution: Increase retry attempts or delay between retries
   - Configuration: Adjust `max_retries` and `base_delay` in service creation

2. **Bad Request (400)**:
   - Cause: Invalid payload or configuration
   - Solution: Check field names and values in configuration
   - Common issues: Case sensitivity, invalid characters in names

3. **Conflict (409)**:
   - Cause: Resource already exists
   - Solution: Usually safe to ignore, indicates duplicate creation attempt
   - Check existing resources if unexpected

4. **Authentication Errors**:
   - Cause: Invalid or expired credentials
   - Solution: Verify API credentials and token refresh
   - Check access permissions for operations

### Best Practices

1. **Regular Log Review**:
   - Check logs after each script run
   - Monitor for patterns in failures
   - Address recurring issues

2. **Log Maintenance**:
   - Rotate logs periodically
   - Archive old logs for reference
   - Clean up logs to manage file size

3. **Error Resolution**:
   - Address critical errors first
   - Group similar errors for batch resolution
   - Document common solutions

4. **Configuration Updates**:
   - Update configurations based on error patterns
   - Adjust timeouts and retries as needed
   - Document configuration changes

### Advanced Troubleshooting

With the new reporting feature in v4.5.2, troubleshooting is significantly easier:

1. **Using the Execution Report**:
   The automatic report shows exactly what failed and why, making troubleshooting much faster.

2. **Service Creation Issues**:
   ```python
   # Increase retry attempts and delays in providers/Phoenix.py
   max_retries = 5  # Default: 3
   base_delay = 5   # Default: 2
   ```

3. **Enable Debug Mode**:
   ```bash
   # Use verbose mode for detailed logging
   python run-phx.py client_id client_secret --action_teams=true --verbose
   ```

4. **API Rate Limiting**:
   - Monitor response headers for rate limits
   - The execution report will show timing-related failures
   - Batch operations when possible 

### Asset Grouping and Component Creation

For automated component creation from assets:
- Group assets per name similarity (configurable through `ASSET_NAME_SIMILARITY_THRESHOLD` variable in Phoenix.py)
- For each asset group containing more than 5 assets, suggest creating a component (component name can be overridden in console)
- Number of assets in group is configurable through `ASSET_GROUP_MIN_SIZE_FOR_COMPONENT_CREATION` variable in Phoenix.py
- If user confirms the component creation, component is created in that environment

## 📚 Additional Resources

### **Documentation Files**
- **[YAML Configuration Guide](YAML_CONFIGURATION_GUIDE.md)** - Complete guide with examples, validation, and troubleshooting
- **[YAML Quick Reference](YAML_QUICK_REFERENCE.md)** - Quick lookup reference for common patterns and validation
- **[CHANGELOG.md](CHANGELOG.md)** - Detailed version history and recent improvements

### **Configuration Validation**
- Use the built-in linter to validate your YAML before deployment
- Check the [supported AssetType values](#supported-assettype-values) for proper configuration
- Review error logs for troubleshooting failed operations

### **Best Practices**
- Start with small configurations and incrementally add complexity
- Test configurations in development environments first
- Keep backup copies of working configurations
- Review and update team configurations regularly
- **Use the execution reporting**: Monitor success rates and review error details after each run
- **Enable verbose mode**: Use `--verbose` flag when troubleshooting issues

---

**Questions or Need Help?** Check the [YAML Configuration Guide](YAML_CONFIGURATION_GUIDE.md) for detailed examples and troubleshooting, or consult the [YAML Quick Reference](YAML_QUICK_REFERENCE.md) for immediate guidance.

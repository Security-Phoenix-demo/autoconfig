## Versioning

V 4.2
Date - 28 Feb 2025

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

Individual team configurations in the `Teams` directory:

```yaml
TeamName: DevTeam
AzureDevopsAreaPath: company\DevTeam
TeamMembers:
  - Name: John Doe
    EmailAddress: john.doe@company.com
    EmployeeType: Employee
```

### Hives Configuration (hives.yaml)

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

``
CreateUsersForApplications: True 
``

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

## Applications

Applications are groupings of code that provide functionality for a service. As per environment services the `subdomain` in `core-structure.yaml`.

For python the application and component are created: in `core-structure.yaml`.

The function is called [CreateApplications](Phoenix.ps1)

If you want to create users from DeploymentGroups.Responsable field, set the variable in core-structure.yaml file

``
CreateUsersForApplications: True 
``

Example core-structure.yaml file

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
- fetch assets for types ("CONTAINER", "CLOUD")
- group assets per name similarity (similarity is configurable through ASSET_NAME_SIMILARITY_THRESHOLD variable in Phoenix.py)
- for each asset group containing more than 5 assets, suggest to user to create a component (component name can be overridden in console)
    - number of assets in group is configurable through ASSET_GROUP_MIN_SIZE_FOR_COMPONENT_CREATION variable in Phoenix.py
- if user confirms the component creation, component is created in that environment


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

python run-phx.py < clientId > < clientSecret > --api_domain=https://api.demo.appsecphx.io --verify=True --action_autocreate_teams_from_pteam=True

It takes two positional arguments (clientId and clientSecret) right after the run.py
After that, you may specify any of these items listed:

| Option                                 | Description                                                                | Example                                     |
|----------------------------------------|----------------------------------------------------------------------------|---------------------------------------------|
| --api_domain                           | to override the value in Phoenix.py file                                   | --api_domain=https://api.demo.appsecphx.io  |
| --verify                               | Flag to run the simulated mode, without committing the changes to platform | --verify=True                               |
| --action_teams                         | Trigger teams action                                                       | --action_teams=True                         |
| --action_code                          | Trigger code action                                                        | --action_code=True                          |
| --action_cloud                         | Trigger cloud action                                                       | --action_cloud=True                         |
| --action_deployment                    | Trigger deployment action                                                  | --action_deployment=True                    |
| --action_autolink_deploymentset        | Trigger autolink deploymentset action                                      | --action_autolink_deploymentset=True        |
| --action_autocreate_teams_from_pteam   | Trigger autocreate teams from pteam action                                 | --action_autocreate_teams_from_pteam=True   |
| --action_create_components_from_assets | Trigger create components from assets action                               | --action_create_components_from_assets=True |

#### Examples of common usecases

Running actions (code + cloud + deployment)

``
python run-phx.py < clientId > < clientSecret > --action_code=true --action_cloud=true --action_deployment=true
``

Running actions (teams + code + cloud + deployment)

``
python run-phx.py < clientId > < clientSecret > --action_teams=true --action_code=true --action_cloud=true --action_deployment=true
``

If you want to override the API domain from Phoenix.py file, use this option:
``
--api_domain=https://newapi.appsecphx.io (or whatever is the domain)
``

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

### Troubleshooting Tips

1. **Service Creation Issues**:
   ```python
   # Increase retry attempts and delays
   max_retries = 5  # Default: 3
   base_delay = 5   # Default: 2
   ```

2. **Rule Creation Issues**:
   ```python
   # Enable debug mode for detailed logging
   DEBUG = True
   ```

3. **Component Verification**:
   ```python
   # Add verification delay
   time.sleep(delay)  # Adjust delay as needed
   ```

4. **API Rate Limiting**:
   - Monitor response headers for rate limits
   - Implement exponential backoff
   - Batch operations when possible 
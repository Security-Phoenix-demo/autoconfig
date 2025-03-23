## Versioning

V 4.5
Date - 22 March 2025

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

2. MultiConditionRule - can combine repos, search, tags etc in one rule

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

~~~

## Applications

Applications are groupings of code that provide functionality for a service. As per environment services the `subdomain` in `core-structure.yaml`.

For python the application and component are created: in `core-structure.yaml`.

The function is called [CreateApplications](Phoenix.ps1)

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

2. MultiConditionRule - can combine repos, search, tags etc in one rule

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
          RepositoryName: testrepo
          SearchName: testsearch2
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

3. Combining single rule with multicondition rule is also supported

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
          RepositoryName: testrepo
          SearchName: testsearch2
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


The function for Component creation is [CreateRepositories](Phoenix.ps1).

## Deployed Applications

Deployed applications is the association of Applications to the Service.

This is based on the logic that Applications (subdomains) are the same as the Service(subdomain).

This association is achieved via `Deployment_set` element in Application and Service.
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

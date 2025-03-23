## Versioning

V 2.1.0
Date - 04 October 2024

# Introduction

This [repo](xxx) provides a method of getting data from your organization repos, teams and domains to [Phoenix](https://phoenix domain).

The following API credentials are required:

1. Phoenix  API Client ID and Client Secret.

## Schedule

The service support flags to run key functions to help avoid exceeding the 60 min cron limit.

- teams - Creates new teams, assigns members to teams, removes members from teams they should no longer have access to (Defaults to true)
- code - Creates applications (sub domains) and the associated components (repos) and rules (Defaults to true)
- cloud - Create Cloud Environments and services (Subdomains) along with associated rules (Defaults to false)

As the job takes typically between 50 - 59 minutes (depending on the size of your org might take less) to complete it is only ran once a day as to not block other pipelines using the release agent.

If required the job can be run adhoc from DevOPS.

## Obtaining Phoenix API Credentials

**Note:** This is for testing hence it using separate credentials, for BAU the Credentials Called "API" in Phoenix are used.

When you run Run.ps1 locally it will prompt you for the

- ClientID
- Client Secret

**Never checkin to code the credentials.**

1. Logon to [Phoenix] *your Phoenix Domain using SSO.
2. Click Settings.
3. Click Organization.
4. Click API Access.
5. Click Create API credential.
6. Take a copy of the key and keep it secret.

## API endpoint

The Phoenix base endpoint for API requests is: [https://api.YOURDOMAIN.securityphoenix.cloud](https://api.YOURDOMAIN.securityphoenix.cloud)

## Obtaining Access token

Using the Phoenix API Credentials you must obtain an Access token that is only valid for a limited amount of time to invoke the Phoenix API's.

This is done via making a HTTP GET call to [v1/auth/access_token](https://YOURDOMAIN.securityphoenix.cloud/v1/auth/access_token).

See function `GetAuthToken`.

The response will contain the access token.

The request to the API will contain a **Authorization** header with a basic base64 encoded byte array.

The byte array is "ClientId : clientSecret"

## Local Debugging

When running the code locally you will need to download `core-structure.yaml` and `hives.yaml` from Release data to a folder called `Resources`.

You will also need a copy of the `Teams` folder and its yaml 

## Local Testing (optional) - Powershell

The project uses Pester for testing. From a powershell command prompt type: `invoke-pester`.

## Hives

A member of your org maybe responsible for one or more team teams. This is currently configured via the (hives.yaml) file.

## Teams

Teams are created by the entries within the team data structure

The teams have component association rules based on the tag pteam `pteam` tag to the API request to Phoenix.

Example `pteam:axelot`.

The function [CreateTeams] Phoenix.ps1

## Team Assignment

Staff need to first login to the [Phoenix portal](https://YOURDOMAIN.securityphoenix.cloud/) using SSO before they can be assigned to a team.

The assignment should be run once a day (at least) [Phoenix Cron job]

The [Teams Yaml] Teams files are used as a source of truth of who belongs to which team.

The function [AssignUsersToTeam] Phoenix.ps1

## Hive Leaders

The [Hives Yaml] hives.yaml contains a list of leaders who are responsible for 1 or more teams.

The function [AssignUsersToTeam] Phoenix.ps1

## Coud subscriptions
in the main run.ps1 the subscriptions are assigned a criticality level and grouped from production to development, use the Azure or AWS subscription ID in these specification

The association of assets to subdomains is done via rules and looking up the pipeline tag against each deployed cloud asset / for AWS those can be cloudformation ID

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

## Applications

Applications are groupings of code that provide functionality for a service. As per environment services the `subdomain` in `core-structure.yaml`.

The function is called [CreateApplications](Phoenix.ps1)

## Components

Component can be create using one or more repositories, web apps, the guidance should be using one subdomain/component per team managing it. 
`core-structure.yaml` contains these definitions from which rules are generated.

Tiering from release data is used to help highlight important repositories.

The tiering in Phoenix work 1 - 10 (10 being most important).

Team allocation is performed by added a `pteam` tag to the API request to Phoenix.

Example `pteam:axelot`.

The function for Component creation is [CreateRepositories](Phoenix.ps1).

## Deployed Applications

Deployed applications is the association of Applications to the Service.

This is based on the logic that Applications (subdomains) are the same as the Service(subdomain).

Due to the infrequency of new services these are currently created manually via the Phoenix UI.

Note: an updated version of this script will be released with the API to allocate the Tag deployment traceability with Applications

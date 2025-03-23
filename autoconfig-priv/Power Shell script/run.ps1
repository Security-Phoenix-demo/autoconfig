. $PSScriptRoot\providers\Phoenix.ps1
. $PSScriptRoot\providers\Utils.ps1
. $PSScriptRoot\providers\YamlHelper.ps1
. $PSScriptRoot\providers\Aks.ps1

#Global Variables
$ResouceFolder = "$PSScriptRoot\Resources"
$clientID
$clientSecret
$accessToken = ""
$actionTeams = $true
$actionCode = $true
$actionCloud = $true

#Set the initial variables via either pass in or by asking the user
Write-Host "Arguments supplied is:" $args.Count

if ($args.Count -eq 5) {
    $clientID = $args[0]
    $clientSecret = $args[1]

    if ($args[2] -eq $false) {
        $actionTeams = $false
    }

    if ($args[3] -eq $false) {
        $actionCode = $false
    }

    if ($args[4] -eq $false) {
        $actionCloud = $false
    }

    Write-Host "Teams:" $actionTeams
    Write-Host "Code:" $actionCode
    Write-Host "Cloud:" $actionCloud
}
else {
    $clientID = Read-Host -Prompt "Please enter clientID"
    $clientSecret = Read-Host -Prompt "Please enter clientSecret"
}

$environments = @()

$repos = PoplulateRepositories $ResouceFolder
$domains = PopulateDomains $repos
$Teams = PopulateTeams $ResouceFolder
$HiveStaff = PopulateHives $ResouceFolder
$SubdomainOwners = PopulateSubdomainOwners $repos
$Subdomains = GetSubdomains $repos

Write-Host "[Teams]"
foreach ($team in $Teams) {
    try {
        if ($team.AzureDevopsAreaPath -like "*Team*") {
            $team.TeamName = ($team.AzureDevopsAreaPath -split ('Team'))[1].Trim()
            Write-Host $team.TeamName
        }
    }
    catch {
        Write-Host "Error: " $_.Exception.Message
    }
}

Write-Host ""
Write-Host "[Domains]"

$domains

Write-Host ""
Write-Host "[Repos]"

$repos
Write-Host ""

$environments += [PSCustomObject]@{
    Name          = "Production"
    Criticality   = 10
    CloudAccounts = "", "" #cloud account / resource name that make prod
}

$environments += [PSCustomObject]@{
    Name          = "Development"
    Criticality   = 5
    CloudAccounts = ""#cloud account / resource name that make dev
}

$environments += [PSCustomObject]@{
    Name          = "DevOPS"
    Criticality   = 5
    CloudAccounts = ""  #cloud account / resource name that make devops
}

$environments += [PSCustomObject]@{
    Name          = "Thirdparty"
    Criticality   = 5
    CloudAccounts = ""
}

$environments += [PSCustomObject]@{
    Name          = "SIM"
    Criticality   = 8
    CloudAccounts = "" #cloud account / resource name that make SIMULATION
}

$environments += [PSCustomObject]@{
    Name          = "Staging"
    Criticality   = 7
    CloudAccounts ="" #cloud account / resource name that make STAGING
}

$accessToken = GetAuthToken $clientID $clientSecret

$headers = @{
    "Authorization" = "Bearer $accessToken"
    "Content-Type"  = "application/json"
}

$phoenixComponents = GetPhoenixComponents
$pteams = PopulatePhoenixTeams
$ApplicationEnvironments = PopulateApplicationsAndEnvironments

$sw = [Diagnostics.Stopwatch]::StartNew()

if ($actionTeams -eq $true) {
    Write-Host "Performing Teams Actions"
    $AllTeamAccess = PopulateUsersWithAllTeamAccess $Teams
    CreateTeams
    CreateTeamRules
    AssignUsersToTeam

    $sw.Stop()
    Write-Host
    Write-Host "[Diagnostic] [Teams] Time Taken: " $sw.Elapsed
    Write-Host
    $sw.Reset()
}

if ($actionCloud -eq $true) {
    Write-Host "Performing Cloud Actions"
    foreach ($environment in $environments) {
        if (-not ($ApplicationEnvironments | Where-Object { $_.Name -eq $environment.Name -and $_.type -eq "ENVIRONMENT" })) {
            CreateEnvironments $environment.Name $environment.Criticality "CLOUD"
        }
    }
        
    AddEnvironmentServices $Subdomains $ApplicationEnvironments $phoenixComponents $SubdomainOwners $Teams
    Write-Host "[Diagnostic] [Cloud] Time Taken: " $sw.Elapsed
    Write-Host "Starting Cloud Asset Rules"
    AddCloudAssetRules
    Write-Host "[Diagnostic] [Cloud] Time Taken: " $sw.Elapsed
    Write-Host "Starting Third Party Rules"
    AddThirdpartyServices $phoenixComponents $ApplicationEnvironments $SubdomainOwners

    $sw.Stop()
    Write-Host
    Write-Host "[Diagnostic] [Cloud] Time Taken: " $sw.Elapsed
    Write-Host
    $sw.Reset()
}

if ($actionCode -eq $true) {
    $clusterImages = @()

    $file = "AKSImages.csv"

    foreach ($subscription in GetSubscriptions) {
        Write-Host $subscription.Name
    
        $clusters = GetClusters $subscription
        foreach ($cluster in $clusters) {
            $clusterImages += GetClusterImages $cluster
        }
    
        Write-Host "Total Images Tally:" $clusterImages.Count

        if ($null -ne $clusterImages -and $clusterImages.Count -gt 0){
            $clusterImages | Export-Csv -Path $file -NoTypeInformation -Force
        }

        Start-Sleep -Seconds 5
    }

    if (Test-Path -Path $file) {
        Write-Host "Processing " $file
        $csvData = Import-Csv -Path $file

        $serviceLookup = @{}
        $serviceLookup["workload-identity-webhook"] = "Compute"
    
        foreach ($row in $csvData) {
            $found = $false
            if ($row.Repo -ne "") {
                Write-Host "Row: " $row.Repo

                if ($serviceLookup.ContainsKey($row.Repo)) {
                    $environment = $environments | Where-Object { $row.SubscriptionId -in $_.CloudAccounts }
                
                    if ($null -ne $environment) {
                        AddContainerRule $row.ContainerUrl $serviceLookup[$row.Repo] $environment.Name
                        $found = $true;
                    }
                }

                if ( $found -eq $false) {
                    #Cross reference the Repo with repos, get the Subdomain
                    $repo = $repos | Where-Object { $_.RepositoryName -eq $row.Repo } | Select-Object -First 1

                    if ($null -ne $repo) {
                        Write-Host "Match found. Subdomain: " $repo.Subdomain
                                
                        # Find the environment that the row's SubscriptionId belongs to
                        $environment = $environments | Where-Object { $row.SubscriptionId -in $_.CloudAccounts }
                
                        if ($null -ne $environment) {
                            Write-Host "Environment found: " $environment.Name
                            AddContainerRule $row.ContainerUrl $repo.Subdomain $environment.Name
                        }
                    }
                }
            }
        }
    }

    Write-Host "Performing Code Actions"
    CreateApplications $Subdomains $ApplicationEnvironments
    CreateRepositories $repos
    RemoveOldTags $phoenixComponents

    $sw.Stop()
    Write-Host
    Write-Host "[Diagnostic] [Code] Time Taken: " $sw.Elapsed
}
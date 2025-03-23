$APIdomain = "https://api.YOURDOMAIN.securityphoenix.cloud"

function GetAuthToken ($clientID, $clientSecret) {
    # Convert client ID and secret to Base64 for Basic Auth
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($clientID + ':' + $clientSecret)
    $base64 = [System.Convert]::ToBase64String($bytes)

    # Define the authorization header using Basic auth
    $authheader = @{
        Authorization = "Basic $base64"
    }

    # Token endpoint
    $tokenUrl = $APIdomain + '/v1/auth/access_token'

    Write-Host "Making request to " $tokenUrl " to obtain token".
    try {
        $response = Invoke-RestMethod -Uri $tokenUrl -Method Get -Headers $authheader

        # Access token
        $accessToken = $response.token

        Write-Host "Access token obtained"    
    }
    catch {
        Write-Host "Error onbtaining token possble bad clientID or secret"
        Write-Host  $_.Exception.Message
        Exit 1
    }

    return  $accessToken
}

function CreateEnvironments {
    param ($name, $criticality, $envType)

    Write-Host "[Environment]"

    try {
        $payload = @{
            "name"        = $name
            "type"        = "ENVIRONMENT"
            "subType"     = $envType
            "criticality" = $criticality
            "owner"       = @{
                "email" = "admin@company.com"
            }
        }

        $payload = $payload | ConvertTo-Json -Depth 2
        $APIUrl = ConstructAPIUrl  "/v1/applications"

        
        Invoke-RestMethod -Uri $APIUrl -Method Post -Headers $headers -Body $payload

        Write-Host " + Environment added " $name

    }
    catch {
        if ($_.Exception.Response.StatusCode -eq "Conflict") {
            Write-Host " > Environment already exists"
        }
        else {
            Write-Host $_.Exception.Message
            Exit 1
        }
    }
}

function PopulateApplicationsAndEnvironments {
    $components = @()

    try {
        Write-Host "Getting list of Phoenix Applications and Environments"
        $APIUrl = ConstructAPIUrl  "/v1/applications"
        $response = Invoke-RestMethod -Uri $APIUrl  -Method Get -Headers $headers
    
        $components = $response.content
    
        $totalPages = $response.totalPages
    
        for ($i = 1; $i -lt $totalPages; $i++) {
            $APIUrl = ConstructAPIUrl  ("/v1/applications?pageNumber=" + $i)
            $response = Invoke-RestMethod -Uri $APIUrl  -Method GET -Headers $headers
    
            $components += $response.content
        }
    }
    catch {
        Write-Host $_.Exception.Message
        Exit 1
    }

    return $components 
}

function AddEnvironmentServices {
    param ($Subdomains, $ApplicationEnvironments, $phoenixComponents, $SubdomainOwners, $Teams)

    foreach ($environment in $environments) {
        $envName = $environment.Name
        $envID = GetEnvironmentID $ApplicationEnvironments $envName

        Write-Host "[Services] for " $envName

        if ($environment.CloudAccounts -ne "") {
            foreach ($subdomain in $Subdomains) {
                if ((EnvironmentServiceExist $envID $phoenixComponents $subdomain.Name) -eq $false) {
                    AddService $envName $subdomain.Name $subdomain.Tier $subdomain.Domain $SubdomainOwners
                }
            }

            if ((EnvironmentServiceExist $envID $phoenixComponents "Databricks") -eq $false) {
                AddService $envName "Databricks" 5 "YOURDOMAIN Data" $SubdomainOwners
            }

            $groupedRepos = $repos | Group-Object -Property Subdomain

            foreach ($group in $groupedRepos) {
                Write-Host "Subdomain: " $group.Name
                $reposInSubdomain = $group.Group
                $buildDefinitions = $reposInSubdomain | ForEach-Object { $_.BuildDefinitionName }

                AddServiceRuleBatch $environment $group.Name "pipeline" $buildDefinitions
            }

            AddServiceRule $environment "Compute" "node_type" "bacs"
            AddServiceRule $environment "Compute" "node_type" "shared"
            AddServiceRule $environment "Compute" "node_type" "account"
            AddServiceRule $environment "Compute" "node_type" "mccy"
            AddServiceRule $environment "Compute" "node_type" "chaps"
            AddServiceRule $environment "Compute" "node_type" "fps"
            AddServiceRule $environment "Compute" "node_type" "system"
        }
    }
}


function AddService {
    param ($environment, $service, $tier, $domain, $SubdomainOwners)


    if ($domain -eq "FX") {
        $domain = "Foreign Exchange(FX)"
    }

    if ($service -eq "FX") {
        $service = "Foreign Exchange(FX)"
    }

    $criticality = CalculateCriticality $tier

    try {   

        Write-Host "> Attempting to add " $service
        $payload = @{
            "name"                = $service
            "criticality"         = $criticality
            "tags"                = @()
            "applicationSelector" = @{
                "name" = $environment
            }
        }

        foreach ($team in $SubdomainOwners[$service]) {
            $tag = @{
                "key"   = "pteam"
                "value" = $team
            }
            $payload.tags += $tag
        }

        $domainTag = @{
            "key"   = "domain"
            "value" = $domain
        }
        $payload.tags += $domainTag

        $payload = $payload | ConvertTo-Json -Depth 3
       

        $APIUrl = ConstructAPIUrl  "/v1/components"
        Invoke-RestMethod -Uri $APIUrl -Method Post -Headers $headers -Body $payload
        Write-Host " + Added Service" $service
        Start-Sleep -Seconds 2
    }
    catch {
        if ($_.Exception.Response.StatusCode -eq "409") {
            Write-Host " > Service" $service "already exists" 
        }
        else {
            Write-Host $_.Exception.Message
            Exit 1
        }
    }
}

function AddContainerRule {
    param ($image, $subdomain, $enviromentname)
    try {
        Write-Host "Adding Container for image" $image  

        if ($subdomain -eq "FX") {
            $subdomain = "Foreign Exchange(FX)"
        }

        $rules = @(
            @{
                "name"   = $image
                "filter" = @{
                    "keyLike" = "*" + $image + "*"
                }
            }
        )
            
        $payload = @{
            "selector" = @{
                "applicationSelector" = @{
                    "name"          = $enviromentname
                    "caseSensitive" = $false
                }
                "componentSelector"   = @{
                    "name"          = $subdomain
                    "caseSensitive" = $false
                }
            }
            "rules"    = $rules
        }

        $payload = $payload | ConvertTo-Json -Depth 3

        $APIUrl = ConstructAPIUrl  "/v1/components/rules"
        Invoke-RestMethod -Uri $APIUrl -Method Post -Headers $headers -Body $payload
        Write-Host "+ Container Rule added"
    }
    catch {
        if ($_.Exception.Response.StatusCode -eq "Conflict") {
            Write-Host " > Container Service Rule" $tagValue "already exists" 
        }
        elseif ($_.Exception.Response.StatusCode -eq 404) {
            Write-Host $_.Exception.Message
        }
        else {
            Write-Host $_.Exception.Message
            Exit 1
        }
    }
}

function AddServiceRuleBatch
{
    param ($environment, $service, $tagName, $tagValue)

    try {
        
            if ($service -eq "FX") {
                $service = "Foreign Exchange(FX)"
            }

            Write-Host "Adding Service Rule" $service "to" $environment.Name

            $payload = @{
                "selector" = @{
                    "applicationSelector" = @{
                        "name" = $environment.Name
                        "caseSensitive" = $false
                    }
                    "componentSelector" = @{
                        "name" = $service
                        "caseSensitive" = $false
                    }
                }
                "rules" = @(
                   
                        foreach($tag in $tagValue)
                        {
                            @{
                            "name" = "$tagName $tag"
                            "filter" = @{
                                "tags" = @(
                                    @{
                                        "key" = $tagName
                                        "value" = $tag
                                    }
                                )
                                "providerAccountId" = $environment.CloudAccounts
                            }
                        }
                        
                    }
                )
            } | ConvertTo-Json -Depth 5

            $APIUrl = ConstructAPIUrl  "/v1/components/rules"
            Invoke-RestMethod -Uri $APIUrl -Method Post -Headers $headers -Body $payload
            Write-Host "+ Service Rule added"

        }
    catch {
            if ($_.Exception.Response.StatusCode -eq "Conflict") {
                Write-Host " > Service Rule" $service "already exists" 
            }
            elseif ($_.Exception.Response.StatusCode -eq 404) {
                Write-Host $_.Exception.Message
            }
            else {
                Write-Host $_.Exception.Message
                Exit 1
            }
        }
} 

function AddServiceRule {
    param ($environment, $service, $tagName, $tagValue)

    try {
        if ($service -eq "FX") {
            $service = "Foreign Exchange(FX)"
        }
        
        Write-Host "Adding Service Rule" $service "tag" $tagValue 

        $payload = '{
            "selector": {
                "applicationSelector": {
                  "name": "'+$environment.Name+'",
                  "caseSensitive": false
                  },            
                "componentSelector" : {
                  "name" : "' + $service + '",
                  "caseSensitive": false
                }
              },
              "rules": [
                {
                  "name": "'+ $tagName + ' ' + $tagValue +'",
                  "filter": {
                  "tags": [
                   {
                    "key": "'+$tagName+'",
                    "value": "'+ $tagValue +'"
                   }],
                   "providerAccountId": ['
                     foreach($cloudAccount in $environment.CloudAccounts)
                     { 
                        $payload+= '"'  +$cloudAccount + '",'
                     }
                     
                     $payload+= ']

                  }
                }
              ]
            }
          }'
          $payload = $payload.Replace(",]","]")

        $swRepo = [Diagnostics.Stopwatch]::StartNew()
        $swRepo.Start()
        $APIUrl = ConstructAPIUrl  "/v1/components/rules"
        Invoke-RestMethod -Uri $APIUrl -Method Post -Headers $headers -Body $payload
        Write-Host "+ Service Rule added"
    }
    catch {
        if ($_.Exception.Response.StatusCode -eq "Conflict") {
            Write-Host " > Service Rule" $tagValue "already exists" 
        }
        elseif ($_.Exception.Response.StatusCode -eq 404) {
            Write-Host $_.Exception.Message
        }
        else {
            Write-Host $_.Exception.Message
            Exit 1
        }
    }

    $swRepo.Stop()
    Write-Host "[Diagnostic] Time Taken: " $swRepo.Elapsed

    if ($swRepo.Elapsed.seconds -ge 7) {
        Write-Host "Sleep as over threshold"
        Start-Sleep -Seconds 1
    }
    $swRepo.Reset()
}

function AddThirdpartyServices {
    param($phoenixComponents, $ApplicationEnvironments, $SubdomainOwners)

    $services = @(
        "Salesforce", 
        "Sharepoint", 
        "Dynamics", 
        "Vulcan",
        "IriusRisk",
        "Resolver",
        "Snyk",
        "e-learning",
        "Dynatrace",
        "Pagerduty",
        "PTRG",
        "Freshdesk",
        "Huggg",
        "Lastpass",
        "LinkedIn",
        "Hacksplaining",
        "Hava",
        "Panorays",
        "Healix",
        "ADP",
        "Power BI",
        "Power Platform",
        "Sentinel",
        "Panorays",
        "CultureAI",
        "Workable",
        "Elastic Cloud",
        "Zscaler",
        "Tableau",
        "Exela",
        "Purview"
    )

    $envName = "Thirdparty"
    $envID = GetEnvironmentID $ApplicationEnvironments $envName


    foreach ($service in $services) {
        if ((EnvironmentServiceExist $envID $phoenixComponents $service) -eq $false) {
            AddService "Thirdparty" $service 5 "Thirdparty" $SubdomainOwners
        }
    }
}


function CreateApplications {
    param ($Subdomains, $ApplicationEnvironments)

    Write-host "[Applications]"
    foreach ($subdomain in $Subdomains) {
        if (-not ($ApplicationEnvironments | Where-Object { $_.Name -eq $subdomain.Name -and $_.type -eq "APPLICATION" })) {
            CreateApplication $subdomain.Name $subdomain.Domain
        }
    }

    CreateApplication "Manual Workflows" "DevOPS"
    CreateApplication "Testing" "DevOPS"
    CreateApplication "Tests" "DevOPS"
}

function CreateApplication {

    param($name, $domain)

    try {
        $payload = @{
            "name"        = $name
            "type"        = "APPLICATION"
            "criticality" = 5
            "tags"        = @(
                @{
                    "key"   = "domain"
                    "value" = $domain
                }
            )
            "owner"       = @{
                "email" = "admin@company.com"
            }
        }

        $payload = $payload | ConvertTo-Json

        $APIUrl = ConstructAPIUrl  "/v1/applications"
        Invoke-RestMethod -Uri $APIUrl  -Method Post -Headers $headers -Body $payload
        Write-Host " + Application" $name "added"
        Start-Sleep -Seconds 2

    }
    catch {
        if ($_.Exception.Response.StatusCode -eq "Conflict") {
            Write-Host " > Application" $name "already exists" 
        }
        else {
            Write-Host $_.Exception.Message
            Exit 1
        }
    }

    CreateCustomComponent $name "Manual Finding"
    CreateCustomFindingRule $name $domain "Manual Finding"
}

function CreateCustomComponent {
    param ($application, $componentName)

    try {
        $payload = @{
            "applicationSelector" = @{
                "name" = $application
            }
            "name"                = $componentName
            "criticality"         = 5
        }

        $payload = $payload | ConvertTo-Json -Depth 2

        $APIUrl = ConstructAPIUrl  "/v1/components"
        Invoke-RestMethod -Uri $APIUrl  -Method Post -Headers $headers -Body $payload
        Write-Host $componentName " component added."
        Start-Sleep -Seconds 2
        
    }
    catch {
        if ($_.Exception.Response.StatusCode -eq "Conflict") {
            Write-Host " > Component" $application " already exists" 
        }
        else {
            Write-Host $_.Exception.Message
            Exit 1
        }
    }
}

function CreateCustomFindingRule {
    param (
        $application, $domain, $componentName
    )
    
    try {
        $payload = @{
            "selector" = @{
                "applicationSelector" = @{
                    "name"          = $application
                    "caseSensitive" = $false
                }
                "componentSelector"   = @{
                    "name"          = $componentName
                    "caseSensitive" = $false
                }
            }
            "rules"    = @(
                @{
                    "name"   = "$application $componentName"
                    "filter" = @{
                        "tags"       = @(
                            @{
                                "key"   = "subdomain"
                                "value" = $application
                            }
                        )
                        "repository" = @($componentName)
                    }
                }
            )
        }

        $payload = $payload | ConvertTo-Json -Depth 6
        $APIUrl = ConstructAPIUrl  "/v1/components/rules"
        Invoke-RestMethod -Uri $APIUrl  -Method Post -Headers $headers -Body $payload
        Write-Host $componentName " rule added."
        Start-Sleep -Seconds 2
    }
    catch {
        if ($_.Exception.Response.StatusCode -eq "Conflict") {
            Write-Host " > Custom Component already exists" 
        }
        else {
            Write-Host $_.Exception.Message
            Exit 1
        }
    }
}


function CreateRepositories {
    param($repos)

    foreach ($repo in $repos) {

        CreateRepo $repo
    }
}

# Create the payload, the function assume 1 repo per component with the component name being the repository this can be edited

function CreateRepo {
    param ($repo)

    try {
        $criticality = CalculateCriticality $repo.Tier
        $payload = @{
            "repository"          = "$($repo.RepositoryName)"
            "applicationSelector" = @{
                "name"          = $repo.Subdomain
                "caseSensitive" = $false
            }
            "component"           = @{
                "name"        = $repo.RepositoryName
                "criticality" = $criticality
                "tags"        = @(
                    @{
                        "key"   = "pteam"
                        "value" = $repo.Team
                    },
                    @{
                        "key"   = "domain"
                        "value" = $repo.Domain
                    },
                    @{
                        "key"   = "subdomain"
                        "value" = $repo.Subdomain
                    }
                )
            }
        }

        $payload = $payload | ConvertTo-Json -Depth 3
        $APIUrl = ConstructAPIUrl  "/v1/applications/repository"
        Invoke-RestMethod -Uri $APIUrl  -Method Post -Headers $headers -Body $payload
        Write-Host " +" $repo.RepositoryName "added."
    }
    catch {
        if ($_.Exception.Response.StatusCode -eq "Conflict") {
            Write-Host " > Repo" $repo.RepositoryName "already exists" 
        }
        else {
            Write-Host $_.Exception.Message
            Exit 1
        }
    }
}

function AddCloudAssetRules 
{

    foreach ($repo in $repos) {

        $searchTerm = "*" + $repo.RepositoryName + "(*"
        CloudAssetRule $repo.subdomain $searchTerm "Production"
    }

    CloudAssetRule "PowerPlatform" "powerplatform_prod" "Production"
    CloudAssetRule "PowerPlatform" "powerplatform_sim" "Sim"
    CloudAssetRule "PowerPlatform" "powerplatform_staging" "Staging"
    CloudAssetRule "PowerPlatform" "powerplatform_dev" "Development"

}

function CloudAssetRule { 
    param($name, $searchTerm, $envioronmentName)

    try { 
        Write-Host "Adding Cloud Asset Rule" $name 

        if ($name -eq "FX") {
            $name = "Foreign Exchange(FX)"
        }

        $payload = @{
            "selector" = @{
                "applicationSelector" = @{
                    "name"          = $envioronmentName
                    "caseSensitive" = $false
                }            
                "componentSelector"   = @{
                    "name"          = $name
                    "caseSensitive" = $false
                }
            }
            "rules"    = @(
                @{
                    "name"   = $name
                    "filter" = @{
                        "keyLike" = $searchTerm
                    }
                }
            )
        }

        $payload = $payload | ConvertTo-Json -Depth 3
          
        $APIUrl = ConstructAPIUrl  "/v1/components/rules"
        Invoke-RestMethod -Uri $APIUrl -Method Post -Headers $headers -Body $payload
        Write-Host "> Cloud Asset Rule added"
    }
    catch {
        if ($_.Exception.Response.StatusCode -eq "Conflict") {
            Write-Host " > Cloud Asset Rule" $name "already exists" 
        }
        else {
            Write-Host $_.Exception.Message
        }
    }
}


function CreateTeams {
    foreach ($team in $Teams) {
        try {
            $found = $false

            foreach ($pteam in $pteams) {
                if ($pteam.name -eq $team.TeamName) {
                    $found = $true
                    break
                }
            }

            if ($found -eq $false -and $team.TeamName -ne ""){
                Write-Host "Going to add" $team.TeamName "team."
                
                $payload = @{
                    "name" = $team.TeamName
                    "type" = "GENERAL"
                }

                $payload = $payload | ConvertTo-Json
            
                $APIUrl = ConstructAPIUrl  "/v1/teams"
                Invoke-RestMethod -Uri $APIUrl  -Method Post -Headers $headers -Body $payload
                Write-Host "+ Team" $team.TeamName " added."
            }
        }
        catch {
            if ($_.Exception.Response.StatusCode -eq "400") {
                Write-Host " > Team " $team.TeamName "already exists" 
            }
            else {
                Write-Host $_.Exception.Message
                Exit 1
            }
        }
    }
}
function PopulatePhoenixTeams 
{
    try 
    {
        Write-Host "Getting list of Phoenix Teams"
        $APIUrl = ConstructAPIUrl  "/v1/teams"
        $response = Invoke-RestMethod -Uri $APIUrl  -Method Get -Headers $headers
    
        return $response.content
    }
    catch {
        Write-Host $_.Exception.Message
        Exit 1
    }

}
function CreateTeamRules {
    foreach ($team in $Teams) {
        try {
            $found = $false

            foreach ($pteam in $pteams) {
                if ($pteam.name -eq $team.TeamName) {
                    $found = $true
                    break
                }
            }

            if ($found -eq $false -and $team.TeamName -ne "") {
                Write-Host "Team: " $team.name
                CreateTeamRule "pteam" $team.name $team.id
            }  
        }
        catch {
            Write-Host $_.Exception.Message
            Exit 1
        }
    }
}

function CreateTeamRule {
    param($tagName, $tagValue, $teamId)

    try {
        $payload = @{
            "match" = "ANY"
            "tags"  = @(
                @{
                    "key"   = $tagName
                    "value" = $tagValue
                }
            )
        }

        $payload = $payload | ConvertTo-Json -Depth 2
        
        $APIUrl = ConstructAPIUrl  ("/v1/teams/" + $teamId + "/components/auto-link/tags")
        Invoke-RestMethod -Uri $APIUrl  -Method Post -Headers $headers -Body $payload
        Write-Host " +" $tageName "rule added for :" $tagValue    
    }
    catch {
        if ($_.Exception.Response.StatusCode -eq "409") {
            Write-Host " > " $tagName " Rule" $tagValue "already exists" 
        }
        else {
            Write-Host $_.Exception.Message
            Exit 1
        }
    }
}

function AssignUsersToTeam {
    foreach ($pteam in $pTeams) {
        $teamMembers = GetPhoenixTeamMembers $pteam.id

        foreach ($team in $Teams) {
            if ($team.TeamName -eq $pteam.name) {
                Write-Host "[Team] " $pteam.name

                foreach ($m in $AllTeamAccess) {
                    $found = $false
                    foreach ($member in $teamMembers) {
                        if ($m -eq $member.email) {
                            $found = $true;
                            break;
                        }
                    }
                    if ( $found -eq $false) {
                        APICallAssignUsersToTeam $pteam.id $m
                    }
                }

                foreach ($teamMember in $team.TeamMembers) {

                    $found = $false

                    foreach ($member in $teamMembers) {
                        if ($member.email -eq $teamMember.EmailAddress) {
                            $found = $true;
                            break;
                        }
                    }

                    if ( $found -eq $false) {
                        APICallAssignUsersToTeam $pteam.id $teamMember.EmailAddress
                    }
                }

                foreach ($member in $teamMembers) {
                    $found = DoesMemberExist  $member.email $team $HiveStaff $AllTeamAccess

                    if ($found -eq $false) {
                        DeleteTeamMember $member.email $pteam.id
                    }
                }
            }
        }

        $HiveTeam = $HiveStaff | Where-Object { $_.Team.ToLower() -eq $pteam.name }

        if ($HiveTeam) {
            Write-Host "> Adding team lead " $HiveTeam.Lead " to team" $pteam.name
            APICallAssignUsersToTeam $pteam.id $HiveTeam.Lead

            foreach ($product in $HiveTeam.Product) {
                Write-Host "> Adding Product Owner " $product " to team" $pteam.name
                APICallAssignUsersToTeam $pteam.id $product
            }
        }
    }
}


function ConstructAPIUrl {
    param($endpoint)
    return $APIdomain + $endpoint
}

function APICallAssignUsersToTeam {
    param($teamID, $email)

    try {
        $payload = @{
            "users" = @(
                @{
                    "email" = $email
                }
            )
        }

        $payload = $payload | ConvertTo-Json

        $APIUrl = ConstructAPIUrl ("/v1/teams/$teamID/users")
        Invoke-RestMethod -Uri $APIUrl  -Method PUT  -Headers $headers -Body $payload
        Write-Host " + User $email added to team"
    }
    catch {
        if ($_.Exception.Response.StatusCode -eq "400") {
            Write-Host " ? Team Member assignment $email user hasn't logged in yet" 
        }

        elseif ($_.Exception.Response.StatusCode -eq "409") {
            Write-Host " - Team Member already assigned" $email 
        }

        else {
            Write-Host $_.Exception.Message
            Exit 1
        }
    }
}

function DeleteTeamMember {
    param($email, $teamId)
    try {
        $APIUrl = ConstructAPIUrl ("/v1/teams/$teamId/users/$email")
        Invoke-RestMethod -Uri $APIUrl  -Method DELETE -Headers $headers
        Write-Host "-Removed $email from team"
    }
    catch {
        Write-Host $_.Exception.Message
    }
}


function GetPhoenixComponents {

    $components = @()

    try {
        Write-Host "Getting list of Phoenix Components"
        $APIUrl = ConstructAPIUrl  "/v1/components"
        $response = Invoke-RestMethod -Uri $APIUrl  -Method GET -Headers $headers

        $components = $response.content

        $totalPages = $response.totalPages

        for ($i = 1; $i -lt $totalPages; $i++) {
            $APIUrl = ConstructAPIUrl  ("/v1/components/?pageNumber=" + $i)
            $response = Invoke-RestMethod -Uri $APIUrl  -Method GET -Headers $headers

            $components += $response.content
        }
    }
    catch {
        Write-Host $_.Exception
    }

    return $components
}

function GetPhoenixTeamMembers {
    param($TeamId)
   
    $teamMembers = @()
    try {
        $APIUrl = ConstructAPIUrl  ("/v1/teams/" + $TeamId + "/users")
        $response = Invoke-RestMethod -Uri $APIUrl  -Method GET -Headers $headers
    
        $teamMembers += $response
    }
    catch {
        Write-Host $_.Exception
    }

    return $teamMembers
}

function RemoveOldTags {
    param ($phoenixComponents)

    Write-Host "Removing old tags"

    foreach ($repo in $repos) {
        if ($repo.Domain -eq "FX") {
            $repo.Domain = "Foreign Exchange(FX)"
        }
    
        if ($repo.Subdomain -eq "FX") {
            $repo.Subdomain = "Foreign Exchange(FX)"
        }

        foreach ($repoOveride in $overrideList) {
            if ($repo.RepositoryName -eq $repoOveride.Key) {
                $repo.Subdomain = $repoOveride.Value   
            }
        }

        foreach ($component in $phoenixComponents) {
            if ($repo.RepositoryName -eq $component.name) 
            {
                Write-Host "Repo: " $repo.RepositoryName
                GetTagValue "domain" $component.tags $repo.Domain
                GetTagValue "subdomain" $component.tags $repo.Subdomain
                GetTagValue "pteam" $component.tags $repo.Team
            }
        }
    }
}

function GetTagValue {
    param (
        $tagName, $source, $expectedValue
    )

    foreach ($tag in $source) 
    {
        if ($tag.key -eq $tagName) 
        {
            if ($tag.value -ne $expectedValue)
            {  
                try 
                {  
                    $payload = @{
                        "action" = "delete"
                        "tags"        = @(
                            @{
                                "id" = $tag.id
                                "key"   = $tag.key
                                "value" = $tag.value
                            }
                        )
                    }

                    $payload = $payload | ConvertTo-Json -Depth 2

                    Write-Host "- Removing tag" $tag.key " " $tag.value

                    $APIUrl = ConstructAPIUrl  ("/v1/components/" + $component.id + "/tags") 
                    Invoke-RestMethod -Uri $APIUrl  -Method Patch -Headers $headers  -Body $payload
                }
                catch {
                    Write-Host  $component.name
                    Write-Host $_.Exception
                
                }
            }
        }
    }
}
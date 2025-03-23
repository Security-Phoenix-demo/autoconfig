if (Get-Module -ListAvailable -Name powershell-yaml) 
{
  Write-Host "Module exists"
} 
else 
{
  Install-Module powershell-yaml -Force -AllowClobber
}

function PoplulateRepositories
{
    param($ResouceFolder)


    $repos = @()

    if($null -eq $ResouceFolder)
    {
        Write-Host "Please supply path for the resources"
        return $repos
    }

    $BankingCore = Join-Path -Path $ResouceFolder -ChildPath "core-structure.yaml"

    $RawYaml = Get-Content -Path $BankingCore -Raw

    $ReposYaml = ConvertFrom-Yaml $RawYaml


    foreach ($row in $ReposYaml.DeploymentGroups[1].BuildDefinitions) 
    {
        $item = [PSCustomObject]@{
            RepositoryName = $row.RepositoryName
            Domain = $row.Domain
            Tier = $row.Tier
            Subdomain = $row.SubDomain
            Team = $row.TeamName
            BuildDefinitionName = $row.BuildDefinitionName
        }
        $repos += $item
    }

    

    return $repos
}

function PopulateSubdomainOwners 
{
    param($repos)

    $subdomains = @{}

    foreach($repo in $repos)
    {
        Write-Host $repo.RepositoryName

        if($subdomains.ContainsKey($repo.Subdomain) -eq $false)
        {
            $subdomains.Add($repo.Subdomain, @())
        }
        
        
        if($subdomains[$repo.Subdomain].Contains($repo.Team) -eq $false)
        {
            $subdomains[$repo.Subdomain] += $repo.Team
        }
        
    }

    return $subdomains
    
}

function PopulateTeams
{
   param($ResouceFolder)

   $Teams = @()

   try 
   {
        if($null -eq $ResouceFolder)
        {
            Write-Host "Please supply path for the resources"
            return $Teams
        }

        $TeamsFilePath = (Join-Path -Path $ResouceFolder -ChildPath "Teams")

        if((Test-Path -Path $TeamsFilePath) -eq $false)
        {
            Write-Host "Path does not exist " $TeamsFilePath
            Exit 1
        }

        $files =  Get-ChildItem -Path $TeamsFilePath -Filter *.yaml 

        foreach($teamFile in $files)
        {
            $RawYaml = Get-Content -Path $teamFile.FullName -Raw
            $Team = ConvertFrom-Yaml $RawYaml

            $found = $false
            foreach($t in $Teams)
            {
                if($t.TeamName -eq $Team.TeamName)
                {
                    $found = $true;
                    break;
                }
            }

            if($found -eq $false)
            {
                $Teams += $Team
            }
        } 
        
   }
   catch {
     Write-Host $_.Exception
   }

   return $Teams
}


function PopulateHives
{
    param($ResouceFolder)

    $Hives = @()

    try 
    {
        if($null -eq $ResouceFolder)
        {
            Write-Host "Please supply path for the resources"
            return $Hives
        }

        $yaml = Join-Path -Path $ResouceFolder -ChildPath "hives.yaml"
        
        if (-not (Test-Path -Path $yaml)) 
        {
            Write-Host "File not found or invalid path: $yaml"
            return $Hives
        }
        
        # Load the YAML file
        $yamlContent = ConvertFrom-Yaml (Get-Content -Path $yaml -Raw)
        
        # Iterate over the Hives
        foreach ($hive in $yamlContent.Hives) 
        {
            # Iterate over the Teams in each Hive
            foreach ($team in $hive.Teams) 
            {

                $products = @()
                if (![string]::IsNullOrEmpty($team.Product)) 
                {
                    # Split the Product field if it contains 'and'  @company.com
                    $products = ($team.Product -split ' and ') | ForEach-Object {
                        $_.ToLower().Replace(" ", ".") + "@company.com"
                    }
                }
                        # Create a PSCustomObject and add it to the $Hives array, please change @company.com
                        $hiveObject = [PSCustomObject]@{
                            'Lead'   = $team.Lead.ToLower().Replace(" ", ".") + "@company.com"
                            'Product' = $products
                            'Team'   = $team.Name
                        }

                        $Hives += $hiveObject
            }
        } 
    }
    catch 
    {
        Write-Host $_.Exception
    }

    return $Hives
}
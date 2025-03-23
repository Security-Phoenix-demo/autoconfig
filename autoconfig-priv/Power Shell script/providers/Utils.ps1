function PopulateDomains 
{
    param (
        $repos
    )

    $domains = @()

    foreach($repo in $repos)
    {
        foreach($dom in $repo.Domain)
        {
            if($domains.Contains($dom) -eq $false)
            {
                $domains+= $dom
            }
        }
    }

    return $domains
}

function GetSubdomains {
    param ($repos)

    $Subdomains = @()

    foreach($repo in $repos)
    {
        if (-not ($Subdomains | Where-Object { $_.Name -eq $repo.Subdomain }))
        {
            $item = [PSCustomObject]@{
                Name = $repo.Subdomain
                Domain = $repo.Domain
                Tier = $repo.Tier
            }

            $Subdomains += $item
        }
    }

    return $Subdomains 
}

function GetEnvironmentID
{
    param ($ApplicationEnvironments, $EnvironmentName)
    return ($ApplicationEnvironments | Where-Object { $_.name -eq $EnvironmentName -and $_.type -eq "ENVIRONMENT"}).id
}

function EnvironmentServiceExist
{
    param ($envID, $phoenixComponents, $servicename)

    foreach($component in $phoenixComponents)
    {
        if($component.applicationId -eq $envId)
        {
            if($component.name -eq $servicename)
            {
                return $true;
            }
        }
    }

    return $false
}

function CalculateCriticality {
    param (
        $tier
    )

    $criticality = 5

    if($tier -eq "0" )
    {
        $criticality = 10
    }

    if($tier -eq "1" )
    {
        $criticality = 9
    }

    elseif($tier -eq "2" )
    {
        $criticality = 8
    }

    elseif($tier -eq "3" )
    {
        $criticality = 7
    }

    elseif($tier -eq "4" )
    {
        $criticality = 6
    }

    return $criticality
    
}

function PopulateUsersWithAllTeamAccess {
    param (
        $Teams
    )
    Write-Host "Populating the users with all team Access"
    $allaccess = @()

    foreach($team in $Teams)
    {
        try {
            if($team.TeamName -eq "staffs" -or $team.TeamName -eq "principals" -or $team.TeamName -eq "directors")
            {
                foreach($member in $team.TeamMembers)
                {
                    $allaccess += $member.EmailAddress
                }
            }
        }
        catch {
            Write-Host $_.Exception.Message
            Exit 1
        }

    }
#this gives super user access to the ciso or who else wants access
    $allaccess += "ciso@company.com"

    return $allaccess
}

function DoesMemberExist
{
    param($email, $team, $HiveStaff, $AllTeamAccess)

    $found = $false;

    $overrideList = @("teamlead@ompany.com", "teamlead2@ompany.com")

    if($overrideList.Contains($email))
    {
        return $true
    }

    if($AllTeamAccess.Contains($email))
    {
        return $true
    }

    foreach($teamMember in $team.TeamMembers)
    {
        if($email -eq $teamMember.EmailAddress)
        {
            $found = $true;
            break;
        }
    }

    if($found -eq $false)
    {
       $hiveStaffMember =  $HiveStaff | Where-Object { $_.Lead -eq $email -or $_.Product -Contains $email } 

        if($hiveStaffMember)
        {
              $found = $true
        }
    }

    return $found
}
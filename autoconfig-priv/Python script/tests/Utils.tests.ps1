Describe 'PopulateDomains' {

    BeforeAll {
        $ErrorActionPreference = 'Stop'
        $sourceDir = resolve-path "$PSScriptRoot/../providers"
        . $sourceDir/Utils.ps1
    }


    It 'should return the null' {
        $repos = @()
        PopulateDomains $repos | Should -Be $null
    }

    It 'Should return domains' {

        $repos = @()

        for($i = 0; $i -lt 5; $i++)
        {
            $item = [PSCustomObject]@{
                RepositoryName = "Test"
                Domain = "Test" +$i
                Tier = 1
                Subdomain = "Test"
                Team = "Test"
            }
            $repos += $item
        }

        $output = PopulateDomains $repos 
        $output.count | Should -Be 5

    }

    It 'Should not add duplicate domains' {

        $repos = @()

        for($i = 0; $i -lt 5; $i++)
        {
            $item = [PSCustomObject]@{
                RepositoryName = "Test"
                Domain = "Test"
                Tier = 1
                Subdomain = "Test"
                Team = "Test"
            }
            $repos += $item
        }

        $output = PopulateDomains $repos 
        $output.count | Should -Be 1
    }

    It 'Should get an empty list of Subdomains' {
        
        $repos = @()
        
        $output = GetSubdomains $repos
        $output.count | Should -Be 0
    }


    It 'Should get a distinct list of Subdomains' {
        
        $repos = @()

        for($i = 0; $i -lt 5; $i++)
        {
            $item = [PSCustomObject]@{
                RepositoryName = "Test"
                Domain = "Test"
                Tier = 1
                Subdomain = "Test" +$i
                Team = "Test"
            }
            $repos += $item
        }

        $item = [PSCustomObject]@{
            RepositoryName = "Test"
            Domain = "Test"
            Tier = 1
            Subdomain = "Test0"
            Team = "Test"
        }

        $repos += $item

        
        $output = GetSubdomains $repos
        $output.count | Should -Be 5
    }

    It "No environments" {

        $ApplicationEnvironments = @() 

        $output = GetEnvironmentID $ApplicationEnvironments "Test"
        $output | Should -BeNullOrEmpty
    }

    It "Environment not found" {

        $ApplicationEnvironments = @() 

        for($i = 0; $i -lt 5; $i++)
        {

            $item = [PSCustomObject]@{
                id = $i
                type = "ENVIRONMENT"
                name = "Test" + $i
            }

            $ApplicationEnvironments += $item

        }

        $output = GetEnvironmentID $ApplicationEnvironments "PRODUCTION"
        $output | Should -BeNullOrEmpty
    }

    It "Should return Environment ID" {

        $ApplicationEnvironments = @() 

        for($i = 0; $i -lt 5; $i++)
        {

            $item = [PSCustomObject]@{
                id = $i
                type = "ENVIRONMENT"
                name = "Test" + $i
            }

            $ApplicationEnvironments += $item

        }

        $output = GetEnvironmentID $ApplicationEnvironments "Test2"
        $output | Should -Be "2"
    }

    It "Service Environment no components" {
        
        $phoenixComponents = @()

        $output = EnvironmentServiceExist 1 $phoenixComponents "TestService"
        $output | Should -BeFalse
    }


    It "Service Environment doesnt exist" {
        
        $phoenixComponents = @()

        for($i = 0; $i -lt 5; $i++)
        {

            $item = [PSCustomObject]@{
                applicationId = $i
                name = "TestService" + $i
            }

            $phoenixComponents += $item

        }

        $output = EnvironmentServiceExist 900 $phoenixComponents "TestService0"
        $output | Should -BeFalse
    }

    It "Service Environment exists" {
        
        $phoenixComponents = @()

        for($i = 0; $i -lt 5; $i++)
        {

            $item = [PSCustomObject]@{
                applicationId = 1
                name = "TestService" + $i
            }

            $phoenixComponents += $item

        }
        $output = EnvironmentServiceExist 1 $phoenixComponents "TestService2"
        $output | Should -BeTrue
    }

    It "Critiocality Test tier 0"    {
        $output = CalculateCriticality 0
        $output | Should -Be 10
    }

    It "Critiocality Test tier 2"    {
        $output = CalculateCriticality 2
        $output | Should -Be 8
    }

    It "Critiocality Test tier out of range"    {
        $output = CalculateCriticality 99
        $output | Should -Be 5
    }

    It "Team Member Exists" {

        $team = @()

        $item = [PSCustomObject]@{
            TeamMembers = @()
        }

        for($i = 0; $i -lt 10; $i++)
        {
            $member = [PSCustomObject]@{
                name = "test " +$i
                EmailAddress = "test" +$i + "@clear.bank"
            }

            $item.TeamMembers += $member
        }

        $team += $item

        $HiveStaff = @{}

        $output = DoesMemberExist "test1@clear.bank" $team $HiveStaff @()
        $output | Should -BeTrue
    }

    It "All Access staff Exists"    {
        $team = @()

        $item = [PSCustomObject]@{
            TeamMembers = @()
        }

        for($i = 0; $i -lt 1; $i++)
        {
            $member = [PSCustomObject]@{
                name = "test " +$i
                EmailAddress = "test" +$i + "@clear.bank"
            }

            $item.TeamMembers += $member
        }

        $team += $item

        $HiveStaff = @{}

        $AllTeamAccess = @("test9@clear.bank", "test10@clear.bank")

        $output = DoesMemberExist "test10@clear.bank" $team $HiveStaff $AllTeamAccess
        $output | Should -BeTrue
    }

    It "Team Member Doesnt Exist" {

        $team = @()

        $item = [PSCustomObject]@{
            TeamMembers = @()
        }

        for($i = 0; $i -lt 5; $i++)
        {
            $member = [PSCustomObject]@{
                name = "test " +$i
                EmailAddress = "test" +$i + "@clear.bank"
            }

            $item.TeamMembers += $member
        }

        $team += $item

        $HiveStaff = @{}

        $output = DoesMemberExist "test10@clear.bank" $team $HiveStaff @()
        $output | Should -BeFalse
    }

    It "Team Member Product Staff Exists" {

        $team = @()

        $item = [PSCustomObject]@{
            TeamMembers = @()
        }

        for($i = 0; $i -lt 5; $i++)
        {
            $member = [PSCustomObject]@{
                name = "test " +$i
                EmailAddress = "test" +$i + "@clear.bank"
            }

            $item.TeamMembers += $member
        }

        $team += $item

        $HiveStaff = @()


        $products = @("test10@clear.bank", "test2@clear.bank")

        $hiveObject = [PSCustomObject]@{
            'Lead'   = "test1@clear.bank"
            'Product' = $products
            'Team'   = "TestTeam"
        }

        $HiveStaff += $hiveObject


        $output = DoesMemberExist "test10@clear.bank" $team $HiveStaff @()
        $output | Should -BeTrue
    }

    It "Team Member Product Staff Doesnt Exists" {

        $team = @()

        $item = [PSCustomObject]@{
            TeamMembers = @()
        }

        for($i = 0; $i -lt 5; $i++)
        {
            $member = [PSCustomObject]@{
                name = "test " +$i
                EmailAddress = "test" +$i + "@clear.bank"
            }

            $item.TeamMembers += $member
        }

        $team += $item

        $HiveStaff = @()


        $products = @("test10@clear.bank", "test2@clear.bank")

        $hiveObject = [PSCustomObject]@{
            'Lead'   = "test1@clear.bank"
            'Product' = $products
            'Team'   = "TestTeam"
        }

        $HiveStaff += $hiveObject


        $output = DoesMemberExist "test999@clear.bank" $team $HiveStaff @()
        $output | Should -BeFalse
    }

    It "PopulateUsersWithAllTeamAccess" {

        $teams = @()

        $staffs = [PSCustomObject]@{
            TeamName = "staffs"
            TeamMembers = @()
        }

        $principals = [PSCustomObject]@{
            TeamName = "prinicpals"
            TeamMembers = @()
        }

        for($i = 0; $i -lt 5; $i++)
        {
            $staffs.TeamMembers += [PSCustomObject]@{
                Name = "Test"
                EmailAddress = "test" +$i + "@clear.bank" 
            }

            $principals.TeamMembers += [PSCustomObject]@{
                Name = "P"
                EmailAddress = "p" +$i + "@clear.bank" 
            }
        }

        $teams += $staffs
        $teams += $principals

        $output = PopulateUsersWithAllTeamAccess $teams
        $output.count | Should -Be 6
    }
}

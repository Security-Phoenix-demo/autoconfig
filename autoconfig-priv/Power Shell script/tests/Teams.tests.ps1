Describe 'Teams' {

    BeforeAll {
        $ErrorActionPreference = 'Stop'
        $sourceDir = resolve-path "$PSScriptRoot/../providers"
        . $sourceDir/YamlHelper.ps1
    }

    It 'should return the null' {
      
        $output = PopulateTeams $null
        $output | Should -BeNullOrEmpty
    }

    It 'Should return unique teams Static test file' {
        $ResourcePath = Join-Path -Path $PSScriptRoot -ChildPath "/Resources"
        $output = PopulateTeams $ResourcePath
        $output.count | Should -Be 4
    }

    It 'Should have team members Static test file Static test file' {
        $ResourcePath = Join-Path -Path $PSScriptRoot -ChildPath "/Resources"
        $output = PopulateTeams $ResourcePath
        $output[0].TeamMembers.Count | Should -Be 8
    }


    It 'Subdomain Should have teams Static test file' {
        $ResourcePath =  Join-Path -Path $PSScriptRoot -ChildPath "/Resources"
        $repos = PoplulateRepositories  $ResourcePath
        $output = PopulateSubdomainOwners $repos
        $output["Sterling Accounts"].Count | Should -Be 3
    }    

    It 'Use Real Release Data' {

        $ResourcePath = Join-Path -Path $PSScriptRoot -ChildPath "../Resources"

        $output = PopulateTeams  $ResourcePath
        $output.count | Should -BeGreaterThan 0
    }
}

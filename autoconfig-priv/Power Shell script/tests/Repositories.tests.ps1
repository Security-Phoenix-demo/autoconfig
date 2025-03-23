Describe 'Repositories' {

    BeforeAll {
        $ErrorActionPreference = 'Stop'
        $sourceDir = resolve-path "$PSScriptRoot/../providers"
        . $sourceDir/YamlHelper.ps1
    }

    It 'should return the null' {
      
        $output = PoplulateRepositories $null
        $output | Should -BeNullOrEmpty
    }

    It 'Should contain Repos Static test file' {
        $ResourcePath = Join-Path -Path $PSScriptRoot -ChildPath "/Resources"
        
        $output = PoplulateRepositories  $ResourcePath
        $output.Count | Should -Be 904
    }

    It 'Should contain Repos Real BankingCore' {
        $ResourcePath = Join-Path -Path $PSScriptRoot -ChildPath "../Resources"
        
        $output = PoplulateRepositories  $ResourcePath
        $output.Count | Should -BeGreaterThan 0
    }
}

Describe 'Hives' {

    BeforeAll {
        $ErrorActionPreference = 'Stop'
        $sourceDir = resolve-path "$PSScriptRoot/../providers"
        . $sourceDir/YamlHelper.ps1
    }

    It 'should return the null' {
      
        $output = PopulateHives $null
        $output | Should -BeNullOrEmpty
    }

    It 'Should return null when the resource path does not exist' {
        $ResourcePath = Join-Path -Path $PSScriptRoot -ChildPath "/NonExistentPath"
        
        $output = PopulateHives $ResourcePath
        $output | Should -BeNullOrEmpty
    }

    It 'Should contain specific team in the output' {
        $ResourcePath = Join-Path -Path $PSScriptRoot -ChildPath "/Resources"
        
        $output = PopulateHives $ResourcePath
        $specificTeam = $output | Where-Object { $_.Team -eq 'narwhal' }
        $specificTeam | Should -Not -BeNullOrEmpty
    }

    It 'Should not contain non-existent team in the output' {
        $ResourcePath = Join-Path -Path $PSScriptRoot -ChildPath "/Resources"
        
        $output = PopulateHives $ResourcePath
        $nonExistentTeam = $output | Where-Object { $_.Team -eq 'nonExistentTeam' }
        $nonExistentTeam | Should -BeNullOrEmpty
    }

    It 'Should contain Repos Static test file' {
        $ResourcePath = Join-Path -Path $PSScriptRoot -ChildPath "/Resources"
        
        $output = PopulateHives  $ResourcePath
        $output.Count | Should -Be 46

        $narwhalTeam = $output | Where-Object { $_.Team -eq 'narwhal' }
        $narwhalTeam.Product.Count | Should -Be 3
    }

    It 'Should contain COMPANY Email' {
        $ResourcePath = Join-Path -Path $PSScriptRoot -ChildPath "/Resources"
        
        $output = PopulateHives  $ResourcePath
        $output | ForEach-Object {
            $_.Lead | Should -Match "@clear.bank$"
        }
    }
}

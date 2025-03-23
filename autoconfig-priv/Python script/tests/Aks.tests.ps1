Describe 'AKS' {

    BeforeAll {
        $ErrorActionPreference = 'Stop'
        $sourceDir = resolve-path "$PSScriptRoot/../providers"
        . $sourceDir/Aks.ps1
    }

    It 'Get Clusters should be NULL' {
      
        $output = GetClusters $null
        $output | Should -BeNullOrEmpty
    }

    It 'Get Clusters should not be null' {
      
        $output = GetClusters "team-ocelot"
        $output.Count | Should -BeGreaterThan 0
    }

    It 'Get Cluster Images should not be null' {
        
        $cluster = [PSCustomObject]@{
            Name = "cbuk-core-testoce-preview-aks-uksouth"
            ResourceGroup = "cbuk-core-testoce-preview-aks-uksouth"
        }

        $output = GetClusterImages $cluster
        $output.Count | Should -BeGreaterThan 0
        $output[0].ImageName | Should -Not -BeNullOrEmpty
    }

    It 'Returns an array of subscriptions' {
        $output = GetSubscriptions
        $output.Count | Should -BeGreaterThan 0
    }

    It "returns an object with correct properties" {
        $container = "registry/image:tag"
        $team = "team1"
        $repo = "repo1"
        $cluster = @{
            SubscriptionName = "subName"
            SubscriptionId = "subId"
        }

        $result = createContainerResult $container $team $repo $cluster

        $result.Register | Should -Be "registry"
        $result.ImageName | Should -Be "image"
        $result.ContainerUrl | Should -Be "registry/image"
        $result.TeamLabel | Should -Be "team1"
        $result.Repo | Should -Be "repo1"
        $result.SubscriptionName | Should -Be "subName"
        $result.SubscriptionId | Should -Be "subId"
    }
}

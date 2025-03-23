function GetSubscriptions {

    $subscriptions = @()

    try {
        Write-Host "Getting subscriptions..."
        $subscriptions = az account subscription list --query "[].displayName" -o tsv | Where-Object { $_ -match "prod" }
        Write-Host "Subscriptions: " $subscriptions.Count
    }
    catch {
       Write-Host "Error: " $_.Exception.Message
    }

   return  $subscriptions
}

function GetClusters {
    param (
        $subscription
    )

    if (!$subscription) {
        return $null
    }

    $clusters = @()

    try 
    {
        Write-Host "Subscription: " $subscription

        az account set --subscription $subscription
        $clusters = az aks list --query "[].{Name:name, ResourceGroup:resourceGroup}" | ConvertFrom-Json

        # Add subscription details to each cluster
        foreach ($cluster in $clusters) {
            $cluster | Add-Member -NotePropertyName SubscriptionName -NotePropertyValue $subscription
            $cluster | Add-Member -NotePropertyName SubscriptionId -NotePropertyValue (az account show --query id -o tsv)
        }

        Write-Host "Clusters: " $clusters.Count
    }
    catch 
    {
        Write-Host "Error: " $_.Exception.Message
    }

    return $clusters
}

function createContainerResult {
    param($container, $team, $repo, $cluster)

    $containerParts = $container.split("/")
    $containerPartsColon = $container.split(":")
    
    $register  = $containerParts[0]
    $imageName = $containerPartsColon[0].split("/")[-1]
    $containerUrl = $containerPartsColon[0]
    $subscriptionName = $cluster.SubscriptionName
    $subscriptionId = $cluster.SubscriptionId
    
    return  New-Object PSObject -Property @{
        Register    = $register
        ImageName   = $imageName
        ContainerUrl = $containerUrl
        TeamLabel   = $team
        Repo        = $repo
        SubscriptionName = $subscriptionName
        SubscriptionId = $subscriptionId
    }
}


function GetClusterImages {
    param (
        $cluster
    )

    $results = @()

    try {
        
        Write-Host "Cluster: " $cluster.Name
        az aks get-credentials --resource-group $cluster.ResourceGroup --name $cluster.Name --overwrite-existing > $null
        kubelogin convert-kubeconfig -l azurecli > $null

        $cronJobs = kubectl get cronjobs -A -o json | ConvertFrom-Json

        foreach ($cronJob in $cronJobs.items) {
            # Get the image name for each container in the cron job
            foreach ($container in $cronJob.spec.jobTemplate.spec.template.spec.containers) {

                $newObject = createContainerResult $container.image $cronJob.metadata.labels.team $cronJob.metadata.labels.git_repository $cluster

                # Only add if item not already in results
                if ($results -notcontains $newObject) {
                    $results += $newObject

                    Write-Host "+" $newObject.ImageName
                }
            }
        }

        $pods = kubectl get pods -A --context $cluster.Name -o json | ConvertFrom-Json

        foreach ($pod in $pods.items) {   

            $container = $pod.spec.containers[0]

            $teamLabel = if ($labels.PSObject.Properties.Name -contains 'team') { $labels.team } else { $null }
            $labels = $pod.metadata.labels
            $git_repository = if ($labels.PSObject.Properties.Name -contains 'git_repository') { $labels.git_repository } else { $labels.chart }

            $newObject = createContainerResult $container.image $teamLabel $git_repository $cluster

            # Only add if item not already in results
            if ($results -notcontains $newObject) {
                $results += $newObject

                Write-Host "+" $newObject.ImageName
            }
        }
    }
    catch {
        Write-Host "Error: " $_.Exception.Message
    }
    Write-Host "Results: " $results.Count " images found."
    return $results
    
}
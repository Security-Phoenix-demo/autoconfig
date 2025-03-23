import subprocess
import json


def run_command(command):
    """Helper function to run shell commands and return the output."""
    try:
        result = subprocess.check_output(command, shell=True, text=True)
        return result.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error: {str(e)}")
        return None


def get_subscriptions():
    """Get a list of subscriptions that match 'prod'."""
    subscriptions = []

    try:
        print("Getting subscriptions...")
        result = run_command("az account subscription list --query '[].displayName' -o tsv")
        if result:
            subscriptions = [sub for sub in result.splitlines() if "prod" in sub]
        print(f"Subscriptions: {len(subscriptions)}")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    return subscriptions


def get_clusters(subscription):
    """Get a list of AKS clusters for a specific subscription."""
    if not subscription:
        return None

    clusters = []

    try:
        print(f"Subscription: {subscription}")
        run_command(f"az account set --subscription {subscription}")
        result = run_command("az aks list --query '[].{Name:name, ResourceGroup:resourceGroup}'")
        clusters = json.loads(result) if result else []

        # Add subscription details to each cluster
        subscription_id = run_command("az account show --query id -o tsv")
        for cluster in clusters:
            cluster['SubscriptionName'] = subscription
            cluster['SubscriptionId'] = subscription_id

        print(f"Clusters: {len(clusters)}")
    except Exception as e:
        print(f"Error: {str(e)}")

    return clusters


def create_container_result(container, team, repo, cluster):
    """Create a result object for the container image."""
    container_parts = container.split("/")
    container_parts_colon = container.split(":")
    
    register = container_parts[0]
    image_name = container_parts_colon[0].split("/")[-1]
    container_url = container_parts_colon[0]
    subscription_name = cluster['SubscriptionName']
    subscription_id = cluster['SubscriptionId']

    return {
        'Register': register,
        'ImageName': image_name,
        'ContainerUrl': container_url,
        'TeamLabel': team,
        'Repo': repo,
        'SubscriptionName': subscription_name,
        'SubscriptionId': subscription_id
    }


def get_cluster_images(cluster):
    """Get a list of container images for a given AKS cluster."""
    results = []

    try:
        print(f"Cluster: {cluster['Name']}")
        run_command(f"az aks get-credentials --resource-group {cluster['ResourceGroup']} --name {cluster['Name']} --overwrite-existing")
        run_command("kubelogin convert-kubeconfig -l azurecli")

        cron_jobs_result = run_command("kubectl get cronjobs -A -o json")
        cron_jobs = json.loads(cron_jobs_result)['items'] if cron_jobs_result else []

        for cron_job in cron_jobs:
            for container in cron_job['spec']['jobTemplate']['spec']['template']['spec']['containers']:
                new_object = create_container_result(container['image'],
                                                     cron_job['metadata']['labels'].get('team'),
                                                     cron_job['metadata']['labels'].get('git_repository'),
                                                     cluster)

                if new_object not in results:
                    results.append(new_object)
                    print(f"+ {new_object['ImageName']}")

        pods_result = run_command(f"kubectl get pods -A --context {cluster['Name']} -o json")
        pods = json.loads(pods_result)['items'] if pods_result else []

        for pod in pods:
            container = pod['spec']['containers'][0]
            labels = pod['metadata']['labels']
            team_label = labels.get('team')
            git_repository = labels.get('git_repository', labels.get('chart'))

            new_object = create_container_result(container['image'], team_label, git_repository, cluster)

            if new_object not in results:
                results.append(new_object)
                print(f"+ {new_object['ImageName']}")

    except Exception as e:
        print(f"Error: {str(e)}")

    print(f"Results: {len(results)} images found.")
    return results
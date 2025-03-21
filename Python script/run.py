import time
import csv
import os
from providers.Phoenix import get_phoenix_components, populate_phoenix_teams, get_auth_token , create_teams, create_team_rules, assign_users_to_team, populate_applications_and_environments, create_environment, add_environment_services, add_cloud_asset_rules, add_thirdparty_services, create_applications, create_deployments, create_autolink_deployments, create_teams_from_pteams, create_components_from_assets
import providers.Phoenix as phoenix_module
from providers.Utils import populate_domains, get_subdomains, populate_users_with_all_team_access
from providers.YamlHelper import populate_repositories, populate_teams, populate_hives, populate_subdomain_owners, populate_environments_from_env_groups, populate_all_access_emails, populate_applications
#from providers.Aks import get_subscriptions, get_clusters, get_cluster_images

# Global Variables
resource_folder = os.path.join(os.path.dirname(__file__), 'Resources')
client_id = ""
client_secret = ""
access_token = ""
action_teams = ""
action_code = True
action_cloud = True
action_deployment = True
action_autolink_deploymentset = True
action_autocreate_teams_from_pteam = True
action_create_components_from_assets = True

# Handle command-line arguments or prompt for input
import sys
args = sys.argv[1:]

print("\n[Configuration]")
print(f"Arguments provided: {len(args)}")

if len(args) == 10:
    client_id = args[0]
    client_secret = args[1]
    phoenix_module.APIdomain = args[9]
    if args[2].lower() == "false":
        action_teams = False

    if args[3].lower() == "false":
        action_code = False

    if args[4].lower() == "false":
        action_cloud = False

    if args[5].lower() == "false":
        action_deployment = False
    
    if args[6].lower() == "false":
        action_autolink_deploymentset = False

    if args[7].lower() == 'false':
        action_autocreate_teams_from_pteam = False

    if args[8].lower() == 'false':
        action_create_components_from_assets = False

    print("\n[Actions Enabled]")
    print(f"✓ Teams: {action_teams}")
    print(f"✓ Code: {action_code}")
    print(f"✓ Cloud: {action_cloud}")
    print(f"✓ Deployment: {action_deployment}")
    print(f"✓ Autolink deploymentset: {action_autolink_deploymentset}")
    print(f"✓ Auto-create teams from pteam: {action_autocreate_teams_from_pteam}")
    print(f"✓ Create components from assets: {action_create_components_from_assets}")
else:
    print("\n[Manual Configuration]")
    client_id = input("Please enter clientID: ")
    client_secret = input("Please enter clientSecret: ")

environments = populate_environments_from_env_groups(resource_folder)

# Populate data from various resources
print("\n[Loading Resources]")
repos = populate_repositories(resource_folder)
domains = populate_domains(repos)
teams = populate_teams(resource_folder)
hive_staff = populate_hives(resource_folder)
subdomain_owners = populate_subdomain_owners(repos)
subdomains = get_subdomains(repos)
access_token = get_auth_token(client_id, client_secret)
pteams = populate_phoenix_teams(access_token)
defaultAllAccessAccounts = populate_all_access_emails(resource_folder)
all_team_access = populate_users_with_all_team_access(teams, defaultAllAccessAccounts)
applications = populate_applications(resource_folder)

# Display teams
print("\n[Teams]")
for team in teams:
    try:
        if "Team" in team['AzureDevopsAreaPath']:
            team['TeamName'] = team['AzureDevopsAreaPath'].split("Team")[1].strip()
            print(f"✓ {team['TeamName']}")
    except Exception as e:
        print(f"✗ Error processing team: {e}")

# Display domains and repos
print("\n[Domains]")
for domain in domains:
    print(f"✓ {domain}")

print("\n[Repositories]")
for repo in repos:
    print(f"✓ {repo['RepositoryName']}")

# Get authentication token
access_token = get_auth_token(client_id, client_secret)

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

phoenix_components = get_phoenix_components(access_token)
pteams = populate_phoenix_teams(access_token)
new_pteams = []

app_environments = populate_applications_and_environments(headers)

# Stopwatch logic
start_time = time.time()

# Team actions
if action_teams:
    print("\n[Teams Actions]")
    all_team_access = populate_users_with_all_team_access(teams, defaultAllAccessAccounts)
    new_pteams = create_teams(teams, pteams, access_token)
    create_team_rules(teams, pteams, access_token)
    assign_users_to_team(pteams, new_pteams, teams, all_team_access, hive_staff, access_token)

    elapsed_time = time.time() - start_time
    print(f"✓ Teams processing completed in {elapsed_time:.2f}s")
    start_time = time.time()

# Cloud actions
if action_cloud:
    print("\n[Cloud Actions]")
    for environment in environments:
        if not any(env['name'] == environment['Name'] and env.get('type') == "ENVIRONMENT" for env in app_environments):
            print(f"Creating environment: {environment['Name']}")
            create_environment(environment, headers)

    print("\n[Cloud Services]")
    add_environment_services(repos, subdomains, environments, app_environments, phoenix_components, subdomain_owners, teams, access_token)
    print(f"✓ Cloud services completed in {time.time() - start_time:.2f}s")
    
    print("\n[Cloud Asset Rules]")
    add_cloud_asset_rules(repos, access_token)
    print(f"✓ Cloud asset rules completed in {time.time() - start_time:.2f}s")
    
    print("\n[Third Party Rules]")
    add_thirdparty_services(phoenix_components, app_environments, subdomain_owners, headers)
    
    elapsed_time = time.time() - start_time
    print(f"✓ Cloud processing completed in {elapsed_time:.2f}s")
    start_time = time.time()

if action_code:
    print("\n[Code Actions]")
    create_applications(applications, app_environments, phoenix_components, headers)
    print(f"✓ Code processing completed in {time.time() - start_time:.2f}s")
    start_time = time.time()

if action_deployment:
    print("\n[Deployment Actions]")
    create_deployments(applications, environments, app_environments, headers)
    print(f"✓ Deployment processing completed in {time.time() - start_time:.2f}s")
    start_time = time.time()

if action_autolink_deploymentset:
    print("\n[Autolink Deployment Set]")
    create_autolink_deployments(applications, environments, headers)
    print(f"✓ Autolink deployment set completed in {time.time() - start_time:.2f}s")
    start_time = time.time()

if action_autocreate_teams_from_pteam:
    print("\n[Auto-Create Teams from PTeam]")
    create_teams_from_pteams(applications, environments, pteams, access_token)
    print(f"✓ Team creation from pteam completed in {time.time() - start_time:.2f}s")
    start_time = time.time()

if action_create_components_from_assets:
    print("\n[Create Components from Assets]")
    create_components_from_assets(app_environments, phoenix_components, headers)
    print(f"✓ Component creation from assets completed in {time.time() - start_time:.2f}s")

print("\n[Process Complete]")
print("✓ All operations finished successfully")

# Code actions
# if action_code:
#     cluster_images = []

#     file = "AKSImages.csv"
#     subscriptions = get_subscriptions()

#     for subscription in subscriptions:
#         print(subscription['Name'])
#         clusters = get_clusters(subscription)
#         for cluster in clusters:
#             cluster_images.extend(get_cluster_images(cluster))

#         print(f"Total Images Tally: {len(cluster_images)}")

#         if cluster_images:
#             with open(file, 'w', newline='') as csvfile:
#                 writer = csv.writer(csvfile)
#                 writer.writerow(cluster_images)

#         time.sleep(5)

#     if os.path.exists(file):
#         print(f"Processing {file}")
#         with open(file, 'r') as csvfile:
#             csv_data = csv.DictReader(csvfile)

#             service_lookup = {"workload-identity-webhook": "Compute"}

#             for row in csv_data:
#                 found = False
#                 if row['Repo']:
#                     print(f"Row: {row['Repo']}")
#                     if row['Repo'] in service_lookup:
#                         environment = next((env for env in environments if row['SubscriptionId'] in env['CloudAccounts']), None)
#                         if environment:
#                             print(f"Adding container rule for {row['ContainerUrl']} in {environment['Name']}")
#                             found = True

#                     if not found:
#                         repo = next((r for r in repos if r['RepositoryName'] == row['Repo']), None)
#                         if repo:
#                             print(f"Match found. Subdomain: {repo['Subdomain']}")
#                             environment = next((env for env in environments if row['SubscriptionId'] in env['CloudAccounts']), None)
#                             if environment:
#                                 print(f"Environment found: {environment['Name']}")
#                                 print(f"Adding container rule for {row['ContainerUrl']} in {environment['Name']}")
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
print("LEGACY MODE YOU ARE CURRENTLY RUNNING IS NOT LONGER MAINTAINED. PLEASE MIGRATE TO run-phx.py")
print("Arguments supplied:", len(args))

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

    print(f"Teams: {action_teams}, Code: {action_code}, Cloud: {action_cloud}, Deployment: {action_deployment}, Autolink deploymentset: {action_autolink_deploymentset}")
else:
    client_id = input("Please enter clientID: ")
    client_secret = input("Please enter clientSecret: ")

environments = populate_environments_from_env_groups(resource_folder)

# Populate data from various resources
repos = populate_repositories(resource_folder)
domains = populate_domains(repos)
teams = populate_teams(resource_folder)
hive_staff = populate_hives(resource_folder)  # List of Hive team staff
subdomain_owners = populate_subdomain_owners(repos)
subdomains = get_subdomains(repos)
access_token = get_auth_token(client_id, client_secret)
pteams = populate_phoenix_teams(access_token)  # Pre-existing Phoenix teams
defaultAllAccessAccounts = populate_all_access_emails(resource_folder)
all_team_access = populate_users_with_all_team_access(teams, defaultAllAccessAccounts)  # Populate users with full team access
applications = populate_applications(resource_folder)

# Display teams
print("[Teams]")
for team in teams:
    try:
        if "Team" in team['AzureDevopsAreaPath']:
            team['TeamName'] = team['AzureDevopsAreaPath'].split("Team")[1].strip()
            print(team['TeamName'])
    except Exception as e:
        print(f"Error: {e}")

# Display domains and repos
print("\n[Domains]")
print(domains)

print("\n[Repos]")
for repo in repos:
    print(repo['RepositoryName'])

# Get authentication token
access_token = get_auth_token(client_id, client_secret)

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

phoenix_components = get_phoenix_components(access_token)
pteams = populate_phoenix_teams(access_token)
# pteams created in this run
new_pteams = []

app_environments = populate_applications_and_environments(headers)  # Should be populated using the equivalent PopulateApplicationsAndEnvironments

# Stopwatch logic
start_time = time.time()

# Team actions
if action_teams:
    print("Performing Teams Actions")
    all_team_access = populate_users_with_all_team_access(teams, defaultAllAccessAccounts)
    new_pteams = create_teams(teams, pteams, access_token)
    create_team_rules(teams, pteams, access_token)
    assign_users_to_team(pteams, new_pteams, teams, all_team_access, hive_staff, access_token)

    elapsed_time = time.time() - start_time
    print(f"[Diagnostic] [Teams] Time Taken: {elapsed_time}")
    start_time = time.time()

# Cloud actions
if action_cloud:
    print("Performing Cloud Actions")
    for environment in environments:
        if not any(env['name'] == environment['Name'] and env.get('type') == "ENVIRONMENT" for env in app_environments):
            # Create environments as needed
            print(f"Creating environment: {environment['Name']}")
            create_environment(environment, headers)

    # Perform cloud services
    add_environment_services(repos, subdomains, environments, app_environments, phoenix_components, subdomain_owners, teams, access_token)
    print("[Diagnostic] [Cloud] Time Taken:", time.time() - start_time)
    print("Starting Cloud Asset Rules")
    add_cloud_asset_rules(repos, access_token)
    print("[Diagnostic] [Cloud] Time Taken:", time.time() - start_time)
    print("Starting Third Party Rules")
    add_thirdparty_services(phoenix_components, app_environments, subdomain_owners, headers)
    
    elapsed_time = time.time() - start_time
    print(f"[Diagnostic] [Cloud] Time Taken: {elapsed_time}")
    start_time = time.time()

if action_code:
    print("Performing Code Actions")
    create_applications(applications, app_environments, phoenix_components, headers)
        
    print(f"[Diagnostic] [Code] Time Taken: {time.time() - start_time}")
    start_time = time.time()

if action_deployment:
    print("Performing deployment action")
    create_deployments(applications, environments, app_environments, headers)
    print(f"[Diagnostic] [Deployment] Time Taken: {time.time() - start_time}")
    start_time = time.time()

if action_autolink_deploymentset:
    print("Performing autolink deployment set action")
    create_autolink_deployments(applications, environments, headers)
    print(f"[Diagnostic] [Autolink deploymentset] Time Taken: {time.time() - start_time}")
    start_time = time.time()

if action_autocreate_teams_from_pteam:
    print("Performing autocreate teams from pteam")
    create_teams_from_pteams(applications, environments, pteams, access_token)
    print(f"[Diagnostic] [Autocreate teams from pteam] Time Taken: {time.time() - start_time}")
    start_time = time.time()

if action_create_components_from_assets:
    print("Performing create components/services from assets")
    create_components_from_assets(app_environments, phoenix_components, headers)
    print(f"[Diagnostic] [Create components/services from assets] Time Taken: {time.time() - start_time}")



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
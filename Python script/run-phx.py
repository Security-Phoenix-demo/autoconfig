import time
import os
import argparse
from itertools import chain
from providers.Phoenix import get_phoenix_components, populate_phoenix_teams, get_auth_token , create_teams, create_team_rules, assign_users_to_team, populate_applications_and_environments, create_environment, add_environment_services, add_cloud_asset_rules, add_thirdparty_services, create_applications, create_deployments, create_autolink_deployments, create_teams_from_pteams, create_components_from_assets, create_user_for_application, load_users_from_phoenix
import providers.Phoenix as phoenix_module
from providers.Utils import populate_domains, get_subdomains, populate_users_with_all_team_access
from providers.YamlHelper import populate_repositories, populate_teams, populate_hives, populate_subdomain_owners, populate_environments_from_env_groups, populate_all_access_emails, populate_applications, load_flag_for_create_users

# Global Variables
resource_folder = os.path.join(os.path.dirname(__file__), 'Resources')

def perform_actions(args):  

    client_id = args.client_id
    client_secret = args.client_secret
    if (args.api_domain):
        phoenix_module.APIdomain = args.api_domain
    action_teams = args.action_teams == 'true'
    action_code = args.action_code == 'true'
    action_cloud = args.action_cloud == 'true'
    action_deployment = args.action_deployment == 'true'
    action_autolink_deploymentset = args.action_autolink_deploymentset == 'true'
    action_autocreate_teams_from_pteam = args.action_autocreate_teams_from_pteam == 'true'
    action_create_components_from_assets = args.action_create_components_from_assets == 'true'

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

    app_environments = populate_applications_and_environments(headers)

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

        if load_flag_for_create_users(resource_folder):
            print("Creating users from Environment 'Responsable' field")
            current_users_emails = list(u.get("email") for u in load_users_from_phoenix(headers))
            print(f"Users in Phoenix {current_users_emails}")
            created_users_emails = []
            for env in environments:
                created_user = create_user_for_application(current_users_emails, created_users_emails, env.get('Responsable'), headers)
                if created_user:
                    created_users_emails.append(created_user.get("email"))
        
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
        if load_flag_for_create_users(resource_folder):
           print("Creating users from Application 'Responsable' field")
           current_users_emails = list(u.get("email") for u in load_users_from_phoenix(headers))
           created_users_emails = []
           for app in applications:
               created_user = create_user_for_application(current_users_emails, created_users_emails, app.get('Responsable'), headers)
               if created_user:
                   created_users_emails.append(created_user.get("email"))
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process input arguments.")

    # Add arguments
    parser.add_argument("client_id", type=str, help="Client ID")
    parser.add_argument("client_secret", type=str, help="Client Secret")
    parser.add_argument("--api_domain", type=str, default=phoenix_module.APIdomain, required=False, help="Phoenix API domain")
    parser.add_argument("--action_teams", type=str, default="false", 
                        required=False, help="Flag triggering teams action")
    parser.add_argument("--action_code", type=str, default="false", 
                        required=False, help="Flag triggering code action")
    parser.add_argument("--action_cloud", type=str, default="false", 
                        required=False, help="Flag triggering cloud action")
    parser.add_argument("--action_deployment", type=str, default="false", 
                        required=False, help="Flag triggering deployment action")
    parser.add_argument("--action_autolink_deploymentset", type=str, default="false", 
                        required=False, help="Flag triggering autolink deploymentset action")
    parser.add_argument("--action_autocreate_teams_from_pteam", type=str, default="false",
                         required=False, help="Flag triggering autocreate teams from pteam action")
    parser.add_argument("--action_create_components_from_assets", type=str, default="false", 
                        required=False, help="Flag triggering create components from assets action")
    parser.add_argument("--verify", type=str, default="false", 
                        required=False, help="Flag indicating whether changes should be only printed (when True) or applied (when False)")

    
    # Parse arguments
    args = parser.parse_args()
    
    perform_actions(args)
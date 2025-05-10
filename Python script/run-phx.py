import time
import os
import argparse
import traceback
from itertools import chain
from providers.Phoenix import get_phoenix_components, populate_phoenix_teams, get_auth_token , create_teams, create_team_rules, assign_users_to_team, populate_applications_and_environments, create_environment, add_environment_services, add_cloud_asset_rules, add_thirdparty_services, create_applications, create_deployments, create_autolink_deployments, create_teams_from_pteams, create_components_from_assets, create_user_for_application, load_users_from_phoenix, update_environment, check_and_create_missing_users, create_user_with_role
import providers.Phoenix as phoenix_module
from providers.Utils import populate_domains, get_subdomains, populate_users_with_all_team_access
from providers.YamlHelper import populate_repositories_from_config, populate_teams, populate_hives, populate_subdomain_owners, populate_environments_from_env_groups_from_config, populate_all_access_emails_from_config, populate_applications_from_config, load_flag_for_create_users_from_config, load_run_config

# Global Variables
resource_folder = os.path.join(os.path.dirname(__file__), 'Resources')


def get_config_files_to_use():
    """
        Return list of config file names to use for processing apps/environments
    """
    config = load_run_config(resource_folder)

    return config['ConfigFiles']


def get_config_files():
    """
        Returns list of config files containing apps/environment data.
        Files are first loaded from Resources folder.
        Then they are filtered to only return ones that are configured in run-config.yaml
    """
    # here we can add the distributed mode logic when needed
    files = next(os.walk(resource_folder), (None, None, []))[2]
    config_files_to_use = get_config_files_to_use()
    if phoenix_module.DEBUG:
        print(f"Scanning detected config files: {files} at {resource_folder}")
    files = list(file for file in files if file in config_files_to_use)
    
    print(f"Using config files for processing: {files}")

    return list(os.path.join(resource_folder, file) for file in files if '.yaml' in file or '.yml' in file)

def perform_actions(args, config_file_path):  

    client_id = args.client_id
    client_secret = args.client_secret
    if (args.api_domain):
        phoenix_module.APIdomain = args.api_domain
    action_teams = args.action_teams == 'true'
    action_create_users_from_teams = args.action_create_users_from_teams == 'true'
    action_code = args.action_code == 'true'
    action_cloud = args.action_cloud == 'true'
    action_deployment = args.action_deployment == 'true'
    action_autolink_deploymentset = args.action_autolink_deploymentset == 'true'
    action_autocreate_teams_from_pteam = args.action_autocreate_teams_from_pteam == 'true'
    action_create_components_from_assets = args.action_create_components_from_assets == 'true'

    # Populate data from various resources
    teams = populate_teams(resource_folder)
    hive_staff = populate_hives(resource_folder)  # List of Hive team staff
    access_token = get_auth_token(client_id, client_secret)
    pteams = populate_phoenix_teams(access_token)  # Pre-existing Phoenix teams
    defaultAllAccessAccounts = populate_all_access_emails_from_config(config_file_path)
    all_team_access = populate_users_with_all_team_access(teams, defaultAllAccessAccounts)  # Populate users with full team access

    # Display teams
    print("[Teams]")
    for team in teams:
        try:
            if team.get('AzureDevopsAreaPath'):  # Only process if AzureDevopsAreaPath exists
                if "Team" in team['AzureDevopsAreaPath']:
                    team['TeamName'] = team['AzureDevopsAreaPath'].split("Team")[1].strip()
                    print(team['TeamName'])
        except Exception as e:
            print(f"Error processing team: {str(e)}")
            if phoenix_module.DEBUG:
                print(f"Team data: {team}")

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
        
        if action_create_users_from_teams:
            print("Creating users from team configuration")
            current_users_emails = list(u.get("email") for u in load_users_from_phoenix(headers))
            created_users_emails = []
            for team in teams:
                for member in team.get('TeamMembers', []):
                    try:
                        if not member.get('Name'):
                            print(f"⚠️ Error: Missing Name field for team member with email {member.get('EmailAddress', 'NO_EMAIL')}")
                            continue
                            
                        name_parts = member['Name'].split()
                        if len(name_parts) < 2:
                            print(f"⚠️ Error: Invalid name format for {member['Name']} - needs first and last name")
                            continue
                            
                        first_name = name_parts[0]
                        last_name = ' '.join(name_parts[1:])
                        email = member.get('EmailAddress')
                        role = member.get('EmployeeRole', 'ORG_USER')
                        
                        # Map role to Phoenix roles
                        if role == 'Security Champion':
                            phoenix_role = 'SECURITY_CHAMPION'
                        elif role == 'Engineering User':
                            phoenix_role = 'ENGINEERING_USER'
                        elif role == 'Application Admin':
                            phoenix_role = 'APPLICATION_ADMIN'
                        else:
                            phoenix_role = 'ORG_USER'
                        
                        if email not in current_users_emails and email not in created_users_emails:
                            create_user_with_role(email, first_name, last_name, phoenix_role, headers)
                            created_users_emails.append(email)
                            
                    except Exception as e:
                        print(f"⚠️ Error processing team member: {str(e)}")
                        if phoenix_module.DEBUG:
                            print(f"Member data: {member}")
        
        new_pteams = create_teams(teams, pteams, access_token)
        check_and_create_missing_users(teams, all_team_access, hive_staff, access_token)
        create_team_rules(teams, pteams, access_token)
        assign_users_to_team(pteams, new_pteams, teams, all_team_access, hive_staff, access_token)

        elapsed_time = time.time() - start_time
        print(f"[Diagnostic] [Teams] Time Taken: {elapsed_time}")
        start_time = time.time()

    # Cloud actions
    if action_cloud:
        print("Performing Cloud Actions")
        repos = populate_repositories_from_config(config_file_path)
        domains = populate_domains(repos)
        subdomain_owners = populate_subdomain_owners(repos)
        subdomains = get_subdomains(repos)
        environments = populate_environments_from_env_groups_from_config(config_file_path)

        # Display domains and repos
        print("\n[Domains]")
        print(domains)

        print("\n[Repos]")
        for repo in repos:
            print(repo['RepositoryName'])

    
        if load_flag_for_create_users_from_config(config_file_path):
            print("Creating users from Environment 'Responsable' field")
            current_users_emails = list(u.get("email") for u in load_users_from_phoenix(access_token))
            print(f"Users in Phoenix {current_users_emails}")
            created_users_emails = []
            for env in environments:
                created_user_email = create_user_for_application(current_users_emails, created_users_emails, env.get('Responsable'), access_token)
                if created_user_email:
                    created_users_emails.append(created_user_email)
        
        # First handle environment updates
        print("\n[Environment Updates]")
        for environment in environments:
            existing_env = next((env for env in app_environments if env.get('type') == 'ENVIRONMENT' and env['name'] == environment['Name']), None)
            if not existing_env:
                # Create environments as needed
                print(f"Creating environment: {environment['Name']}")
                create_environment(environment, headers)
            else:
                print(f"Updating environment: {environment['Name']}")
                try:
                    update_environment(environment, existing_env, headers)
                except Exception as e:
                    print(f"Warning: Failed to update environment {environment['Name']}: {str(e)}")
                    continue

        # Then handle services
        print("\n[Service Updates]")
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
        applications = populate_applications_from_config(config_file_path)
        if load_flag_for_create_users_from_config(config_file_path):
           print("Creating users from Application 'Responsable' field")
           current_users_emails = list(u.get("email") for u in load_users_from_phoenix(access_token))
           created_users_emails = []
           for app in applications:
               created_user_email = create_user_for_application(current_users_emails, created_users_emails, app.get('Responsable'), access_token)
               if created_user_email:
                   created_users_emails.append(created_user_email)
        create_applications(applications, app_environments, phoenix_components, headers)
        
        print(f"[Diagnostic] [Code] Time Taken: {time.time() - start_time}")
        start_time = time.time()

    if action_deployment:
        print("Performing deployment action")
        # reload apps/envs before deployment
        app_environments = populate_applications_and_environments(headers)
        environments = populate_environments_from_env_groups_from_config(config_file_path)
        applications = populate_applications_from_config(config_file_path)
        create_deployments(applications, environments, app_environments, headers)
        print(f"[Diagnostic] [Deployment] Time Taken: {time.time() - start_time}")
        start_time = time.time()

    if action_autolink_deploymentset:
        print("Performing autolink deployment set action")
        environments = populate_environments_from_env_groups_from_config(config_file_path)
        applications = populate_applications_from_config(config_file_path)
        create_autolink_deployments(applications, environments, headers)
        print(f"[Diagnostic] [Autolink deploymentset] Time Taken: {time.time() - start_time}")
        start_time = time.time()

    if action_autocreate_teams_from_pteam:
        print("Performing autocreate teams from pteam")
        environments = populate_environments_from_env_groups_from_config(config_file_path)
        applications = populate_applications_from_config(config_file_path)
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
    parser.add_argument("--action_create_users_from_teams", type=str, default="false",
                        required=False, help="Flag triggering automatic user creation from team configuration")
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
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug output")
    
    # Parse arguments
    args = parser.parse_args()

    # Set DEBUG mode in all relevant modules if --verbose is passed
    if args.verbose:
        phoenix_module.DEBUG = True
        import providers.YamlHelper as yaml_helper_module
        yaml_helper_module.DEBUG = True

    for config_file in get_config_files():
        try:
            print(f"Started processing config file {config_file}")
            perform_actions(args, config_file)
            print(f"Finished processing config file {config_file}")
        except Exception as e:
            print(f"Error performing actions for {config_file} error: {traceback.format_exc()}")
            phoenix_module.log_error(
                "Perform actions",
                config_file,
                "N/A",
                "Error performing actions",
                traceback.format_exc()
            )
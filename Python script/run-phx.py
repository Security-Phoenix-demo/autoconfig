import time
import os
import argparse
import traceback
import stat
from git import Repo
from datetime import datetime, timedelta
from threading import Thread, Event
from itertools import chain
from providers.Phoenix import get_phoenix_components, populate_phoenix_teams, get_auth_token , create_teams, create_team_rules, assign_users_to_team, populate_applications_and_environments, create_environment, add_environment_services, add_cloud_asset_rules, add_thirdparty_services, create_applications, create_deployments, create_autolink_deployments, create_teams_from_pteams, create_components_from_assets, create_user_for_application, load_users_from_phoenix, update_environment, check_and_create_missing_users, create_user_with_role
import providers.Phoenix as phoenix_module
from providers.Utils import populate_domains, get_subdomains, populate_users_with_all_team_access, add_PAT_to_github_repo_url
from providers.YamlHelper import populate_repositories_from_config, populate_teams, populate_hives, populate_subdomain_owners, populate_environments_from_env_groups_from_config, populate_all_access_emails_from_config, populate_applications_from_config, load_flag_for_create_users_from_config, load_run_config, load_remote_configuration_locations, load_github_repo_folder, load_github_config_file_name

# Global Variables
resource_folder = os.path.join(os.path.dirname(__file__), 'Resources')
access_token = None
headers = {}
CLIENT_ID = None
CLIENT_SECRET = None


def get_config_files_to_use():
    """
        Return list of config file names to load from Resources folder
    """
    config = load_run_config(resource_folder)

    return config['ConfigFiles']


def get_config_files_from_github_repos(github_pat):
    """
        If github repos aren't configured in run-config.yaml, return empty list.

        Otherwise, try to checkout each repo, try to find the config file named as 'ConfigFileName' in run-config.yaml and return the files
    """
    config_files = []
    repositories = load_remote_configuration_locations(resource_folder)

    if not repositories or not len(repositories):
        print("No GitHub repos configured to use")
        return config_files
    
    if not github_pat:
        print("GitHub Personal Access token not provided via CLI, unable to use github configurations")
        return config_files
    
    gh_config_file_name = load_github_config_file_name(resource_folder)
    local_gh_repo_folder = load_github_repo_folder(resource_folder)
        
    for repository in repositories:
        try:
            local_folder = repository.rsplit("/")[4]
            local_folder_path = os.path.join(local_gh_repo_folder, local_folder)
            print(f'Pulling latest config for {local_folder}')
            if not os.path.exists(local_folder_path):
                print(f'Cloning repo for {local_folder}')
                repository = add_PAT_to_github_repo_url(github_pat, repository)
                repo = Repo.clone_from(repository, local_folder_path)
                os.chmod(local_folder_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            repo = Repo.init(local_folder_path).remote()
            repo.pull()
            print(f'Pulled latest config for {local_folder}')
            gh_config_file = find_config_file_in_github_repo(local_folder_path, gh_config_file_name)
            if gh_config_file:
                config_files.append(gh_config_file)
            else:
                print(f"{gh_config_file_name} not found in {local_folder_path}")
        except Exception as e:
            print(f'Error occurred while pulling latest changes for repository {repository}')
            print(e)
            continue

    return config_files


def find_config_file_in_github_repo(folder, gh_config_file_name):
    if os.path.exists(os.path.join(folder, gh_config_file_name)):
        return os.path.join(folder, gh_config_file_name)
    return None

def get_config_files(github_pat):
    """
        Returns list of config files from Resources folder.

        Optionally, if GitHub repos are configured, it will checkout those repos
        and try to load config files from those repos, and return them as well
    """
    config_files = get_config_files_from_resources_folder()

    config_files.extend(get_config_files_from_github_repos(github_pat))

    return config_files


def get_config_files_from_resources_folder():
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

    if not config_files_to_use:
        print(f"No config files to use from Resources folder")
        return []
    files = list(file for file in files if file in config_files_to_use)
    
    print(f"Using config files for processing: {files}")

    return list(os.path.join(resource_folder, file) for file in files if '.yaml' in file or '.yml' in file)

def refresh_access_token(stop_event):
    global access_token
    global headers
    refresh_period_in_minutes = 10
    next_refresh = datetime.now()
    while not stop_event.is_set():
        if datetime.now() > next_refresh:
            access_token = get_auth_token(CLIENT_ID, CLIENT_SECRET)
            headers['Authorization'] = f'Bearer {access_token}'
            phoenix_module.access_token = access_token
            phoenix_module.headers = headers
            print(f"Refreshed access token")
            next_refresh = datetime.now() + timedelta(minutes=refresh_period_in_minutes)
            time.sleep(5)


def perform_actions(args, config_file_path):  

    client_id = args.client_id
    global CLIENT_ID
    CLIENT_ID = client_id
    client_secret = args.client_secret
    global CLIENT_SECRET
    CLIENT_SECRET = client_secret
    global access_token
    global headers
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


    # Start refresh token process
    stop_event = Event()
    thread = Thread(target=refresh_access_token, args=(stop_event,))
    thread.start()
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
        app_environments = populate_applications_and_environments(headers)
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

    print("Waiting for refresh access token thread to stop")
    stop_event.set()
    thread.join()
    print("Refresh access token thread stopped")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process input arguments.")

    # Add arguments
    parser.add_argument("client_id", type=str, help="Client ID")
    parser.add_argument("client_secret", type=str, help="Client Secret")
    parser.add_argument("--github_pat", type=str, help="GitHub Personal Access Token")
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

    for config_file in get_config_files(args.github_pat):
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
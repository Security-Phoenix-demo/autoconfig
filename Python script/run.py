import time
import os
import argparse
from itertools import chain
from providers.Phoenix import get_phoenix_components, populate_phoenix_teams, get_auth_token , create_teams, create_team_rules, assign_users_to_team, populate_applications_and_environments, create_environment, add_environment_services, add_cloud_asset_rules, add_thirdparty_services, create_applications, create_deployments, create_autolink_deployments, create_teams_from_pteams, create_components_from_assets
import providers.Phoenix as phoenix_module
from providers.Utils import populate_domains, get_subdomains, populate_users_with_all_team_access
from providers.YamlHelper import populate_repositories, populate_teams, populate_hives, populate_subdomain_owners, populate_environments_from_env_groups, populate_all_access_emails, populate_applications

# Global Variables
resource_folder = os.path.join(os.path.dirname(__file__), 'Resources')

def perform_actions(args):  

    client_id = args.client_id
    client_secret = args.client_secret
    if (args.api_domain):
        phoenix_module.APIdomain = args.api_domain
    action_teams = args.action_teams
    action_code = args.action_code
    action_cloud = args.action_cloud
    action_deployment = args.action_deployment
    action_autolink_deploymentset = args.action_autolink_deploymentset
    action_autocreate_teams_from_pteam = args.action_autocreate_teams_from_pteam
    action_create_components_from_assets = args.action_create_components_from_assets
    should_verify_only = args.verify

    verify_data = {}
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

    if not should_verify_only:
        # Display teams
        print("[Teams]")
        for team in teams:
            try:
                if "Team" in team['AzureDevopsAreaPath']:
                    team['TeamName'] = team['AzureDevopsAreaPath'].split("Team")[1].strip()
                    print(team['TeamName'])
            except Exception as e:
                print(f"Error: {e}")

    if not should_verify_only:
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
        teams_resp = create_teams(teams, pteams, access_token, should_verify_only)
        verify_data["teams"] = teams_resp.get("verify_data", [])
        new_pteams = teams_resp.get("new_pteams")
        verify_data["team_rules"] = create_team_rules(teams, pteams, access_token, should_verify_only)
        assign_users_to_team(pteams, new_pteams, teams, all_team_access, hive_staff, access_token, should_verify_only)

        elapsed_time = time.time() - start_time
        print(f"[Diagnostic] [Teams] Time Taken: {elapsed_time}")
        start_time = time.time()

    # Cloud actions
    if action_cloud:
        print("Performing Cloud Actions")
        verify_data['environments'] = []
        verify_data['environment_services'] = []
        verify_data['cloud_asset_rules'] = []
        verify_data['thirdparty_services'] = []
        for environment in environments:
            if not any(env['name'] == environment['Name'] and env.get('type') == "ENVIRONMENT" for env in app_environments):
                # Create environments as needed
                print(f"Creating environment: {environment['Name']}")
                verify_data['environments'].append(create_environment(environment, headers, should_verify_only))

        # Perform cloud services
        verify_data['environment_services']=add_environment_services(repos, subdomains, environments, app_environments, phoenix_components, subdomain_owners, teams, access_token, should_verify_only)
        print("[Diagnostic] [Cloud] Time Taken:", time.time() - start_time)
        print("Starting Cloud Asset Rules")
        verify_data['cloud_asset_rules'] = add_cloud_asset_rules(repos, access_token, should_verify_only)
        print("[Diagnostic] [Cloud] Time Taken:", time.time() - start_time)
        print("Starting Third Party Rules")
        verify_data['thirdparty_services'] = add_thirdparty_services(phoenix_components, app_environments, subdomain_owners, headers, should_verify_only)
    
        elapsed_time = time.time() - start_time
        print(f"[Diagnostic] [Cloud] Time Taken: {elapsed_time}")
        start_time = time.time()

    if action_code:
        print("Performing Code Actions")
        verify_data['applications'] = create_applications(applications, app_environments, phoenix_components, headers, should_verify_only)
        
        print(f"[Diagnostic] [Code] Time Taken: {time.time() - start_time}")
        start_time = time.time()

    if action_deployment:
        print("Performing deployment action")
        verify_data['deployments'] = create_deployments(applications, environments, app_environments, headers, should_verify_only)
        print(f"[Diagnostic] [Deployment] Time Taken: {time.time() - start_time}")
        start_time = time.time()

    if action_autolink_deploymentset:
        print("Performing autolink deployment set action")
        verify_data['autolink_deployments'] = create_autolink_deployments(applications, environments, headers, should_verify_only)
        print(f"[Diagnostic] [Autolink deploymentset] Time Taken: {time.time() - start_time}")
        start_time = time.time()

    if action_autocreate_teams_from_pteam:
        print("Performing autocreate teams from pteam")
        verify_data['autocreated_teams'] = create_teams_from_pteams(applications, environments, pteams, access_token, should_verify_only)
        print(f"[Diagnostic] [Autocreate teams from pteam] Time Taken: {time.time() - start_time}")
        start_time = time.time()

    if action_create_components_from_assets:
        print("Performing create components/services from assets")
        verify_data['components_from_assets'] = create_components_from_assets(app_environments, phoenix_components, headers, should_verify_only)
        print(f"[Diagnostic] [Create components/services from assets] Time Taken: {time.time() - start_time}")

   

    if should_verify_only:
        #verify_data_json = json.dumps(verify_data, indent=4)    
        #with open('verify.json', 'w') as f:
        #    f.write(verify_data_json)
        print_verify_data(verify_data)

def print_verify_data(verify_data):
    print('')
    print('[VERIFY ONLY MODE] Changes to apply:')
    if len(verify_data.get('environments', [])):
        print('')
        print("Environments: ")
        print('')
        for env in verify_data['environments']:
            env_name = env['name']
            print(f'Environment: {env_name}')
            print('  Services')
            for service in verify_data.get('environment_services', {}).get('services', []):
                service_name = service.get('name', '')
                if not env_name == service.get('applicationSelector', {}).get('name'):
                    continue
                apps_from_deployment = [] #list(d.get('applicationSelector').get('name') for d in verify_data.get('deployments') if service_name in list(t.get('value') for t in d.get('serviceSelector').get('tags', [])))
                print("    Service: " + service_name + ((" -> " + ', '.join(apps_from_deployment)) if apps_from_deployment else '')) 
                print("      Service rules")
                for service_rule in verify_data.get('environment_services', {}).get('service_rules', []):
                    if not env_name == service_rule.get('selector', {}).get('applicationSelector', {}).get('name') or \
                        not service_name == service_rule.get('selector', {}).get('componentSelector', {}).get('name'):
                        continue
                    for rule in service_rule.get('rules', []):
                        print(f"        Service rule: {rule.get('name', '')}")
                        for filter in rule.get('filter', {}).items():
                            print(f"          {filter}")
    if len(verify_data.get('applications', {}).get('created', [])):
        print('')
        print("Applications to create:")
        print('')
        for app in verify_data.get('applications', {}).get('created', []):
            app_name = app.get("application", {}).get("name", "")
            deployments_for_app = [l.get('value', '') for l in 
                                   chain.from_iterable(d.get('serviceSelector', {}).get('tags', []) for 
                                                       d in verify_data.get('deployments', []) if app_name == d.get('applicationSelector', {}).get('name', ''))]
            print(f'  Application: {app_name + ((' -> ' + ", ".join(deployments_for_app)) if deployments_for_app else '')}')
            for comp in app.get('components', []):
                c = comp.get("component", {})
                print(f'    Component: {c.get("name", "")}')
                for tag in c.get('tags', []):
                    print(f'      (\'{tag.get("key", "")}\', \'{tag.get("value", "")}\')')
    
    if len(verify_data.get("teams", [])):
        print('')
        print("Teams to create:")
        print('')
        for team in verify_data.get("teams", []):
            team_name = team.get("name", "")
            print(f'Team: {team_name}')
            for app in verify_data.get('applications', {}).get('created', []):
                if team_name in list(t.get("value") for t in app.get("application", {}).get("tags", []) if t.get("key", "") == "pteam"):
                    print(f'  Application: {app.get("application", {}).get("name", "")}')
                    for comp in app.get("components", []):
                        if team_name in list(t.get("value") for t in comp.get("component", {}).get("tags", []) if t.get("key", "") == "pteam"):
                            print(f'    Component: {comp.get("component").get("name")}')
            
            for env in verify_data.get("environments", []):
                if team_name in list(t.get("value") for t in env.get("tags", []) if t.get("key") == "pteam"):
                    env_name = env.get("name")
                    print(f'  Environment: {env_name}')
                    for service in verify_data.get("environment_services", {}).get("services", []):
                        if env_name == service.get("applicationSelector", {}).get("name", "") and \
                                team_name in list(t.get("value", "") for t in service.get("tags", []) if t.get("key", "") == "pteam"):
                            print(f'    Service: {service.get("name", "")}')

    if len(verify_data.get("deployments", [])):
        print('Deployments to create')
        for deployment in verify_data.get("deployments", []):
            print_line = f'  App: {deployment.get("applicationSelector", {}).get("name", "")}'
            if deployment.get("serviceSelector", {}).get("name", ""):
                print_line += f' -> Service: {deployment.get("serviceSelector", {}).get("name", "")}'
            if deployment.get("serviceSelector", {}).get("tags", []):
                print_line += f' -> Service deployment tags: {list(t.get("value") for t in deployment.get("serviceSelector", {}).get("tags", []))}'
            print(print_line)
            

    if len(verify_data.get("autocreated_teams", [])):
        print('')
        print("Teams to autocreate:")
        print('')
        for team in verify_data.get("autocreated_teams", []):
            team_name = team.get("name")
            print(team_name)
            for app in verify_data.get('applications', {}).get('created', []):
                if team_name in list(t.get("value") for t in app.get("application", {}).get("tags", []) if t.get("key", "") == "pteam"):
                    print(f'  Application: {app.get("application", {}).get("name", "")}')
                    for comp in app.get("components", []):
                        if team_name in list(t.get("value") for t in comp.get("component", {}).get("tags", []) if t.get("key", "") == "pteam"):
                            print(f'    Component: {comp.get("component").get("name")}')
            
            for env in verify_data.get("environments", []):
                if team_name in list(t.get("value") for t in env.get("tags", []) if t.get("key") == "pteam"):
                    env_name = env.get("name")
                    print(f'  Environment: {env_name}')
                    for service in verify_data.get("environment_services", {}).get("services", []):
                        if env_name == service.get("applicationSelector", {}).get("name", "") and \
                                team_name in list(t.get("value", "") for t in service.get("tags", []) if t.get("key", "") == "pteam"):
                            print(f'    Service: {service.get("name", "")}')
    
    if len(verify_data.get("components_from_assets", [])):
        print('')
        print('Create components from assets (App/Env -> Comp/Serv)')
        print('')
        for comp in verify_data.get("components_from_assets", []):
            print(f' {comp.get("component", {}).get("applicationSelector", {}).get("name")} -> {comp.get("component", {}).get("name")}')



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process input arguments.")

    # Add arguments
    parser.add_argument("client_id", type=str, help="Client ID")
    parser.add_argument("client_secret", type=str, help="Client Secret")
    parser.add_argument("--api_domain", type=str, default=phoenix_module.APIdomain, required=False, help="Phoenix API domain")
    parser.add_argument("--action_teams", type=bool, default=False, 
                        required=False, help="Flag triggering teams action")
    parser.add_argument("--action_code", type=bool, default=False, 
                        required=False, help="Flag triggering code action")
    parser.add_argument("--action_cloud", type=bool, default=False, 
                        required=False, help="Flag triggering cloud action")
    parser.add_argument("--action_deployment", type=bool, default=False, 
                        required=False, help="Flag triggering deployment action")
    parser.add_argument("--action_autolink_deploymentset", type=bool, default=False, 
                        required=False, help="Flag triggering autolink deploymentset action")
    parser.add_argument("--action_autocreate_teams_from_pteam", type=bool, default=False,
                         required=False, help="Flag triggering autocreate teams from pteam action")
    parser.add_argument("--action_create_components_from_assets", type=bool, default=False, 
                        required=False, help="Flag triggering create components from assets action")
    parser.add_argument("--verify", type=bool, default=False, 
                        required=False, help="Flag indicating whether changes should be only printed (when True) or applied (when False)")

    
    # Parse arguments
    args = parser.parse_args()
    
    perform_actions(args)
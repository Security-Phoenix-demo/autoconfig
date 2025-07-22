import os
import yaml
from pathlib import Path
from providers.Utils import calculate_criticality
from email_validator import validate_email, EmailNotValidError
from .Linter import validate_component, validate_application, validate_environment, validate_service
from .Phoenix import extract_last_two_path_parts

# Check if PyYAML module exists
try:
    import yaml
    print("Module exists")
except ImportError:
    print("Module does not exist. Installing...")
    os.system('pip install pyyaml')

# Debug setting
DEBUG = True

# Function to populate repositories
def populate_repositories(resource_folder):
    if not resource_folder:
        print("Please supply path for the resources")
        return []

    core_structure = os.path.join(resource_folder, "core-structure.yaml")

    return populate_repositories_from_config(core_structure) 


def populate_repositories_from_config(core_structure):
    repos = []
    with open(core_structure, 'r') as stream:
        repos_yaml = yaml.safe_load(stream)

    if 'DeploymentGroups' not in repos_yaml:
        print(f"DeploymentGroups not found in {core_structure}, uanble to populate repositories")
        return repos

    for deployment_group in repos_yaml['DeploymentGroups']:
        if 'BuildDefinitions' not in deployment_group:
            continue
        
        for row in deployment_group['BuildDefinitions']:
            repositoryNames = row.get('RepositoryName', [])
            
            # Check if repositoryNames is a string, if so convert to list
            if isinstance(repositoryNames, str):
                repositoryNames = [repositoryNames]
            
            # Ensure repositoryNames is iterable
            if not isinstance(repositoryNames, list):
                print(f"Warning: RepositoryName is not in an expected format for row: {row}")
                continue

            for repositoryName in repositoryNames:
                # Extract last 2 parts of repository path for cleaner names
                shortened_repo_name = extract_last_two_path_parts(repositoryName)
                print(f'Created repository {shortened_repo_name} (original: {repositoryName})')
                item = {
                    'RepositoryName': shortened_repo_name,
                    'Domain': row['Domain'],
                    'Tier': row.get('Tier', 5),
                    'Subdomain': row['SubDomain'],
                    'Team': row['TeamName'],
                    'BuildDefinitionName': row['BuildDefinitionName']
                }
                repos.append(item)

    return repos


# Function to populate environments
def populate_environments_from_env_groups(resource_folder):
    if not resource_folder:
        print("Please supply path for the resources")
        return []

    banking_core = os.path.join(resource_folder, "core-structure.yaml")
    return populate_environments_from_env_groups_from_config(banking_core)


def populate_environments_from_env_groups_from_config(config_file_path):
    envs = []
    
    with open(config_file_path, 'r') as stream:
        repos_yaml = yaml.safe_load(stream)

    if 'Environment Groups' not in repos_yaml:
        print(f"Environment Groups key not found in {config_file_path}, unable to populate envs from config")
        return envs

    for row in repos_yaml['Environment Groups']:
        print_linter_result(row.get('Name', 'N/A'), validate_environment(row))
        # Define the environment item
        item = {
            'Name': row['Name'],
            'Type': row['Type'],
            'Criticality': calculate_criticality(row['Tier']),
            'CloudAccounts': [""],  # Add CloudAccounts if applicable
            'Status': row['Status'],
            'Responsable': row['Responsable'].lower(),
            'TeamName': row.get('TeamName', None),  # Add TeamName from the environment or set as None
            'Ticketing': load_ticketing(row),
            'Messaging': load_messaging(row),
            'Services': []  # To populate services later
        }

        # Now process the services under the "Team" or "Services" key
        if 'Services' in row:
            for service in row['Services']:
                print_linter_result(service.get('Service', 'N/A'), validate_service(service))
                repository_names = service.get('RepositoryName', [])
                if isinstance(repository_names, str):
                    repository_names = [repository_names]
                # Build the service entry with association details
                service_entry = {
                    'Service': service['Service'],
                    'Type': service['Type'],
                    'Tier': service.get('Tier', 5),  # Default tier to 5 if not specified
                    'TeamName': service.get('TeamName', item['TeamName']),  # Default to environment's TeamName if missing
                    'Ticketing': load_ticketing(service),
                    'Messaging': load_messaging(service),
                    'Deployment_set': service.get('Deployment_set', None),
                    'Deployment_tag': service.get('Deployment_tag', None),
                    'MultiConditionRule': list(x for x in [load_multi_condition_rule(service.get('MultiConditionRule', None))] if x is not None),
                    'MultiConditionRules': load_multi_condition_rules(service),
                    'RepositoryName': repository_names,  # Properly handle missing 'RepositoryName'
                    'SearchName': service.get('SearchName', None),
                    "Tag": service.get("Tag", None),
                    "Tag_rule": service.get("Tag_rule", None),
                    "Tags_rule": service.get("Tags_rule", None),
                    "Tag_label": service.get("Tag_label", None),
                    "Tags_label": service.get("Tags_label", None),
                    "Cidr": service.get("Cidr", None),
                    "Fqdn": service.get("Fqdn", None),
                    "Netbios": service.get("Netbios", None),
                    "OsNames": service.get("OsNames", None),
                    "Hostnames": service.get("Hostnames", None),
                    "ProviderAccountId": service.get("ProviderAccountId", None),
                    "ProviderAccountName": service.get("ProviderAccountName", None),
                    "ResourceGroup": service.get("ResourceGroup", None),
                    "AssetType": service.get("AssetType", None)
                }
                item['Services'].append(service_entry)

        # Append the environment entry to the list of environments
        envs.append(item)

    return envs

# Function to populate subdomain owners
def populate_subdomain_owners(repos):
    subdomains = {}

    for repo in repos:
        print(repo['RepositoryName'])

        if repo['Subdomain'] not in subdomains:
            subdomains[repo['Subdomain']] = []

        if repo['Team'] not in subdomains[repo['Subdomain']]:
            subdomains[repo['Subdomain']].append(repo['Team'])

    return subdomains


# Function to populate teams

# Example of populating repositories - already in place, no changes needed unless additional processing is required

# Function to populate teams
def populate_teams(resource_folder):
    teams = []

    if not resource_folder:
        print("Please supply path for the resources")
        return teams

    teams_file_path = os.path.join(resource_folder, "Teams")

    if not os.path.exists(teams_file_path):
        print(f"Path does not exist: {teams_file_path}")
        exit(1)

    for team_file in Path(teams_file_path).glob("*.yaml"):
        with open(team_file, 'r') as stream:
            team = yaml.safe_load(stream)

        found = False
        for t in teams:
            if t['TeamName'] == team['TeamName']:
                found = True
                break

        if not found:
            teams.append(team)

    return teams


# Function to populate hives
def populate_hives(resource_folder):
    hives = []

    if not resource_folder:
        print("Please supply path for the resources")
        return hives

    yaml_file = os.path.join(resource_folder, "hives.yaml")

    if not os.path.exists(yaml_file):
        print(f"File not found or invalid path: {yaml_file}")
        return hives

    with open(yaml_file, 'r') as stream:
        yaml_content = yaml.safe_load(stream)

    is_custom_email = yaml_content.get('CustomEmail', False)
    company_email_domain = yaml_content.get('CompanyEmailDomain', None)
    if not is_custom_email and not company_email_domain:
        company_email_domain = input('Please enter company email domain (without @ symbol):')

    for hive in yaml_content['Hives']:
        for team in hive['Teams']:
            products = []
            if team.get('Product'):
                products = [conditionally_replace_first_last_name_with_email(is_custom_email, company_email_domain, p)
                            for p in team['Product'].split(' and ')]

            hive_object = {
                'Lead': conditionally_replace_first_last_name_with_email(is_custom_email, company_email_domain, team['Lead']),
                'Product': products,
                'Team': team['Name']
            }

            hives.append(hive_object)

    return hives

# If is_custom_email=True, only validate the emails and don't replace anything
def conditionally_replace_first_last_name_with_email(is_custom_email, company_email_domain, first_last_name_or_email):
    if (is_custom_email):
        try:
            result = validate_email(first_last_name_or_email)
            return
        except EmailNotValidError as e:
            print(str(e))
            exit(1)

    
    return first_last_name_or_email.strip().lower().replace(" ", ".") + "@" + company_email_domain


def populate_all_access_emails(resource_folder):
    if not resource_folder:
        print("Please supply path for the resources")
        return []

    core_structure = os.path.join(resource_folder, "core-structure.yaml")

    return populate_all_access_emails_from_config(core_structure)


def populate_all_access_emails_from_config(config_file_path):
    with open(config_file_path, 'r') as stream:
        repos_yaml = yaml.safe_load(stream)

    if 'AllAccessAccounts' not in repos_yaml:
        print(f"AllAccessAccounts not found in {config_file_path}, unable to populate all access account list")
        return []
    return repos_yaml['AllAccessAccounts']

# Populate applications

# Populate applications
def populate_applications(resource_folder):
    if not resource_folder:
        print("Please supply path for the resources")
        return []

    core_structure = os.path.join(resource_folder, "core-structure.yaml")

    return populate_applications_from_config(core_structure)


def populate_applications_from_config(config_file_path):
    apps = []
    with open(config_file_path, 'r') as stream:
        apps_yaml = yaml.safe_load(stream)

    if 'DeploymentGroups' not in apps_yaml:
        print(f"DeploymentGroups key not found in {config_file_path}, unable to populate apps from config")
        return apps
        

    for row in apps_yaml['DeploymentGroups']:
        print_linter_result(row.get("AppName", "N/A"), validate_application(row))
        app = {
            'AppName': row['AppName'],
            'Status': row.get('Status', None),
            'TeamNames': row.get('TeamNames', []),
            'ReleaseDefinitions': row['ReleaseDefinitions'],
            'Responsable': row['Responsable'].lower(),
            'Criticality': calculate_criticality(row.get('Tier', 5)),
            'Deployment_set': row.get('Deployment_set', None),
            'Ticketing': load_ticketing(row),
            'Messaging': load_messaging(row),
            'Components': []
        }

        if not 'Components' in row:
            continue

        for component in row['Components']:
            # Handle RepositoryName properly
            print_linter_result(component.get("ComponentName", "N/A"), validate_component(component))
            repository_names = component.get('RepositoryName', [])
            if isinstance(repository_names, str):
                repository_names = [repository_names]

            # Get ticketing and messaging configurations
            ticketing = load_ticketing(component) or app.get('Ticketing')  # Inherit from app if not specified
            messaging = load_messaging(component) or app.get('Messaging')  # Inherit from app if not specified

            comp = {
                'ComponentName': component['ComponentName'],
                'Status': component.get('Status', None),
                'Type': component.get('Type', None),
                'Ticketing': ticketing,
                'Messaging': messaging,
                'TeamNames': component.get('TeamNames', app['TeamNames']),
                'RepositoryName': repository_names,
                'SearchName': component.get('SearchName', None),
                'Tags': component.get('Tags', None),
                'Tag_label': component.get('Tag_label', None),
                'Tags_label': component.get('Tags_label', None),
                'Cidr': component.get('Cidr', None),
                'Fqdn': component.get('Fqdn', None),
                'Netbios': component.get('Netbios', None),
                'OsNames': component.get('OsNames', None),
                'Hostnames': component.get('Hostnames', None),
                'ProviderAccountId': component.get('ProviderAccountId', None),
                'ProviderAccountName': component.get('ProviderAccountName', None),
                'ResourceGroup': component.get('ResourceGroup', None),
                'AssetType': component.get('AssetType', None),
                'MultiConditionRule': load_multi_condition_rule(component.get('MultiConditionRule', None)),
                'MultiConditionRules': load_multi_condition_rules(component),
                'Criticality': calculate_criticality(component.get('Tier', 5)),
                'Domain': component.get('Domain', None),
                'SubDomain': component.get('SubDomain', None),
                'AutomaticSecurityReview': component.get('AutomaticSecurityReview', None)
            }

            if DEBUG:
                print(f"\nProcessing component {comp['ComponentName']}:")
                if ticketing:
                    print(f"└─ Ticketing configuration:")
                    for ticket_config in ticketing:
                        print(f"   └─ TIntegrationName: {ticket_config.get('TIntegrationName')}")
                        print(f"   └─ Backlog: {ticket_config.get('Backlog')}")
                if messaging:
                    print(f"└─ Messaging configuration:")
                    for message_config in messaging:
                        print(f"   └─ MIntegrationName: {message_config.get('MIntegrationName')}")
                        print(f"   └─ Channel: {message_config.get('Channel')}")

            app['Components'].append(comp)
        apps.append(app)

    return apps


def load_multi_condition_rule(mcr):
    if not mcr:
        return None
    rule = {
        "RepositoryName": mcr.get("RepositoryName", None),
        "SearchName": mcr.get("SearchName", None),
        "Tags": mcr.get("Tags", None),
        "Tag": mcr.get("Tag", None),
        "Tag_rule": mcr.get("Tag_rule", None),
        "Tags_rule": mcr.get("Tags_rule", None),
        "Tag_label": mcr.get("Tag_label", None),
        "Tags_label": mcr.get("Tags_label", None),
        "Cidr": mcr.get("Cidr", None),
        "Fqdn": mcr.get("Fqdn", None),
        "Netbios": mcr.get("Netbios", None),
        "OsNames": mcr.get("OsNames", None),
        "Hostnames": mcr.get("Hostnames", None),
        "ProviderAccountId": mcr.get("ProviderAccountId", None),
        "ProviderAccountName": mcr.get("ProviderAccountName", None),
        "ResourceGroup": mcr.get("ResourceGroup", None),
        "AssetType": mcr.get("AssetType", None)
    }

    if not rule['RepositoryName'] and not rule['SearchName'] and not rule['Tags'] and not rule['Tag'] and not rule['Tag_rule'] and not rule['Tags_rule'] and not rule['Cidr']:
        print(f'Multicondition rule is missing any of (RepositoryName, SearchName, Tags, Tag, Tag_rule, Tags_rule, Cidr), skipping multicondition rule. Received MultiConditionRule: {mcr}')
        return None
    return rule


def load_multi_condition_rules(component):
    rules = []
    
    # Check all possible variations of multicondition rule keys
    rule_keys = [
        'MULTI_MultiConditionRules',
        'MultiMultiConditionRules',
        'MultiConditionRules',
        'MultiConditionRule'
    ]
    
    for key in rule_keys:
        if key in component and component[key]:
            # If it's a single rule, wrap it in a list
            rules_list = component[key] if isinstance(component[key], list) else [component[key]]
            for mcr in rules_list:
                rule = load_multi_condition_rule(mcr)
                if rule:
                    rules.append(rule)
    
    return rules if rules else None


def load_flag_for_create_users(resource_folder):
    core_structure = os.path.join(resource_folder, "core-structure.yaml")
    return load_flag_for_create_users_from_config(core_structure)


def load_flag_for_create_users_from_config(config_file_path):
    with open(config_file_path, 'r') as stream:
        repos_yaml = yaml.safe_load(stream)

    if True == repos_yaml.get('CreateUsersForApplications', "False"):
        return True
    return False


def load_ticketing(element):
    """
    Load ticketing configuration from element.
    Only accepts list format:
    Ticketing:
      - TIntegrationName: Jira-testphx
        Backlog: demoteam2
    """
    if 'Ticketing' not in element:
        return None
    
    ticketing = element.get('Ticketing')
    
    # Only accept list format
    if not isinstance(ticketing, list):
        print(f'Ticketing must be in list format. Current format: {type(ticketing)}')
        print('Example format:\nTicketing:\n  - TIntegrationName: Jira-testphx\n    Backlog: demoteam2')
        return None
    
    if not ticketing:  # Empty list
        return None
    
    # Get the first item from the list
    ticketing_config = ticketing[0]
    if not isinstance(ticketing_config, dict):
        print(f'Invalid ticketing configuration format: {ticketing_config}')
        return None
    
    # Support both old and new integration name fields
    integration_name = ticketing_config.get('TIntegrationName') or ticketing_config.get('IntegrationName')
    backlog = ticketing_config.get('Backlog')
    
    # Check for required fields
    if not backlog:
        print(f'Ticketing missing mandatory Backlog field: {ticketing_config}')
        return None
    
    if not integration_name:
        print(f'Ticketing missing integration name (TIntegrationName or IntegrationName): {ticketing_config}')
        return None
    
    if ticketing_config.get('IntegrationName') and not ticketing_config.get('TIntegrationName'):
        print(f'Warning: Using deprecated "IntegrationName" field in Ticketing. Please update to "TIntegrationName"')
    
    return ticketing


def load_messaging(element):
    """
    Load messaging configuration from element.
    Only accepts list format:
    Messaging:
      - MIntegrationName: Slack-phx
        Channel: int-tests
    """
    if 'Messaging' not in element:
        return None
    
    messaging = element.get('Messaging')
    
    # Only accept list format
    if not isinstance(messaging, list):
        print(f'Messaging must be in list format. Current format: {type(messaging)}')
        print('Example format:\nMessaging:\n  - MIntegrationName: Slack-phx\n    Channel: int-tests')
        return None
    
    if not messaging:  # Empty list
        return None
    
    # Get the first item from the list
    messaging_config = messaging[0]
    if not isinstance(messaging_config, dict):
        print(f'Invalid messaging configuration format: {messaging_config}')
        return None
    
    # Support both old and new integration name fields
    integration_name = messaging_config.get('MIntegrationName') or messaging_config.get('IntegrationName')
    channel = messaging_config.get('Channel')
    
    # Check for required fields
    if not channel:
        print(f'Messaging missing mandatory Channel field: {messaging_config}')
        return None
    
    if not integration_name:
        print(f'Messaging missing integration name (MIntegrationName or IntegrationName): {messaging_config}')
        return None
    
    if messaging_config.get('IntegrationName') and not messaging_config.get('MIntegrationName'):
        print(f'Warning: Using deprecated "IntegrationName" field in Messaging. Please update to "MIntegrationName"')
    
    return messaging


def load_run_config(resource_folder):
    default_config_files = ["core-structure.yaml"]
    config_file = os.path.join(resource_folder, 'run-config.yaml')
    if not resource_folder or not os.path.exists(config_file):
        config = {
            "ConfigFiles": default_config_files
        }
        print(f" ! Run config not provided via run-config.yaml, using default values: {config}")
        return config

    with open(config_file, 'r') as stream:
        config = yaml.safe_load(stream)

    if not 'ConfigFiles' in config:
        print(f" ! ConfigFiles not found in run-config.yaml, using default value: {default_config_files}")
        config['ConfigFiles'] = default_config_files
    
    return config


def print_linter_result(name, linter_result):
    print("****************************************")
    print("* Linter results")
    print("*")
    print(f"* {name} Is Valid: {linter_result[0]}")
    if linter_result[1]:
        print("*")
        print(f"* Linter errors: {linter_result[1]}")
    print("****************************************")


def load_remote_configuration_locations(resource_folder):
    if not resource_folder:
        print("Please supply path for the resources")
        return []

    repos_file = os.path.join(resource_folder, "run-config.yaml")

    with open(repos_file, 'r') as stream:
        repos_yaml = yaml.safe_load(stream)

    if not 'GitHubRepositories' in repos_yaml:
        print("run-config configuration is missing 'GitHubRepositories' property, will not load GitHub configurations")
        return []

    return repos_yaml['GitHubRepositories']


def load_github_repo_folder(resource_folder):
    if not resource_folder:
        print("Please supply path for the resources")
        return None

    repos_file = os.path.join(resource_folder, "run-config.yaml")

    with open(repos_file, 'r') as stream:
        repos_yaml = yaml.safe_load(stream)

    if not 'GitHubRepoFolder' in repos_yaml:
        raise Exception("run-config configuration is missing 'GitHubRepoFolder' property")

    return repos_yaml['GitHubRepoFolder']


def load_github_config_file_name(resource_folder):
    if not resource_folder:
        print("Please supply path for the resources")
        return None

    repos_file = os.path.join(resource_folder, "run-config.yaml")

    with open(repos_file, 'r') as stream:
        repos_yaml = yaml.safe_load(stream)

    if not 'ConfigFileName' in repos_yaml:
        raise Exception("run-config configuration is missing 'ConfigFileName' property")

    return repos_yaml['ConfigFileName']
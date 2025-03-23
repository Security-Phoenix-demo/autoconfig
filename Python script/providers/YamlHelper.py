import os
import yaml
from pathlib import Path
from providers.Utils import calculate_criticality
from email_validator import validate_email, EmailNotValidError

# Check if PyYAML module exists
try:
    import yaml
    print("Module exists")
except ImportError:
    print("Module does not exist. Installing...")
    os.system('pip install pyyaml')


# Function to populate repositories
def populate_repositories(resource_folder):
    repos = []

    if not resource_folder:
        print("Please supply path for the resources")
        return repos

    core_structure = os.path.join(resource_folder, "core-structure.yaml")

    with open(core_structure, 'r') as stream:
        repos_yaml = yaml.safe_load(stream)

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
                print(f'Created repository {repositoryName}')
                item = {
                    'RepositoryName': repositoryName,
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
    envs = []

    if not resource_folder:
        print("Please supply path for the resources")
        return envs

    banking_core = os.path.join(resource_folder, "core-structure.yaml")

    with open(banking_core, 'r') as stream:
        repos_yaml = yaml.safe_load(stream)

    for row in repos_yaml['Environment Groups']:
        # Define the environment item
        item = {
            'Name': row['Name'],
            'Type': row['Type'],
            'Criticality': calculate_criticality(row['Tier']),
            'CloudAccounts': [""],  # Add CloudAccounts if applicable
            'Status': row['Status'],
            'Responsable': row['Responsable'],
            'TeamName': row.get('TeamName', None),  # Add TeamName from the environment or set as None
            'Services': []  # To populate services later
        }

        # Now process the services under the "Team" or "Services" key
        if 'Services' in row:
            for service in row['Services']:
                repository_names = service.get('RepositoryName', [])
                if isinstance(repository_names, str):
                    repository_names = [repository_names]
                # Build the service entry with association details
                service_entry = {
                    'Service': service['Service'],
                    'Type': service['Type'],
                    'Tier': service.get('Tier', 5),  # Default tier to 5 if not specified
                    'TeamName': service.get('TeamName', item['TeamName']),  # Default to environment's TeamName if missing
                    'Deployment_set': service.get('Deployment_set', None),
                    'Deployment_tag': service.get('Deployment_tag', None),
                    'MultiConditionRule': load_multi_condition_rule(service.get('MultiConditionRule', None)),
                    'MultiConditionRules': load_multi_condition_rules(service),
                    'RepositoryName': repository_names,  # Properly handle missing 'RepositoryName'
                    'SearchName': service.get('SearchName', None),
                    "Tag": service.get("Tag", None),
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
    all_access_emails = []

    if not resource_folder:
        print("Please supply path for the resources")
        return all_access_emails

    core_structure = os.path.join(resource_folder, "core-structure.yaml")

    with open(core_structure, 'r') as stream:
        repos_yaml = yaml.safe_load(stream)

    return repos_yaml['AllAccessAccounts']

# Populate applications

# Populate applications
def populate_applications(resource_folder):
    apps = []

    if not resource_folder:
        print("Please supply path for the resources")
        return apps

    core_structure = os.path.join(resource_folder, "core-structure.yaml")

    with open(core_structure, 'r') as stream:
        apps_yaml = yaml.safe_load(stream)

    for row in apps_yaml['DeploymentGroups']:
        app = {
            'AppName': row['AppName'],
            'Status': row.get('Status', None),
            'TeamNames': row.get('TeamNames', []),
            'ReleaseDefinitions': row['ReleaseDefinitions'],
            'Responsable': row['Responsable'],
            'Criticality': calculate_criticality(row.get('Tier', 5)),  # Use .get() to handle missing 'Tier'
            'Deployment_set': row.get('Deployment_set', None),
            'Components': []
        }

        if not 'Components' in row:
            continue

        for component in row['Components']:
            # Handle RepositoryName properly
            repository_names = component.get('RepositoryName', [])
            if isinstance(repository_names, str):
                repository_names = [repository_names]

            comp = {
                'ComponentName': component['ComponentName'],
                'Status': component.get('Status', None),
                'Type': component.get('Type', None),
                'TeamNames': component.get('TeamNames', app['TeamNames']),  # Fallback to app's TeamNames if missing
                'RepositoryName': repository_names,  # Properly handle missing 'RepositoryName'
                'SearchName': component.get('SearchName', None),
                "Tags": component.get("Tags", None),
                "Cidr": component.get("Cidr", None),
                "Fqdn": component.get("Fqdn", None),
                "Netbios": component.get("Netbios", None),
                "OsNames": component.get("OsNames", None),
                "Hostnames": component.get("Hostnames", None),
                "ProviderAccountId": component.get("ProviderAccountId", None),
                "ProviderAccountName": component.get("ProviderAccountName", None),
                "ResourceGroup": component.get("ResourceGroup", None),
                "AssetType": component.get("AssetType", None),
                'MultiConditionRule': load_multi_condition_rule(component.get('MultiConditionRule', None)),
                'MultiConditionRules': load_multi_condition_rules(component),
                'Criticality': calculate_criticality(component.get('Tier', 5)),  # Handle missing 'Tier'
                'Domain': component.get('Domain', None),  # Handle missing 'Domain'
                'SubDomain': component.get('SubDomain', None),  # Handle missing 'SubDomain'
                'AutomaticSecurityReview': component.get('AutomaticSecurityReview', None)  # Handle missing 'AutomaticSecurityReview'
            }
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

    if not rule['RepositoryName'] and not rule['SearchName'] and not rule['Tags'] and not rule['Tag'] and not rule['Cidr']:
        print(f'Multicondition rule is missing any of (RepositoryName, SearchName, Tags, Tag, Cidr), skipping multicondition rule. Received MultiConditionRule: {mcr}')
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
    with open(core_structure, 'r') as stream:
        repos_yaml = yaml.safe_load(stream)

    if True == repos_yaml.get('CreateUsersForApplications', "False"):
        return True
    return False
from itertools import groupby

# Function to populate unique domains from a list of repos
def populate_domains(repos):
    domains = []
    for repo in repos:
        dom= repo['Domain']
        if dom not in domains:
            domains.append(dom)
    return domains

# Function to retrieve unique subdomains from repos
def get_subdomains(repos):
    subdomains = []
    for repo in repos:
        if not any(item['Name'] == repo['Subdomain'] for item in subdomains):
            item = {
                'Name': repo['Subdomain'],
                'Domain': repo['Domain'],
                'Tier': repo['Tier']
            }
            subdomains.append(item)
    return subdomains

# Function to get the environment ID based on environment name
def get_environment_id(application_environments, environment_name):
    env = next((env for env in application_environments if env['name'] == environment_name and env['type'] == 'ENVIRONMENT'), None)
    return env['id'] if env else None

# Function to check if a service exists in a given environment
def environment_service_exist(env_id, phoenix_components, servicename):
    for component in phoenix_components:
        if component['applicationId'] == env_id and component['name'] == servicename:
            return True
    return False


# Function to calculate criticality based on tier value Tier 1 is the most critical tier 10 is the least critical, tier 6 is neutral tier 
def calculate_criticality(tier):
    criticality = 5
    if tier == 1:
        criticality = 10
    elif tier == 2:
        criticality = 9
    elif tier == 3:
        criticality = 8
    elif tier == 4:
        criticality = 7
    elif tier == 5:
        criticality = 6
    elif tier == 6:
        criticality = 5
    elif tier == 7:
        criticality = 4
    elif tier == 8:
        criticality = 3
    elif tier == 9:
        criticality = 2
    elif tier == 10:
        criticality = 1
    return criticality

# Function to populate users who have access to all teams
def populate_users_with_all_team_access(teams, defaultAllAccessAccounts):
    print("Populating the users with all team Access")
    all_access = []
    for team in teams:
        try:
            if team['TeamName'] in ["staffs", "principals", "directors"]:
                for member in team['TeamMembers']:
                    all_access.append(member['EmailAddress'])
        except Exception as e:
            print(str(e))
            exit(1)
    #this gives super user access to the ciso or who else wants access
    print(f'Add default all access accounts: {defaultAllAccessAccounts}')
    all_access.extend(defaultAllAccessAccounts)
    return all_access

# Function to check if a member exists in the given team or override list
def does_member_exist(email, team, hive_staff, all_team_access):
    override_list = ["admin1@company.com", "admin1@company.com"]
    
    if email in override_list or email in all_team_access:
        return True
    
    for member in team['TeamMembers']:
        if email == member['EmailAddress']:
            return True
    
    hive_staff_member = next((staff for staff in hive_staff if staff['Lead'] == email or email in staff['Product']), None)
    
    return hive_staff_member is not None

# Function to group repos by 'Subdomain' key
def group_repos_by_subdomain(repos):
    # sort INFO data by 'company' key.
    sorted_repos = sorted(repos, key=lambda k: k['Subdomain'])
 
    return groupby(sorted_repos, lambda k: k['Subdomain'])

    
def extract_user_name_from_email(email):
    try:
        email_parts = email.split("@")
    except Exception as e:
        print(f'  ! Failed to extract name from email {email}, error {e}')
        return (None, None)
    
    if len(email_parts) < 2:
        print(f'  ! Failed to extract name from email {email}, @ sign not found in email')
        return (None, None)
    
    user_full_name = email_parts[0]
    user_first_name = user_full_name
    user_last_name = user_full_name
    try:
        user_full_name_parts = user_full_name.split(".")
        if len(user_full_name_parts) > 1:
            user_first_name = user_full_name_parts[0]
            user_last_name = user_full_name_parts[1]
    except Exception as e:
        print(f"Unable to detect user's first and last name in {email}, using {user_full_name} as both first and last name")
    return (user_first_name, user_last_name)


def validate_user_role(user_role):
    allowed_roles = ["ORG_ADMIN", "ORG_APP_ADMIN", "ORG_USER", 
                    "ORG_ADMIN_LITE", "ORG_SEC_ADMIN", "ORG_SEC_DEV"]
    
    if not any(allowed_role == user_role for allowed_role in allowed_roles):
        raise Exception(f"Invalid user role, received {user_role}, allowed roles: {allowed_roles}")
    

def add_PAT_to_github_repo_url(pat, repo_url):
    # update the repo_url to contain the PAT right after https://
    # only for github repos
    if "https://github.com" in repo_url:
        return repo_url[:8] + pat + "@" + repo_url[8:]
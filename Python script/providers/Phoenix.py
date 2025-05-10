import base64
import requests
import json
import time
import Levenshtein
import random
from multipledispatch import dispatch
from providers.Utils import group_repos_by_subdomain, calculate_criticality, extract_user_name_from_email, validate_user_role
import logging
import datetime

# Configure logging
logging.basicConfig(
    filename='errors.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_error(operation_type, name, environment, error_msg, details=None):
    """
    Log error information to errors.log
    
    Args:
        operation_type: Type of operation (e.g., 'Service Creation', 'Rule Creation')
        name: Name of the service/component/rule
        environment: Environment name
        error_msg: Error message
        details: Additional details (optional)
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    error_entry = f"""
TIME: {timestamp}
OPERATION: {operation_type}
NAME: {name}
ENVIRONMENT: {environment}
ERROR: {error_msg}
"""
    if details:
        error_entry += f"DETAILS: {details}\n"
    error_entry += "-" * 80 + "\n"
    
    logging.error(error_entry)

AUTOLINK_DEPLOYMENT_SIMILARITY_THRESHOLD = 1 # Levenshtein ratio for comparing app name with service name. (1 means being equal)
SERVICE_LOOKUP_SIMILARITY_THRESHOLD = 0.99 # Levenshtein ratio for comparing service name with existing services, in case service was not found by exact match
ASSET_NAME_SIMILARITY_THRESHOLD = 1 # Levenshtein ratio for comparing asset name similarity (1 means being equal)
ASSET_GROUP_MIN_SIZE_FOR_COMPONENT_CREATION = 5 # Minimal number of assets with similar name that will trigger component creation

APIdomain = "https://api.demo.appsecphx.io/" #change this with your specific domain
DEBUG = False #debug settings to trigger debug output 

def get_auth_token(clientID, clientSecret, retries=3):
    credentials = f"{clientID}:{clientSecret}".encode('utf-8')
    base64_credentials = base64.b64encode(credentials).decode('utf-8')
    
    headers = {
        'Authorization': f'Basic {base64_credentials}'
    }
    token_url = f"{APIdomain}/v1/auth/access_token"
    
    print(f"Making request to {token_url} to obtain token.")
    
    for attempt in range(retries):
        try:
            response = requests.get(token_url, headers=headers)
            response.raise_for_status()
            return response.json().get('token')
        except requests.exceptions.RequestException as e:
            print(f"Error obtaining token (Attempt {attempt+1}/{retries}): {e}")
            time.sleep(2)  # Wait for 2 seconds before retrying
    
    print(f"Failed to obtain token after {retries} attempts.")
    exit(1)

def construct_api_url(endpoint):
    return f"{APIdomain}{endpoint}"

def create_environment(environment, headers):
    print("[Environment]")
    print(f"└─ Creating: {environment['Name']}")

    payload = {
        "name": environment['Name'],
        "type": "ENVIRONMENT",
        "subType": environment['Type'],
        "criticality": environment['Criticality'],
        "owner": {
            "email": environment['Responsable']
        },
        "tags": []
    }

    # Add status tag
    if environment['Status']:
        payload["tags"].append({"key": "status", "value": environment['Status']})

    # Add team_name tag only if it's provided
    if environment['TeamName']:
        payload["tags"].append({"key": "pteam", "value": environment['TeamName']})
    else:
        print(f"└─ Warning: No team_name provided for environment {environment['Name']}. Skipping pteam tag.")

    # Handle ticketing configuration
    if environment.get('Ticketing'):
        ticketing = environment['Ticketing']
        if isinstance(ticketing, list):
            ticketing = ticketing[0] if ticketing else {}
        
        if ticketing.get('Backlog'):  # Only add if Backlog is present
            payload["ticketing"] = {
                "integrationName": ticketing.get('TIntegrationName'),
                "projectName": ticketing.get('Backlog')  # This is required
            }
        else:
            print(f"└─ Warning: Skipping ticketing configuration - missing required Backlog field")

    # Handle messaging configuration
    if environment.get('Messaging'):
        messaging = environment['Messaging']
        if isinstance(messaging, list):
            messaging = messaging[0] if messaging else {}
        
        if messaging.get('Channel'):  # Only add if Channel is present
            payload["messaging"] = {
                "integrationName": messaging.get('MIntegrationName'),
                "channelName": messaging.get('Channel')
            }
        else:
            print(f"└─ Warning: Skipping messaging configuration - missing required Channel field")

    try:
        api_url = construct_api_url("/v1/applications")
        print(f"└─ Sending payload:")
        print(f"   └─ {json.dumps(payload, indent=2)}")
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"└─ Environment added successfully: {environment['Name']}")
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to create environment: {str(e)}"
        error_details = f'Response: {getattr(response, "content", "No response content")}\nPayload: {json.dumps(payload)}'
        log_error(
            'Environment Creation',
            environment['Name'],
            'N/A',
            error_msg,
            error_details
        )
        print(f"└─ Error: {error_msg}")
        if DEBUG:
            print(f"└─ Response content: {error_details}")

def update_environment(environment, existing_environment, headers):
    payload = {}
    has_errors = False

    # Handle ticketing configuration
    if environment.get('Ticketing'):
        try:
            ticketing = environment['Ticketing']
            if isinstance(ticketing, list):
                ticketing = ticketing[0] if ticketing else {}
            
            integration_name = ticketing.get('TIntegrationName')
            project_name = ticketing.get('Backlog')

            if integration_name and project_name:
                payload["ticketing"] = {
                    "integrationName": integration_name,
                    "projectName": project_name
                }
                print(f"└─ Adding ticketing configuration:")
                print(f"   └─ Integration: {integration_name}")
                print(f"   └─ Project: {project_name}")
            else:
                has_errors = True
                print(f"└─ Warning: Ticketing configuration missing required fields")
                print(f"   └─ TIntegrationName: {integration_name}")
                print(f"   └─ Backlog: {project_name}")
        except Exception as e:
            has_errors = True
            error_msg = f"Failed to process ticketing configuration: {str(e)}"
            log_error(
                'Ticketing Config',
                environment['Name'],
                'N/A',
                error_msg
            )
            print(f"└─ Warning: {error_msg}")

    # Handle messaging configuration
    if environment.get('Messaging'):
        try:
            messaging = environment['Messaging']
            if isinstance(messaging, list):
                messaging = messaging[0] if messaging else {}
            
            integration_name = messaging.get('MIntegrationName')
            channel_name = messaging.get('Channel')

            if integration_name and channel_name:
                payload["messaging"] = {
                    "integrationName": integration_name,
                    "channelName": channel_name
                }
                print(f"└─ Adding messaging configuration:")
                print(f"   └─ Integration: {integration_name}")
                print(f"   └─ Channel: {channel_name}")
            else:
                has_errors = True
                print(f"└─ Warning: Messaging configuration missing required fields")
                print(f"   └─ MIntegrationName: {integration_name}")
                print(f"   └─ Channel: {channel_name}")
        except Exception as e:
            has_errors = True
            error_msg = f"Failed to process messaging configuration: {str(e)}"
            log_error(
                'Messaging Config',
                environment['Name'],
                'N/A',
                error_msg
            )
            print(f"└─ Warning: {error_msg}")
    
    if not payload:
        if DEBUG:
            print(f'No changes detected to update environment {environment["Name"]}')
        return
    
    try:
        api_url = construct_api_url(f"/v1/applications/{existing_environment['id']}")
        print(f"Payload for environment update: {json.dumps(payload, indent=2)}")
        response = requests.patch(api_url, headers=headers, json=payload)
        response.raise_for_status()
        print(f" + Environment updated: {environment['Name']}")
    except requests.exceptions.RequestException as e:
        has_errors = True
        error_msg = f"Failed to update environment: {str(e)}"
        log_error(
            'Environment Update',
            environment['Name'],
            'N/A',
            error_msg,
            details={'payload': payload}
        )
        print(f"└─ Error: {error_msg}")
        if hasattr(response, 'content'):
            print(f"Response content: {response.content}")
        # Don't raise the exception, just log it and continue

# Function to add services and process rules for the environment
def add_environment_services(repos, subdomains, environments, application_environments, phoenix_components, subdomain_owners, teams, access_token):
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}

    for environment in environments:
        env_name = environment['Name']
        env_id = get_environment_id(application_environments, env_name)
        if not env_id:
            print(f"[Services] Environment {env_name} doesn't have ID! Skipping service and rule creation")
            continue
        print(f"[Services] for {env_name}:{env_id}")

        if environment['Services']:
            for service in environment['Services']:
                team_name = service.get('TeamName', None)
                service_name = service['Service']
                
                # First verify if service exists with thorough check
                exists, service_id = verify_service_exists(env_name, env_id, service_name, headers)
                
                if not exists:
                    print(f" > Service {service_name} does not exist, attempting to create...")
                    creation_success = False
                    try:
                        if team_name:
                            creation_success = add_service(env_name, env_id, service, service['Tier'], team_name, headers)
                        else:
                            creation_success = add_service(env_name, env_id, service, service['Tier'], headers)
                    except NotImplementedError as e:
                        print(f"Error adding service {service_name} for environment {env_name}: {e}")
                        continue
                        
                    if not creation_success:
                        print(f" ! Failed to create service {service_name}, skipping rule creation")
                        continue
                        
                    # Re-verify after creation
                    exists, service_id = verify_service_exists(env_name, env_id, service_name, headers)
                    if not exists:
                        print(f" ! Service {service_name} creation verified failed, skipping rule creation")
                        continue
                else:
                    update_service(service, service_id, headers)
                
                print(f" > Service {service_name} verified, updating rules...")
                # Always update rules if service exists and is verified
                add_service_rule_batch(application_environments, environment, service, service_id, headers)
                time.sleep(1)  # Add small delay between operations

# AddContainerRule Function
def add_container_rule(image, subdomain, environment_name, access_token):
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}

    rules = [{
        "name": image,
        "filter": {"keyLike": f"*{image}*"}
    }]
    payload = {
        "selector": {
            "applicationSelector": {"name": environment_name, "caseSensitive": False},
            "componentSelector": {"name": subdomain, "caseSensitive": False}
        },
        "rules": rules
    }

def add_service_rule_batch(application_environments, environment, service, service_id, headers):
    serviceName = service['Service']
    environmentName = environment['Name']
    env_id = get_environment_id(application_environments, environmentName)
    # First verify that the service exists and get its ID
    if not service_id:
        exists, service_id = verify_service_exists(environmentName, env_id, serviceName, headers)
    else:
        exists = True
    
    if not exists:
        print(f" ! Service {serviceName} not found, cannot create rules")
        return False

    print(f" > Creating rules for service {serviceName} (ID: {service_id})")

    # First, delete existing rules for this service
    try:
        api_url = construct_api_url(f"/v1/components/rules")
        # Get existing rules using the service name
        params = {
            "applicationSelector": {"name": environmentName, "caseSensitive": False},
            "componentSelector": {"name": serviceName, "caseSensitive": False}
        }
            
        response = requests.get(api_url, headers=headers, params=params)
        if response.status_code == 200:
            existing_rules = response.json()
            # Delete each existing rule
            for rule in existing_rules:
                if rule.get('id'):
                    delete_url = construct_api_url(f"/v1/components/rules/{rule['id']}")
                    delete_response = requests.delete(delete_url, headers=headers)
                    if delete_response.status_code == 200:
                        print(f" - Deleted existing rule for {serviceName}")
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed cleaning existing rules: {str(e)}"
        error_details = f'Response: {getattr(response, "content", "No response content")}'
        log_error(
            'Existing Rules Cleanup',
            serviceName,
            environmentName,
            error_msg,
            error_details
        )
        print(f"└─ Error: {error_msg}")
        if DEBUG:
            print(f"└─ Response content: {error_details}")
    # Now proceed with creating new rules
    success = True

    # Handle INFRA services with CIDR association (IP-based)
    if service.get('Cidr') and service['Type'] == 'Infra':
        print(f"Adding Service Rule {serviceName} to {environmentName} for Cidr")
        
        cidrs = [cidr.strip() for cidr in service['Cidr'].split(",") if cidr.strip()]
        
        if not cidrs:
            print(f"Error: No valid CIDR values found for {serviceName}.")
            return False
        
        for index, cidr in enumerate(cidrs, start=1):
            # Ensure proper CIDR formatting
            if '/' not in cidr:
                finalCidr = f"{cidr}/32"  # Default to /32 if no CIDR mask provided
            else:
                finalCidr = cidr

            payload = {
                "selector": {
                    "applicationSelector": {
                        "name": environmentName,
                        "caseSensitive": False
                    },
                    "componentSelector": {
                        "name": serviceName,
                        "caseSensitive": False
                    }
                },
                "rules": [
                    {
                        "name": f"CIDR rule for {serviceName} - {index}",
                        "filter": {
                            "assetType": "INFRA",
                            "cidr": finalCidr
                        }
                    }
                ]
            }

            try:
                api_url = construct_api_url("/v1/components/rules")
                response = requests.post(api_url, headers=headers, json=payload)
                response.raise_for_status()
                print(f"+ CIDR Rule {index} for {finalCidr} added to {serviceName}.")
            except requests.exceptions.RequestException as e:
                print(f"Error creating CIDR rule: {e}")
                print(f"Response content: {response.content}")
                success = False

    # Handle other rules
    for rule_type, rule_key, rule_value in [
        ('Tag', 'tags', service.get('Tag')),
        ('SearchName', 'keyLike', service.get('SearchName')),
        ('Fqdn', 'fqdn', service.get('Fqdn')),
        ('Netbios', 'netbios', service.get('Netbios')),
        ('OsNames', 'osNames', service.get('OsNames')),
        ('Hostnames', 'hostnames', service.get('Hostnames')),
        ('ProviderAccountId', 'providerAccountId', service.get('ProviderAccountId')),
        ('ProviderAccountName', 'providerAccountName', service.get('ProviderAccountName')),
        ('ResourceGroup', 'resourceGroup', service.get('ResourceGroup')),
        ('AssetType', 'assetType', service.get('AssetType'))
    ]:
        if rule_value:
            try:
                if rule_type == 'Tag':
                    tag_value = rule_value
                    if isinstance(tag_value, list):
                        for tag_item in tag_value:
                            if ':' in tag_item:
                                tag_parts = tag_item.split(':')
                                if len(tag_parts) >= 2:
                                    rule_result = create_component_rule(
                                        environmentName, 
                                        serviceName, 
                                        'tags', 
                                        [{"key": tag_parts[0].strip(), "value": tag_parts[1].strip()}],
                                        f"Rule for tag {tag_parts[0]}:{tag_parts[1]} for {serviceName}", 
                                        headers
                                    )
                                    success = success and (rule_result if rule_result is not None else False)
                    else:
                        if ':' in tag_value:
                            tag_parts = tag_value.split(':')
                            if len(tag_parts) >= 2:
                                rule_result = create_component_rule(
                                    environmentName, 
                                    serviceName, 
                                    'tags', 
                                    [{"key": tag_parts[0].strip(), "value": tag_parts[1].strip()}],
                                    f"Rule for tag {tag_parts[0]}:{tag_parts[1]} for {serviceName}", 
                                    headers
                                )
                                success = success and (rule_result if rule_result is not None else False)
                else:
                    rule_result = create_component_rule(
                        environmentName, 
                        serviceName, 
                        rule_key, 
                        rule_value, 
                        f"Rule for {rule_type} for {serviceName}", 
                        headers
                    )
                    success = success and (rule_result if rule_result is not None else False)
            except Exception as e:
                print(f"Error creating {rule_type} rule: {e}")
                success = False

    # Handle MultiCondition rules
    for rule_type in ['MultiConditionRule', 'MultiConditionRules', 'MULTI_MultiConditionRules', 'MultiMultiConditionRules']:
        if service.get(rule_type):
            try:
                create_multicondition_service_rules(environmentName, serviceName, service.get(rule_type), headers)
            except Exception as e:
                print(f"  └─ Error creating multicondition rule: {e}")
                error_msg = f"Failed to create multicondition rule for service: {str(e)}"
                log_error(
                    "Service Rule Creation",
                    serviceName,
                    environmentName,
                    error_msg,
                    f" Multicondition rule info from {rule_type} is {service.get(rule_type)}"
                )
                success = False

    return success

# AddServiceRule Function
def add_service_rule(environment, service, tag_name, tag_value, access_token):
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}


    print(f"Adding Service Rule {service} tag {tag_value}")

    payload = {
        "selector": {
            "applicationSelector": {"name": environment['Name'], "caseSensitive": False},
            "componentSelector": {"name": service, "caseSensitive": False}
        },
        "rules": [{
            "name": f"{tag_name} {tag_value}",
            "filter": {
                "tags": [{"key":tag_name, "value":tag_value}],
                "providerAccountId": environment['CloudAccounts']
            }
        }]
        
    }
    if DEBUG:
            print(f"Payload being sent to /v1rule: {json.dumps(payload, indent=2)}")


def create_applications(applications, application_environments, phoenix_components, headers):
    print('[Applications]')
    for application in applications:
        if not any(env['name'] == application['AppName'] and env['type'] == "APPLICATION" for env in application_environments):
            create_application(application, headers)
        else:
            update_application(application, application_environments, phoenix_components, headers)


def create_application(app, headers):
    print(f"\n[Application Creation]")
    print(f"└─ Creating: {app['AppName']}")
    
    payload = {
        "name": app['AppName'],
        "type": "APPLICATION",
        "criticality": app['Criticality'],
        "tags": [],
        "owner": {"email": app['Responsable']}
    }

    # Handle ticketing configuration
    if app.get('Ticketing'):
        try:
            ticketing = app['Ticketing']
            if isinstance(ticketing, list):
                ticketing = ticketing[0] if ticketing else {}
            
            integration_name = ticketing.get('TIntegrationName')
            project_name = ticketing.get('Backlog')

            if integration_name and project_name:
                payload["ticketing"] = {
                    "integrationName": integration_name,
                    "projectName": project_name
                }
                print(f"└─ Adding ticketing configuration:")
                print(f"   └─ Integration: {integration_name}")
                print(f"   └─ Project: {project_name}")
            else:
                print(f"└─ Warning: Ticketing configuration missing required fields")
                print(f"   └─ TIntegrationName: {integration_name}")
                print(f"   └─ Backlog: {project_name}")
        except Exception as e:
            error_msg = f"Failed to process ticketing configuration: {str(e)}"
            log_error(
                'Ticketing Config',
                app['AppName'],
                'N/A',
                error_msg
            )
            print(f"└─ Warning: {error_msg}")

    # Handle messaging configuration
    if app.get('Messaging'):
        try:
            messaging = app['Messaging']
            if isinstance(messaging, list):
                messaging = messaging[0] if messaging else {}
            
            integration_name = messaging.get('MIntegrationName')
            channel_name = messaging.get('Channel')

            if integration_name and channel_name:
                payload["messaging"] = {
                    "integrationName": integration_name,
                    "channelName": channel_name
                }
                print(f"└─ Adding messaging configuration:")
                print(f"   └─ Integration: {integration_name}")
                print(f"   └─ Channel: {channel_name}")
            else:
                print(f"└─ Warning: Messaging configuration missing required fields")
                print(f"   └─ MIntegrationName: {integration_name}")
                print(f"   └─ Channel: {channel_name}")
        except Exception as e:
            error_msg = f"Failed to process messaging configuration: {str(e)}"
            log_error(
                'Messaging Config',
                app['AppName'],
                'N/A',
                error_msg
            )
            print(f"└─ Warning: {error_msg}")

    # Add team tags
    for team in app['TeamNames']:
        payload['tags'].append({"key": "pteam", "value": team})
                    
    if DEBUG:
        print(f"└─ Final payload:")
        print(json.dumps(payload, indent=2))

    try:
        api_url = construct_api_url("/v1/applications")
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"└─ Application created successfully")
        time.sleep(2)
    except requests.exceptions.RequestException as e:
        if response.status_code == 409:
            print(f"└─ Application {app['AppName']} already exists")
        else:
            error_msg = f"Failed to create application: {str(e)}"
            error_details = f'Response: {getattr(response, "content", "No response content")}\nPayload: {json.dumps(payload)}'
            log_error(
                'Application Creation',
                app['AppName'],
                'N/A',
                error_msg,
                error_details
            )
            print(f"└─ Error: {error_msg}")
            if DEBUG:
                print(f"└─ Response content: {response.content}")
            return
    
    # Create components if any
    if app.get('Components'):
        print(f"└─ Processing {len(app['Components'])} components")
        for component in app['Components']:
            create_custom_component(app['AppName'], component, headers)

def create_custom_component(applicationName, component, headers):
    print(f"\n[Component Creation]")
    print(f"└─ Application: {applicationName}")
    print(f"└─ Component: {component['ComponentName']}")

    # Ensure valid tag values by filtering out empty or None 
    tags = []
    
    if component.get('Status'):
        tags.append({"key": "Status", "value": component['Status']})
    if component.get('Type'):
        tags.append({"key": "Type", "value": component['Type']})

    # Add team tags
    for team in component.get('TeamNames', []):
        if team:  # Only add non-empty team names
            tags.append({"key": "pteam", "value": team})

    # Add domain and subdomain tags only if they are not None or empty
    if component.get('Domain'):
        tags.append({"key": "domain", "value": component['Domain']})
    if component.get('SubDomain'):
        tags.append({"key": "subdomain", "value": component['SubDomain']})

    payload = {
        "applicationSelector": {
            "name": applicationName
        },
        "name": component['ComponentName'],
        "criticality": component.get('Criticality', 5),  # Default to criticality 5
        "tags": tags
    }

    # Handle ticketing configuration
    if component.get('Ticketing'):
        ticketing = component['Ticketing']
        if isinstance(ticketing, list):
            ticketing = ticketing[0] if ticketing else {}
        
        if ticketing.get('Backlog'):  # Only add if Backlog is present
            payload["ticketing"] = {
                "integrationName": ticketing.get('TIntegrationName'),
                "projectName": ticketing.get('Backlog')  # This is required
            }
        else:
            print(f"└─ Warning: Skipping ticketing configuration - missing required Backlog field")

    # Handle messaging configuration
    if component.get('Messaging'):
        messaging = component['Messaging']
        if isinstance(messaging, list):
            messaging = messaging[0] if messaging else {}
        
        if messaging.get('Channel'):  # Only add if Channel is present
            payload["messaging"] = {
                "integrationName": messaging.get('MIntegrationName'),
                "channelName": messaging.get('Channel')
            }
        else:
            print(f"└─ Warning: Skipping messaging configuration - missing required Channel field")

    if DEBUG:
        print(f"└─ Sending payload:")
        print(f"   └─ {json.dumps(payload, indent=2)}")

    api_url = construct_api_url("/v1/components")

    try:
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"└─ Component created successfully")
        time.sleep(2)
    except requests.exceptions.RequestException as e:
        if response.status_code == 409:
            print(f"└─ Component already exists")
        else:
            error_msg = f"Failed to create component: {str(e)}"
            error_details = f'Response: {getattr(response, "content", "No response content")}\nPayload: {json.dumps(payload)}'
            log_error(
                'Component Creation',
                f"{applicationName} -> {component['ComponentName']}",
                'N/A',
                error_msg,
                error_details
            )
            print(f"└─ Error: {error_msg}")
            if DEBUG:
                print(f"└─ Response content: {response.content}")
            return

    try:
        create_component_rules(applicationName, component, headers)
    except Exception as e:
        error_msg = f"Failed to create component rules: {str(e)}"
        log_error(
            'Component Rules Creation',
            f"{applicationName} -> {component['ComponentName']}",
            'N/A',
            error_msg
        )
        print(f"└─ Warning: {error_msg}")

def update_application(application, existing_apps_envs, existing_components, headers):
    print(f"\n[Application Update]")
    print(f"└─ Processing: {application['AppName']}")
    
    # Find the existing application
    existing_app = next((app for app in existing_apps_envs if app['name'] == application['AppName'] and app['type'] == 'APPLICATION'), None)
    if not existing_app:
        error_msg = f"Application {application['AppName']} not found for update"
        log_error(
            'Application Update',
            application['AppName'],
            'N/A',
            error_msg,
            'Application missing during update'
        )
        print(f"└─ Warning: {error_msg}")
        return

    # Update teams and criticality first
    try:
        update_application_teams(existing_app, application, headers)
    except Exception as e:
        error_msg = f"Failed to update teams: {str(e)}"
        log_error(
            'Team Update',
            application['AppName'],
            'N/A',
            error_msg
        )
        print(f"└─ Warning: {error_msg}")

    try:
        update_application_crit_owner(application, existing_app, headers)
    except Exception as e:
        error_msg = f"Failed to update criticality/owner: {str(e)}"
        log_error(
            'Criticality/Owner Update',
            application['AppName'],
            'N/A',
            error_msg
        )
        print(f"└─ Warning: {error_msg}")

    payload = {}
    has_changes = False

    # Handle ticketing configuration
    if application.get('Ticketing'):
        try:
            ticketing = application['Ticketing']
            if isinstance(ticketing, list):
                ticketing = ticketing[0] if ticketing else {}
            
            if ticketing:
                integration_name = ticketing.get('TIntegrationName')
                project_name = ticketing.get('Backlog')

                if not integration_name or not project_name:
                    print(f"└─ Warning: Ticketing configuration missing required fields")
                    print(f"   └─ TIntegrationName: {integration_name}")
                    print(f"   └─ Backlog: {project_name}")
                else:
                    payload["ticketing"] = {
                        "integrationName": integration_name,
                        "projectName": project_name
                    }
                    has_changes = True
                    print(f"└─ Adding ticketing configuration:")
                    print(f"   └─ Integration: {integration_name}")
                    print(f"   └─ Project: {project_name}")
        except Exception as e:
            error_msg = f"Failed to process ticketing configuration: {str(e)}"
            log_error(
                'Ticketing Config',
                application['AppName'],
                'N/A',
                error_msg
            )
            print(f"└─ Warning: {error_msg}")

    # Handle messaging configuration
    if application.get('Messaging'):
        try:
            messaging = application['Messaging']
            if isinstance(messaging, list):
                messaging = messaging[0] if messaging else {}
            
            if messaging:
                integration_name = messaging.get('MIntegrationName')
                channel_name = messaging.get('Channel')

                if not integration_name or not channel_name:
                    print(f"└─ Warning: Messaging configuration missing required fields")
                    print(f"   └─ MIntegrationName: {integration_name}")
                    print(f"   └─ Channel: {channel_name}")
                else:
                    payload["messaging"] = {
                        "integrationName": integration_name,
                        "channelName": channel_name
                    }
                    has_changes = True
                    print(f"└─ Adding messaging configuration:")
                    print(f"   └─ Integration: {integration_name}")
                    print(f"   └─ Channel: {channel_name}")
        except Exception as e:
            error_msg = f"Failed to process messaging configuration: {str(e)}"
            log_error(
                'Messaging Config',
                application['AppName'],
                'N/A',
                error_msg
            )
            print(f"└─ Warning: {error_msg}")

    # Only proceed with update if there are changes
    if has_changes and payload:
        try:
            api_url = construct_api_url(f"/v1/applications/{existing_app['id']}")
            print(f"└─ Updating application with:")
            print(f"   └─ {json.dumps(payload, indent=2)}")
            response = requests.patch(api_url, headers=headers, json=payload)
            response.raise_for_status()
            print(f"└─ Application configuration updated successfully")
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to update application configuration: {str(e)}"
            error_details = f'Response: {getattr(response, "content", "No response content")}\nPayload: {json.dumps(payload)}'
            log_error(
                'Application Config Update',
                application['AppName'],
                'N/A',
                error_msg,
                error_details
            )
            print(f"└─ Warning: {error_msg}")
            if DEBUG:
                print(f"└─ Response content: {getattr(response, 'content', 'No response content')}")

    # Update components if needed
    if 'Components' in application:
        print(f"└─ Processing {len(application['Components'])} components")
        for component in application['Components']:
            try:
                existing_component = next((comp for comp in existing_components 
                                        if comp['name'] == component['ComponentName'] 
                                        and comp['applicationId'] == existing_app['id']), None)
                if existing_component:
                    print(f"   └─ Updating component: {component['ComponentName']}")
                    update_component(application, component, existing_component, headers)
                else:
                    print(f"   └─ Creating new component: {component['ComponentName']}")
                    create_custom_component(application['AppName'], component, headers)
            except Exception as e:
                error_msg = f"Failed to process component {component.get('ComponentName', 'Unknown')}: {str(e)}"
                log_error(
                    'Component Update',
                    f"{application['AppName']} -> {component.get('ComponentName', 'Unknown')}",
                    'N/A',
                    error_msg
                )
                print(f"   └─ Warning: {error_msg}")
                continue  # Continue with next component

    print(f"└─ Completed processing application: {application['AppName']}")

def update_component(application, component, existing_component, headers):
    print(f"\n[Component Update]")
    print(f"└─ Application: {application['AppName']}")
    print(f"└─ Component: {component['ComponentName']}")

    # Handle team tags
    try:
        for team in filter(lambda tag: tag.get('key') == 'pteam', existing_component.get('tags', [])):
            if team.get('value') not in component.get('TeamNames', []):
                remove_tag_from_component(team.get('id'), team.get('key'), team.get('value'), existing_component.get('id'), headers)
    except Exception as e:
        error_msg = f"Failed to update team tags: {str(e)}"
        log_error(
            'Team Tags Update',
            f"{application['AppName']} -> {component['ComponentName']}",
            'N/A',
            error_msg
        )
        print(f"└─ Warning: {error_msg}")

    payload = {
        "name": component['ComponentName'],
        "criticality": component.get('Criticality', 5),  # Default to criticality 5
        "tags": []
    }

    # Handle ticketing configuration
    if component.get('Ticketing'):
        try:
            ticketing = component['Ticketing']
            if isinstance(ticketing, list):
                ticketing = ticketing[0] if ticketing else {}
            
            if ticketing:
                integration_name = ticketing.get('TIntegrationName')
                project_name = ticketing.get('Backlog')

                if not integration_name or not project_name:
                    print(f"└─ Warning: Ticketing configuration missing required fields")
                    print(f"   └─ TIntegrationName: {integration_name}")
                    print(f"   └─ Backlog: {project_name}")
                else:
                    payload["ticketing"] = {
                        "integrationName": integration_name,
                        "projectName": project_name
                    }
                    print(f"└─ Adding ticketing configuration:")
                    print(f"   └─ Integration: {integration_name}")
                    print(f"   └─ Project: {project_name}")
        except Exception as e:
            error_msg = f"Failed to process ticketing configuration: {str(e)}"
            log_error(
                'Ticketing Config',
                f"{application['AppName']} -> {component['ComponentName']}",
                'N/A',
                error_msg
            )
            print(f"└─ Warning: {error_msg}")

    # Handle messaging configuration
    if component.get('Messaging'):
        try:
            messaging = component['Messaging']
            if isinstance(messaging, list):
                messaging = messaging[0] if messaging else {}
            
            if messaging:
                integration_name = messaging.get('MIntegrationName')
                channel_name = messaging.get('Channel')

                if not integration_name or not channel_name:
                    print(f"└─ Warning: Messaging configuration missing required fields")
                    print(f"   └─ MIntegrationName: {integration_name}")
                    print(f"   └─ Channel: {channel_name}")
                else:
                    payload["messaging"] = {
                        "integrationName": integration_name,
                        "channelName": channel_name
                    }
                    print(f"└─ Adding messaging configuration:")
                    print(f"   └─ Integration: {integration_name}")
                    print(f"   └─ Channel: {channel_name}")
        except Exception as e:
            error_msg = f"Failed to process messaging configuration: {str(e)}"
            log_error(
                'Messaging Config',
                f"{application['AppName']} -> {component['ComponentName']}",
                'N/A',
                error_msg
            )
            print(f"└─ Warning: {error_msg}")

    # Only proceed with update if there are changes
    if payload:
        try:
            api_url = construct_api_url(f"/v1/components/{existing_component['id']}")
            print(f"└─ Sending update payload:")
            print(f"   └─ {json.dumps(payload, indent=2)}")
            response = requests.patch(api_url, headers=headers, json=payload)
            response.raise_for_status()
            print(f"└─ Component updated successfully")
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to update component: {str(e)}"
            error_details = f'Response: {getattr(response, "content", "No response content")}\nPayload: {json.dumps(payload)}'
            log_error(
                'Component Update',
                f"{application['AppName']} -> {component['ComponentName']}",
                'N/A',
                error_msg,
                error_details
            )
            print(f"└─ Error: {error_msg}")
            if DEBUG:
                print(f"└─ Response content: {response.content}")
    
    try:
        create_component_rules(application['AppName'], component, headers)
    except Exception as e:
        error_msg = f"Failed to create component rules: {str(e)}"
        log_error(
            'Component Rules Creation',
            f"{application['AppName']} -> {component['ComponentName']}",
            'N/A',
            error_msg
        )
        print(f"└─ Warning: {error_msg}")

def update_application_teams(existing_app, application, headers):
    for team in filter(lambda tag: tag.get('key') == 'pteam', existing_app.get('tags')):
        if team.get('value') not in application.get('TeamNames'):
            remove_tag_from_application(team.get('id'), team.get('key'), team.get('value'), existing_app.get('id'), headers)

    for new_team in application.get('TeamNames'):
        if not next(filter(lambda team: team.get('key') == 'pteam' and team['value'] == new_team, existing_app.get('tags')), None):
            add_tag_to_application('pteam', new_team, existing_app.get('id'), headers)

def update_application_crit_owner(application, existing_application, headers):
    print(f"\n[Application Configuration Update]")
    print(f"└─ Application: {application['AppName']}")
    
    payload = {
        "name": application['AppName'],
        "criticality": application['Criticality'],
        "owner": {"email": application['Responsable']}
    }

    # Handle ticketing configuration
    if application.get('Ticketing'):
        try:
            ticketing = application['Ticketing']
            if isinstance(ticketing, list):
                ticketing = ticketing[0] if ticketing else {}
            elif not isinstance(ticketing, dict):
                print(f"└─ Warning: Ticketing configuration is not in the expected format")
                ticketing = {}
            
            integration_name = ticketing.get('TIntegrationName')
            project_name = ticketing.get('Backlog')

            if integration_name and project_name:
                payload["ticketing"] = {
                    "integrationName": integration_name,
                    "projectName": project_name
                }
                print(f"└─ Adding ticketing configuration:")
                print(f"   └─ Integration: {integration_name}")
                print(f"   └─ Project: {project_name}")
            else:
                print(f"└─ Warning: Ticketing configuration missing required fields")
                print(f"   └─ TIntegrationName: {integration_name}")
                print(f"   └─ Backlog: {project_name}")
                if DEBUG:
                    print(f"   └─ Raw ticketing config: {ticketing}")
        except Exception as e:
            error_msg = f"Failed to process ticketing configuration: {str(e)}"
            log_error(
                'Ticketing Config',
                application['AppName'],
                'N/A',
                error_msg
            )
            print(f"└─ Warning: {error_msg}")

    # Handle messaging configuration
    if application.get('Messaging'):
        try:
            messaging = application['Messaging']
            if isinstance(messaging, list):
                messaging = messaging[0] if messaging else {}
            elif not isinstance(messaging, dict):
                print(f"└─ Warning: Messaging configuration is not in the expected format")
                messaging = {}
            
            integration_name = messaging.get('MIntegrationName')
            channel_name = messaging.get('Channel')

            if integration_name and channel_name:
                payload["messaging"] = {
                    "integrationName": integration_name,
                    "channelName": channel_name
                }
                print(f"└─ Adding messaging configuration:")
                print(f"   └─ Integration: {integration_name}")
                print(f"   └─ Channel: {channel_name}")
            else:
                print(f"└─ Warning: Messaging configuration missing required fields")
                print(f"   └─ MIntegrationName: {integration_name}")
                print(f"   └─ Channel: {channel_name}")
                if DEBUG:
                    print(f"   └─ Raw messaging config: {messaging}")
        except Exception as e:
            error_msg = f"Failed to process messaging configuration: {str(e)}"
            log_error(
                'Messaging Config',
                application['AppName'],
                'N/A',
                error_msg
            )
            print(f"└─ Warning: {error_msg}")

    if DEBUG:
        print(f"└─ Final payload:")
        print(json.dumps(payload, indent=2))

    try:
        api_url = construct_api_url(f"/v1/applications/{existing_application.get('id')}")
        response = requests.patch(api_url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"└─ Application configuration updated successfully")
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to update application: {str(e)}"
        error_details = f'Response: {getattr(response, "content", "No response content")}\nPayload: {json.dumps(payload)}'
        log_error(
            'Application Update',
            application['AppName'],
            'N/A',
            error_msg,
            error_details
        )
        print(f"└─ Warning: {error_msg}")
        if DEBUG:
            print(f"└─ Response content: {getattr(response, 'content', 'No response content')}")

def create_component_rules(applicationName, component, headers):
    # Helper function to validate value
    def is_valid_value(value):
        if value is None:
            return False
        if isinstance(value, str) and (not value.strip() or value.lower() == 'null'):
            return False
        return True

    def is_valid_tag(tag):
        if not is_valid_value(tag):
            return False
        # Tag must be between 3 and 255 characters
        tag_str = str(tag).strip()
        return 3 <= len(tag_str) <= 255

    # SearchName rule
    if component.get('SearchName') and is_valid_value(component.get('SearchName')):
        create_component_rule(applicationName, component['ComponentName'], 'keyLike', component['SearchName'], f"Rule for keyLike for {component['ComponentName']}", headers)

    # Tags rule
    if component.get('Tags'):
        tags_to_add = []
        for tag in component.get('Tags'):
            if isinstance(tag, dict) and 'value' in tag:
                # If tag is already in correct format, validate the value
                if is_valid_tag(tag['value']):
                    tags_to_add.append(tag)
                elif DEBUG:
                    print(f" ! Skipping invalid tag value: '{tag['value']}' (must be between 3 and 255 characters)")
            else:
                # If tag is a string, validate and convert to correct format
                if is_valid_tag(tag):
                    tags_to_add.append({'value': tag})
                elif DEBUG:
                    print(f" ! Skipping invalid tag: '{tag}' (must be between 3 and 255 characters)")
        
        if tags_to_add:
            try:
                create_component_rule(applicationName, component['ComponentName'], 'tags', tags_to_add, f"Rule for tags for {component['ComponentName']}", headers)
            except Exception as e:
                if DEBUG:
                    print(f" ! Error creating tag rule for {component['ComponentName']}: {str(e)}")
                    print(f" ! Tags attempted: {json.dumps(tags_to_add, indent=2)}")
        elif DEBUG:
            print(f" ! No valid tags found for {component['ComponentName']}")

    # Repository rule - using get_repositories_from_component helper
    repository_names = get_repositories_from_component(component)
    if repository_names:  # This will handle empty lists as well
        create_component_rule(applicationName, component['ComponentName'], 'repository', repository_names, f"Rule for repository for {component['ComponentName']}", headers)

    # Other rules with validation
    if component.get('Cidr') and is_valid_value(component.get('Cidr')):
        create_component_rule(applicationName, component['ComponentName'], 'cidr', component['Cidr'], f"Rule for cidr for {component['ComponentName']}", headers)
    if component.get('Fqdn') and is_valid_value(component.get('Fqdn')):
        create_component_rule(applicationName, component['ComponentName'], 'fqdn', component['Fqdn'], f"Rule for fqdn for {component['ComponentName']}", headers)
    if component.get('Netbios') and is_valid_value(component.get('Netbios')):
        create_component_rule(applicationName, component['ComponentName'], 'netbios', component['Netbios'], f"Rule for netbios for {component['ComponentName']}", headers)
    if component.get('OsNames') and is_valid_value(component.get('OsNames')):
        create_component_rule(applicationName, component['ComponentName'], 'osNames', component['OsNames'], f"Rule for osNames for {component['ComponentName']}", headers)
    if component.get('Hostnames') and is_valid_value(component.get('Hostnames')):
        create_component_rule(applicationName, component['ComponentName'], 'hostnames', component['Hostnames'], f"Rule for hostnames for {component['ComponentName']}", headers)
    if component.get('ProviderAccountId') and is_valid_value(component.get('ProviderAccountId')):
        create_component_rule(applicationName, component['ComponentName'], 'providerAccountId', component['ProviderAccountId'], f"Rule for providerAccountId for {component['ComponentName']}", headers)
    if component.get('ProviderAccountName') and is_valid_value(component.get('ProviderAccountName')):
        create_component_rule(applicationName, component['ComponentName'], 'providerAccountName', component['ProviderAccountName'], f"Rule for providerAccountName for {component['ComponentName']}", headers)
    if component.get('ResourceGroup') and is_valid_value(component.get('ResourceGroup')):
        create_component_rule(applicationName, component['ComponentName'], 'resourceGroup', component['ResourceGroup'], f"Rule for resourceGroup for {component['ComponentName']}", headers)
    if component.get('AssetType') and is_valid_value(component.get('AssetType')):
        create_component_rule(applicationName, component['ComponentName'], 'assetType', component['AssetType'], f"Rule for assetType for {component['ComponentName']}", headers)

    # MultiCondition rules
    if component.get('MultiConditionRule') and is_valid_value(component.get('MultiConditionRule')):
        create_multicondition_component_rules(applicationName, component['ComponentName'], [component.get('MultiConditionRule')], headers)    

    if component.get('MultiConditionRules') and is_valid_value(component.get('MultiConditionRules')):
        create_multicondition_component_rules(applicationName, component['ComponentName'], component.get('MultiConditionRules'), headers)

def create_multicondition_component_rules(applicationName, componentName, multiconditionRules, headers):
    for multicondition in multiconditionRules:
        rule = {'name': f'MC-R {componentName}'}  # Shortened name format
        rule['filter'] = {}
        
        max_retries = 3
        current_try = 0
            
        while current_try < max_retries:
            try:
                if multicondition.get('SearchName'):
                    keylike = multicondition.get('SearchName')
                    # Start with full keylike value
                    rule['filter']['keyLike'] = keylike
                if multicondition.get('RepositoryName'):
                    repository_names = multicondition.get('RepositoryName')
                    if isinstance(repository_names, str):
                        repository_names = [repository_names]
                    rule['filter']['repository'] = repository_names
                if multicondition.get('Tags'):
                    rule['filter']['tags'] = []
                    for tag in multicondition.get('Tags'):
                        rule['filter']['tags'].append({"value": tag})
                if multicondition.get('Cidr'):
                    rule['filter']['cidr'] = multicondition.get('Cidr')
                if multicondition.get('Fqdn'):
                    rule['filter']['fqdn'] = multicondition.get('Fqdn')
                if multicondition.get('Netbios'):
                    rule['filter']['netbios'] = multicondition.get('Netbios')
                if multicondition.get('OsNames'):
                    rule['filter']['osNames'] = multicondition.get('OsNames')
                if multicondition.get('Hostnames'):
                    rule['filter']['hostnames'] = multicondition.get('Hostnames')
                if multicondition.get('ProviderAccountId'):
                    rule['filter']['providerAccountId'] = multicondition.get('ProviderAccountId')
                if multicondition.get('ProviderAccountName'):
                    rule['filter']['providerAccountName'] = multicondition.get('ProviderAccountName')
                if multicondition.get('ResourceGroup'):
                    rule['filter']['resourceGroup'] = multicondition.get('ResourceGroup')
                if multicondition.get('AssetType'):
                    rule['filter']['assetType'] = multicondition.get('AssetType')

                if not rule['filter']:
                    return

                payload = {
                    "selector": {
                        "applicationSelector": {"name": applicationName, "caseSensitive": False},
                        "componentSelector": {"name": componentName, "caseSensitive": False}
                    },
                    "rules": [rule]
                }

                if DEBUG:
                    print(f"\nSending payload for {componentName}:")
                    print(json.dumps(payload, indent=2))

                api_url = construct_api_url("/v1/components/rules")
                response = requests.post(api_url, headers=headers, json=payload)
                response.raise_for_status()
                print(f"MC-R {componentName} created.")
                break  # Success, exit the retry loop
                    
            except requests.exceptions.RequestException as e:
                if response.status_code == 409:
                    filter_str = json.dumps(rule['filter'])
                    print(f" > MC-R {componentName} with filter {filter_str} already exists.")
                    break
                elif response.status_code == 400 and 'keyLike' in str(response.content):
                    # If error is related to keyLike length, shorten it
                    current_try += 1
                    if current_try < max_retries:
                        # Shorten the keyLike value by 25% each try
                        reduction = int(len(keylike) * 0.75)
                        keylike = keylike[:reduction]
                        rule['filter']['keyLike'] = keylike
                        if DEBUG:
                            print(f"Retrying with shortened keyLike: {keylike}")
                        continue
                if DEBUG:
                    print(f"Error: {e}")
                    print(f"Response content: {response.content}")
                break  # Exit on other errors

def create_multicondition_service_rules(environmentName, serviceName, multiconditionRules, headers):
    # Helper function to validate value
    def is_valid_value(value):
        if value is None:
            return False
        if isinstance(value, str) and (not value.strip() or value.lower() == 'null'):
            return False
        return True

    for multicondition in multiconditionRules:
        if not is_valid_value(multicondition):
            print(f" ! Skipping invalid multicondition rule for {serviceName}")
            continue

        # Build the filter first
        rule = {'filter': {}}
        filter_details = []
        
        # Add each condition to the filter and collect details for logging
        if multicondition.get('SearchName') and is_valid_value(multicondition.get('SearchName')):
            # Preserve exact search pattern
            rule['filter']['keyLike'] = str(multicondition.get('SearchName'))
            filter_details.append(f"KEY:{multicondition.get('SearchName')}")
            
        if multicondition.get('RepositoryName'):
            repository_names = multicondition.get('RepositoryName')
            if isinstance(repository_names, str):
                repository_names = [repository_names]
            valid_repos = [repo for repo in repository_names if is_valid_value(repo)]
            if valid_repos:
                rule['filter']['repository'] = valid_repos
                filter_details.append(f"REPO:{','.join(valid_repos)}")
            
        if multicondition.get('Tag') and is_valid_value(multicondition.get('Tag')):
            # Preserve exact tag pattern
            tag_value = str(multicondition.get('Tag'))
            if ':' in tag_value:
                tag_parts = tag_value.split(':')
                if len(tag_parts) >= 2:
                    key = tag_parts[0].strip()
                    value = ':'.join(tag_parts[1:]).strip()  # Join remaining parts in case value contains colons
                    rule['filter']['tags'] = [{"key": key, "value": value}]
                    filter_details.append(f"TAG:{key}={value}")
            else:
                # Handle tag without key:value format, preserving exact pattern including wildcards
                rule['filter']['tags'] = [{"value": tag_value}]
                filter_details.append(f"TAG:{tag_value}")
                
        if multicondition.get('AssetType') and is_valid_value(multicondition.get('AssetType')):
            rule['filter']['assetType'] = str(multicondition.get('AssetType'))
            filter_details.append(f"ASSET:{multicondition.get('AssetType')}")

        if not rule['filter']:
            print(f" ! No valid filters found in rule for {serviceName}, skipping")
            continue

        # Create descriptive rule name based on the filter type and value
        rule_name = f"MC-R-{serviceName}-{' AND '.join(filter_details)}"
        
        # Truncate rule name if too long (max 255 chars)
        if len(rule_name) > 255:
            rule_name = rule_name[:252] + "..."
            
        rule['name'] = rule_name

        payload = {
            "selector": {
                "applicationSelector": {"name": environmentName, "caseSensitive": False},
                "componentSelector": {"name": serviceName, "caseSensitive": False}
            },
            "rules": [rule]
        }

        if DEBUG:
            print(f"\nSending payload for {serviceName}:")
            print(json.dumps(payload, indent=2))

        try:
            api_url = construct_api_url("/v1/components/rules")
            response = requests.post(api_url, headers=headers, json=payload)
            
            if DEBUG:
                print(f"Response status code: {response.status_code}")
                print(f"Response content: {response.content}")
                
            response.raise_for_status()
            print(f" + Created rule: {rule_name}")
        except requests.exceptions.RequestException as e:
            if response.status_code == 409:
                filter_str = json.dumps(rule['filter'])
                print(f" > Rule already exists: {rule_name}")
            else:
                error_msg = f"Error creating rule: {str(e)}"
                if hasattr(response, 'content'):
                    error_msg += f"\nResponse content: {response.content.decode()}"
                log_error(
                    'Rule Creation',
                    f"{serviceName} -> {rule_name}",
                    environmentName,
                    error_msg
                )
                print(f" ! {error_msg}")
                # Don't exit, just continue with next rule
                continue

    return True  # Return success if we get here

def get_repositories_from_component(component):
    """
    Get repository names from a component, handling all edge cases.
    
    Args:
        component (dict): The component dictionary that may contain repository information
        
    Returns:
        list: A list of valid repository names, or an empty list if none are found
    """
    if DEBUG:
        print("\nProcessing repositories from component:")
        print(f"Component: {json.dumps(component, indent=2)}")
    
    # Handle case where component is None
    if not component:
        if DEBUG:
            print("Component is None, returning empty list")
        return []
        
    repository = component.get('RepositoryName')
    
    if DEBUG:
        print(f"Raw repository value: {repository}")
    
    # Handle None, null, empty string, or missing key cases
    if repository is None:
        if DEBUG:
            print("Repository is None, returning empty list")
        return []
        
    # Handle string case
    if isinstance(repository, str):
        # Clean and validate the string
        repository = repository.strip()
        if not repository or repository.lower() == 'null':
            if DEBUG:
                print(f"Repository is empty or 'null': {repository}")
            return []
        if len(repository) >= 3:  # Only return if length requirement is met
            if DEBUG:
                print(f"Valid repository found: {repository}")
            return [repository]
        if DEBUG:
            print(f"Repository too short: {repository}")
        return []
    
    # Handle list case
    if isinstance(repository, list):
        if DEBUG:
            print("Processing repository list")
        valid_repos = []
        for repo in repository:
            if repo and isinstance(repo, str):
                repo = repo.strip()
                if repo and repo.lower() != 'null' and len(repo) >= 3:
                    if DEBUG:
                        print(f"Valid repository found in list: {repo}")
                    valid_repos.append(repo)
                elif DEBUG:
                    print(f"Invalid repository in list: {repo}")
        return valid_repos
    
    # If we get here, repository is an unexpected type
    if DEBUG:
        print(f"Warning: Unexpected repository type: {type(repository)}")
    return []

# CreateRepositories Function
def create_repositories(repos, access_token):
    # Iterate over the list of repositories and call the create_repo function
    for repo in repos:
        create_repo(repo, access_token)

# CreateRepo Function
def create_repo(repo, access_token):
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}
    
    # Calculate criticality (assuming a function `calculate_criticality` exists)
    criticality = calculate_criticality(repo['Tier'])
    
    # Create the payload, the function assume 1 repo per component with the component name being the repository this can be edited
    payload = {
        "repository": f"{repo['RepositoryName']}",
        "applicationSelector": {
            "name": repo['Subdomain'],
            "caseSensitive": False
        },
        "component": {
            "name": repo['RepositoryName'],
            "criticality": criticality,
            "tags": [
                {"key": "pteam", "value": repo['Team']},
                {"key": "domain", "value": repo['Domain']},
                {"key": "subdomain", "value": repo['Subdomain']}
            ]
        }
    }
    if DEBUG:
        print(f"Payload being sent to /v1rule: {json.dumps(payload, indent=2)}")


    api_url = construct_api_url("/v1/applications/repository")

    try:
        # Make POST request to create the repository
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        print(f" + {repo['RepositoryName']} added.")
    
    except requests.exceptions.RequestException as e:
        if response.status_code == 409:
            print(f" > Repo {repo['RepositoryName']} already exists")
        else:
            print(f"Error: {e}")
            exit(1)

# AddCloudAssetRules Function
def add_cloud_asset_rules(repos, access_token):
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}
    
    # Loop through each repository and modify domain if needed
    for repo in repos:
        search_term = f"*{repo['RepositoryName']}(*"
        cloud_asset_rule(repo['Subdomain'], search_term, "Production", access_token)

    # Adding rules for PowerPlatform with different environments
    #cloud_asset_rule("PowerPlatform", "powerplatform_prod", "Production", access_token)
    #cloud_asset_rule("PowerPlatform", "powerplatform_sim", "Sim", access_token)
    #cloud_asset_rule("PowerPlatform", "powerplatform_staging", "Staging", access_token)
    #cloud_asset_rule("PowerPlatform", "powerplatform_dev", "Development", access_token)

# CloudAssetRule Function
def cloud_asset_rule(name, search_term, environment_name, access_token):
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}
    
    # Create the payload
    payload = {
        "selector": {
            "applicationSelector": {
                "name": environment_name,
                "caseSensitive": False
            },
            "componentSelector": {
                "name": name,
                "caseSensitive": False
            }
        },
        "rules": [
            {
                "name": name,
                "filter": {
                    "keyLike": search_term
                }
            }
        ]
    }

    api_url = construct_api_url("/v1/components/rules")
    if DEBUG:
        print(f"Payload being sent to /v1rule: {json.dumps(payload, indent=2)}")

    try:
        # Make POST request to add the cloud asset rule
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"> Cloud Asset Rule added for {name} in {environment_name}")
    
    except requests.exceptions.RequestException as e:
        if response.status_code == 409:
            print(f" > Cloud Asset Rule for {name} already exists")
        else:
            print(f"Error: {e}")
            print(f"Error details: {response.content}")

def create_teams(teams, pteams, access_token):
    """
    This function iterates through a list of teams and adds new teams if they are not already present in `pteams`.

    Args:
    - teams: List of team objects to be added.
    - pteams: List of existing team objects to check if a team already exists.
    - access_token: Access token for API authentication.
    """
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}
    new_pteams = []
    
    # Iterate over the list of teams to be added
    for team in teams:
        found = False

        # Check if the team already exists in the existing pteams
        for pteam in pteams:
            if pteam['name'] == team['TeamName']:
                found = True
                break
        
        # If the team is not found and has a valid name, proceed to add it
        if not found and team['TeamName']:
            print("[Team]")
            print(f"└─ Creating: {team['TeamName']}")
            
            # Prepare the payload for creating the team
            payload = {
                "name": team['TeamName'],
                "type": "GENERAL"
            }

            api_url = construct_api_url("/v1/teams")
            print("└─ Sending payload:")
            print(f"  └─ {json.dumps(payload, indent=2)}")

            try:
                # Make the POST request to add the team
                response = requests.post(api_url, headers=headers, json=payload)
                response.raise_for_status()
                team['id'] = response.json()['id']
                new_pteams.append(response.json())
                print(f"└─ Team created successfully: {team['TeamName']}")
            except requests.exceptions.RequestException as e:
                if response.status_code == 400:
                    print(f"└─ Team {team['TeamName']} already exists")
                else:
                    error_msg = f"Failed to create team: {str(e)}"
                    error_details = f"Response: {getattr(response, 'content', 'No response content')}\nPayload: {json.dumps(payload)}"
                    log_error(
                        'Team Creation',
                        team['TeamName'],
                        'N/A',
                        error_msg,
                        error_details
                    )
                    print(f"Error: {error_msg}")
                    if DEBUG:
                        print(f"└─ Response content: {response.content}")
                    exit(1)
    return new_pteams


def create_teams_from_pteams(applications, environments, pteams, access_token):
    existing_teams = set([pteam['name'] for pteam in pteams ])
    teams_to_add = set()
    for env in environments:
        if 'TeamName' in env and env['TeamName'] not in existing_teams:
            teams_to_add.add(env['TeamName'])
        for service in env['Services']:
            if 'TeamName' in service and service['TeamName'] not in existing_teams:
                teams_to_add.add(service['TeamName'])
    
    for app in applications:
        if 'TeamNames' in app:
            for team in app['TeamNames']:
                if team not in existing_teams:
                    teams_to_add.add(team)
        for comp in app['Components']:
            if 'TeamNames' in comp:
                for team in comp['TeamNames']:
                    if team not in existing_teams:
                        teams_to_add.add(team)

    print(f'Detected teams to add {teams_to_add}')

    teams_to_add = [{'TeamName': team} for team in teams_to_add]
    for team in teams_to_add:
        create_teams(teams_to_add, pteams, access_token)
        create_team_rules(teams_to_add, pteams, access_token)


def populate_phoenix_teams(access_token):
    """
    This function retrieves the list of Phoenix teams by making a GET request to the /v1/teams endpoint.

    Args:
    - access_token: Access token for API authentication.

    Returns:
    - List of teams if the request is successful, otherwise exits with an error message.
    """
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}
    api_url = construct_api_url("/v1/teams")

    try:
        print("Getting list of Phoenix Teams")
        # Make the GET request to retrieve the list of teams
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        
        # Return the content of the response (team list)
        return response.json().get('content', [])
    
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        exit(1)


# CreateTeamRules Function
def create_team_rules(teams, pteams, access_token):
    """
    This function iterates through a list of teams and creates team rules for teams
    that do not already exist in `pteams`.

    Args:
    - teams: List of team objects.
    - pteams: List of pre-existing teams to check if a team already exists.
    - access_token: Access token for API authentication.
    """    
    for team in teams:
        found = False

        # Check if the team already exists in pteams
        for pteam in pteams:
            if pteam['name'] == team['TeamName']:
                print("[Team Rules]")
                print(f"└─ Team: {team['TeamName']}")
                # override logic for creating team associations
                if team.get('RecreateTeamAssociations'):
                    print(f"└─ recreating pteam association")
                    create_team_rule("pteam", team['TeamName'], pteam['id'], access_token)
                found = True
                break
        
        # If the team does not exist and has a valid name, create the team rule
        if not found and team['TeamName']:
            print(f"Team: {team['TeamName']}")
            create_team_rule("pteam", team['TeamName'], team['id'], access_token)

def create_team_rule(tag_name, tag_value, team_id, access_token):
    """
    This function creates a team rule by adding tags to a team.

    Args:
    - tag_name: Name of the tag (e.g., "pteam").
    - tag_value: Value of the tag (e.g., the team name).
    - team_id: ID of the team.
    - access_token: API authentication token.
    """
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}
    
    # Create the payload with the tags
    payload = {
        "match": "ANY",
        "tags": [
            {
                "key": tag_name,
                "value": tag_value
            }
        ]
    }

    api_url = construct_api_url(f"/v1/teams/{team_id}/components/auto-link/tags")
    
    try:
        print(f"└─ Creating team rule")
        # Make the POST request to create the team rule
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()

        print(f" + {tag_name} Component rule added for: {tag_value}")
    
    except requests.exceptions.RequestException as e:
        if response.status_code == 409:
            print(f" > {tag_name} Component Rule {tag_value} already exists")
        else:
            error_msg = f"Failed to add team rule: {str(e)}"
            error_details = f'Response: {getattr(response, "content", "No response content")}\nPayload {json.dumps(payload)}'
            log_error(
                'Team Rule Creation',
                f'TeamId: {team_id}',
                'N/A',
                error_msg,
                error_details
            )
            print(f"└─ Error: {error_msg}")
            if DEBUG:
                print(f"└─ {error_details}")
            exit(1)

    api_url = construct_api_url(f"/v1/teams/{team_id}/applications/auto-link/tags")
    
    try:
        # Make the POST request to create the team rule
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        print(f" + {tag_name} App/Env rule added for: {tag_value}")
    
    except requests.exceptions.RequestException as e:
        if response.status_code == 409:
            print(f" > {tag_name} App/Env Rule {tag_value} already exists")
        else:
            print(f"Error: {e}")
            exit(1)

def check_and_create_missing_users(teams, all_team_access, hive_staff, access_token):
    """
        This function checks whether some user from teams or hives is missing and creates them.

        Args:
        - teams: List of target teams to check users for
        - all_team_access: list of all team access users
        - hive_staff: list of hives. Only Lead and Product users will be managed in this function
    """
    p_users_emails = list(u.get("email") for u in load_users_from_phoenix(access_token))
    print('[User Creation from Teams]')
    for team in teams:
        print(f'└─ Team name: {team["TeamName"]}')
        for member in team.get('TeamMembers', []):
            if not member.get('EmailAddress'):
                print(f'  ! Missing email address for member {str(member)}')
                log_error(
                    "Create User",
                    getattr(team, 'TeamName', "No team name available"),
                    'N/A',
                    f'Member does not have EmailAddress field, received: {str(member)}'
                )
                continue

            email = member.get("EmailAddress")
            if any(p_email.lower() == email.lower() for p_email in p_users_emails):
                if DEBUG:
                    print(f'  └─ User already exists with email: {email}')
                continue
 
            print(f'  └─ Creating user with email {email}')
            name = member.get('Name', None)
            first_name, last_name = (None, None)
            if not name:
                print(f'  ! "Name" field not provided, received {str(member)}')
                print(f'  * Trying to get name from email')
                first_name, last_name = extract_user_name_from_email(email)
            else:
                try:
                    name_parts = name.split(" ")
                    first_name = name_parts[0]
                    last_name = name_parts[1]
                except Exception as e:
                    print(f'  └─ Error extracting first/last name from "Name", trying fallback to name from email, error={e}')
                    first_name, last_name = extract_user_name_from_email(email)
            if not first_name or not last_name:
                print(f'  └─ Could not obtain user first/last name, please check your configuration!')
                log_error(
                    'Create User',
                    email,
                    'N/A',
                    'Could not obtain user first/last name, please check your configuration'
                )
                continue

            try:
                api_call_create_user(email, first_name, last_name, "ORG_USER", access_token)
            except Exception as e:
                print(f'  └─ Error creating user from teams {e} ')
                log_error(
                    "Create User",
                    getattr(team, 'TeamName', "No team name available"),
                    'N/A',
                    f'Failed creating user, received: {str(member)}, error: {e}'
                )
                continue
    
    print('[User Creation from Hives]')
    for hive in hive_staff:
        if hive.get('Lead'):
            email = hive.get("Lead")
            if any(p_email.lower() == email.lower() for p_email in p_users_emails):
                if DEBUG:
                    print(f'  └─ User already exists with email: {email}')
            else:
                print(f'└─ Hive Lead: {email}')
                first_name, last_name = extract_user_name_from_email(email)
                if not first_name or not last_name:
                    print(f'  ! Could not extract first/last name, unable to create user {email}')
                    log_error(
                        'Create User',
                        email,
                        'N/A',
                        'Could not extract first/last name, unable to create user'
                    )

                try:
                    api_call_create_user(email, first_name, last_name, "ORG_USER", access_token)
                except Exception as e:
                    print(f'  └─ Error creating user from hives Lead {e} ')
                    log_error(
                        "Create User",
                        email,
                        'N/A',
                        f'Failed creating user, error: {e}'
                    )

        if hive.get('Product'):
            for email in hive.get('Product'):
                if any(p_email.lower() == email.lower() for p_email in p_users_emails):
                    if DEBUG:
                        print(f'  └─ User already exists with email: {email}')
                else:
                    print(f'└─ Hive Product: {email}')
                    first_name, last_name = extract_user_name_from_email(email)
                    if not first_name or not last_name:
                        print(f'  ! Could not extract first/last name, unable to create user {email}')
                        log_error(
                            'Create User',
                            email,
                            'N/A',
                            f'Could not extract first/last name, unable to create user {email}'
                        )

                    try:
                        api_call_create_user(email, first_name, last_name, "ORG_USER", access_token)
                    except Exception as e:
                        print(f'  └─ Error creating user from hives Product {e} ')
                        log_error(
                            "Create User",
                            email,
                            'N/A',
                            f'Failed creating user, error: {e}'
                        )

    
    print('[User Creation for All Access Accounts]')
    for all_access_email in all_team_access:
        if any(p_email.lower() == all_access_email.lower() for p_email in p_users_emails):
            if DEBUG:
                print(f'  └─ User already exists with email: {all_access_email}')
            continue
        print(f'└─ All access email: {all_access_email}')
        first_name, last_name = extract_user_name_from_email(all_access_email)
        if not first_name or not last_name:
            print(f'  ! Could not extract first/last name, unable to create user {all_access_email}')
            log_error(
                'Create User',
                all_access_email,
                'N/A',
                'Could not extract first/last name, unable to create user'
            )
            continue

        try:
            api_call_create_user(all_access_email, first_name, last_name, "ORG_USER", access_token)
        except Exception as e:
            print(f'  └─ Error creating user with all access account {e} ')
            log_error(
                "Create User",
                all_access_email,
                'N/A',
                f'Failed creating user, error: {e}'
            )


@dispatch(list,list,list,list,list,str)
def assign_users_to_team(p_teams, new_pteams, teams, all_team_access, hive_staff, access_token):
    """
    This function assigns users to teams by checking if users are already part of the team, and adds or removes them accordingly.
    
    Args:
    - p_teams: List of Phoenix teams.
    - teams: List of target teams to manage.
    - all_team_access: List of users with full team access.
    - hive_staff: List of Hive team staff.
    - access_token: API authentication token.
    """
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}
    all_pteams = p_teams + new_pteams
    for pteam in all_pteams:
        # Fetch current team members from the Phoenix platform
        team_members = get_phoenix_team_members(pteam['id'], headers)
        print(f"[Assign Users To Team]")
        print(f"└─ Team name: {pteam['name']}")
        for team in teams:
            if team['TeamName'] == pteam['name']:

                # Assign users from AllTeamAccess that are not part of the current team members
                print("  └─ Check and assign all team access users")
                for user_email in all_team_access:
                    found = any(member['email'].lower() == user_email.lower() for member in team_members)
                    if not found:
                        api_call_assign_users_to_team(pteam['id'], user_email, access_token)

                # Assign team members from the team if they are not part of the current team members
                print("  └─ Check and Assign team members")
                for team_member in team['TeamMembers']:
                    found = any(member['email'].lower() == team_member['EmailAddress'].lower() for member in team_members)
                    if not found:
                        print(f"    └─ Assign team member: {team_member['EmailAddress']}")
                        api_call_assign_users_to_team(pteam['id'], team_member['EmailAddress'], access_token)

                # Remove users who no longer exist in the team members
                print("  └─ Check members to remove")
                for member in team_members:
                    found = does_member_exist(member['email'], team, hive_staff, all_team_access)
                    if not found:
                        print(f"    └─ Removing member: {member['email']}")
                        delete_team_member(member['email'], pteam['id'], access_token)

        # Assign Hive team lead and product owners to the team
        hive_team = next((hs for hs in hive_staff if hs['Team'].lower() == pteam['name'].lower()), None)

        if hive_team:
            print("  └─ Hive")
            print(f"    └─ Adding team lead {hive_team['Lead']} to team {pteam['name']}")
            api_call_assign_users_to_team(pteam['id'], hive_team['Lead'], access_token)

            for product_owner in hive_team['Product']:
                print(f"    └─ Adding Product Owner {product_owner} to team {pteam['name']}")
                api_call_assign_users_to_team(pteam['id'], product_owner, access_token)


# ConstructAPIUrl Function
def construct_api_url(endpoint):
    """
    Constructs the full API URL by appending the endpoint to the base domain.
    
    Args:
    - endpoint: The API endpoint (e.g., "/v1/teams/{team_id}/users").
    
    Returns:
    - Full API URL.
    """
    return f"{APIdomain}{endpoint}"



# APICallAssignUsersToTeam Function
def api_call_assign_users_to_team(team_id, email, access_token):
    """
    Assigns a user to a team by making a PUT request to the API.

    Args:
    - team_id: The ID of the team.
    - email: The email address of the user to be added to the team.
    - access_token: API authentication token.
    """
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}
    
    # Construct the payload with the user email
    payload = {
        "users": [
            {"email": email.lower()}
        ]
    }
    
    # Construct the full API URL
    api_url = construct_api_url(f"/v1/teams/{team_id}/users")
    
    try:
        print(f"    └─ Assign user: {email}")
        # Make the PUT request to assign the user to the team
        response = requests.put(api_url, headers=headers, json=payload)
        print(f"    └─ Sending payload:")
        print(f"      └─ {json.dumps(payload, indent=2)}")
        response.raise_for_status()
        print(f"    + User {email} added to team {team_id}")
    except requests.exceptions.RequestException as e:
        if response.status_code == 400:
            print(f"    ? Team Member assignment {email} user hasn't logged in yet")
        elif response.status_code == 409:
            print(f"    ! Team Member {email} already assigned")
        else:
            error_msg = f"Failed to assign user: {str(e)}"
            error_details = f'Response: {getattr(response, "content", "No response content")}\nPayload: {json.dumps(payload)}'
            log_error(
                'Team Assignment',
                email,
                'N/A',
                error_msg,
                error_details
            )
            print(f"    └─ Error: {error_msg}")
            if DEBUG:
                print(f"    └─ Response content: {error_details}")
            exit(1)


# DeleteTeamMember Function
def delete_team_member(email, team_id, access_token):
    """
    Removes a user from a team by making a DELETE request to the API.

    Args:
    - email: The email address of the user to be removed from the team.
    - team_id: The ID of the team.
    - access_token: API authentication token.
    """
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}
    
    # Construct the full API URL
    api_url = construct_api_url(f"/v1/teams/{team_id}/users/{email}")
    
    print(f' * Sending remove team member ({email}) from team ({team_id}) request...')
    
    try:
        # Make the DELETE request to remove the user from the team
        response = requests.delete(api_url, headers=headers)
        response.raise_for_status()
        print(f" - Removed {email} from team {team_id}")
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to remove member {str(e)}"
        error_details = f'Response: {getattr(response, "content", "No response content")}'
        log_error(
            'Removing member',
            email,
            'N/A',
            error_msg,
            error_details
        )
        print(f"└─ Error: {error_msg}")
        if DEBUG:
            print(f"└─ Response content: {response.content}")

@dispatch(str)
def get_phoenix_components(access_token):
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}
    return get_phoenix_components(headers)

@dispatch(dict)
def get_phoenix_components(headers):
    """
    Fetches all Phoenix components with proper pagination handling.
    
    Args:
        headers: Request headers containing authorization
        
    Returns:
        list: Complete list of all components across all pages
    """
    components = []
    page_size = 100
    page_number = 0
    total_pages = None
    
    print("\n[Component Listing]")
    print(" * Fetching all components with pagination...")
    
    while total_pages is None or page_number < total_pages:
        try:
            api_url = construct_api_url("/v1/components")
            params = {
                "pageSize": page_size,
                "pageNumber": page_number,
                "sort": "name,asc"  # Sort by name for consistent listing
            }
            
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Add components from current page
            page_components = data.get('content', [])
            components.extend(page_components)
            
            # Update total pages on first iteration
            if total_pages is None:
                total_pages = data.get('totalPages', 1)
                total_elements = data.get('totalElements', 0)
                print(f" * Found {total_elements} total components across {total_pages} pages")
            
            print(f" * Fetched page {page_number + 1}/{total_pages} ({len(page_components)} components)")
            
            # Print components from this page if in debug mode
            if DEBUG:
                for comp in page_components:
                    env_name = comp.get('applicationId', 'Unknown')
                    print(f"   - [{env_name}] {comp.get('name', 'Unknown')}")
            
            page_number += 1
            
            # Add small delay between pages to avoid rate limiting
            if page_number < total_pages:
                time.sleep(0.5)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching components page {page_number}: {str(e)}"
            log_error(
                'Component Listing',
                'N/A',
                'N/A',
                error_msg,
                f'Response: {getattr(response, "content", "No response content")}'
            )
            print(f" ! {error_msg}")
            
            if response.status_code in [429, 503]:  # Rate limit or service unavailable
                retry_after = int(response.headers.get('Retry-After', 5))
                print(f" * Rate limited, waiting {retry_after} seconds...")
                time.sleep(retry_after)
                continue
            elif response.status_code >= 500:  # Server error
                print(" * Server error, retrying after 5 seconds...")
                time.sleep(5)
                continue
            else:
                break
    
    print(f" * Total components fetched: {len(components)}")
    return components


def get_phoenix_components_in_environment(env_id, access_token):
    return list(x for x in get_phoenix_components(access_token) if x.get('applicationId', None) == env_id)


def environment_service_exist(env_id, phoenix_components, service_name):
    """
    Check if a service exists in an environment with case-insensitive comparison.
    
    Args:
        env_id: Environment ID
        phoenix_components: List of Phoenix components
        service_name: Name of the service to check
        
    Returns:
        bool: True if service exists, False otherwise
    """
    service_name_lower = service_name.lower()
    
    # First try the cached components with case-insensitive comparison
    for component in phoenix_components:
        if (component['applicationId'] == env_id and 
            component['name'].lower() == service_name_lower):
            if DEBUG:
                print(f" * Found service {service_name} in cached components")
            return True
    
    # If not found in cache, return False to trigger a fresh check
    if DEBUG:
        print(f" * Service {service_name} not found in cached components")
    return False

def verify_service_exists(env_name, env_id, service_name, headers, max_retries=5):
    """
    Verify if a service exists in an environment with thorough checking and pagination.
    """
    print(f"\n[Service Verification]")
    print(f" └─ Environment: {env_name}")
    print(f" └─ Service: {service_name}")
    
    service_name_lower = service_name.lower()
    api_url = construct_api_url("/v1/components")
    
    try:
        # Get all services in one go with a larger page size
        params = {
            "pageSize": 1000,  # Use larger page size to reduce pagination
            "sort": "name,asc"  # Consistent sorting
        }
        
        print(" * Fetching all services...")
        response = requests.get(api_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        total_elements = data.get('totalElements', 0)
        total_pages = data.get('totalPages', 1)
        print(f" * Found {total_elements} total services across {total_pages} pages")
        
        all_services = data.get('content', [])
        
        # If more pages exist, fetch them
        for page in range(1, total_pages):
            params['pageNumber'] = page
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            all_services.extend(response.json().get('content', []))
            print(f" * Fetched page {page + 1}/{total_pages}")
        
        # filter out services that are not part of the given environment
        all_services = list(x for x in all_services if x.get('applicationId', None) == env_id)
        # First try exact case-insensitive match
        for service in all_services:
            if service['name'].lower() == service_name_lower:
                print(f" + Service found: {service['name']} (ID: {service.get('id')})")
                if DEBUG:
                    print(f"   └─ Application: {service.get('applicationId')}")
                return True, service.get('id')
        
        # If not found, look for similar services
        similar_services = []
        for service in all_services:
            ratio = Levenshtein.ratio(service['name'].lower(), service_name_lower)
            if ratio > SERVICE_LOOKUP_SIMILARITY_THRESHOLD:  # 80% similarity threshold
                similar_services.append((service['name'], ratio, service.get('id')))
        
        if similar_services:
            print(f" ! Service not found. Similar services:")
            for name, ratio, _ in sorted(similar_services, key=lambda x: x[1], reverse=True)[:5]:
                print(f"   └─ {name} (similarity: {ratio:.2f})")
            
            # If we have a very close match (>90% similarity), use it
            best_match = max(similar_services, key=lambda x: x[1])
            if best_match[1] > 0.9:
                print(f" + Using similar service: {best_match[0]} (similarity: {best_match[1]:.2f})")
                return True, best_match[2]
        
        # Print available services only in debug mode
        print(f" ! Service '{service_name}' not found in environment '{env_name}'")
        if DEBUG:
            print(f" ! Available services:")
            for service in sorted(all_services, key=lambda x: x['name']):
                print(f"   └─ {service['name']}")
        else:
            print(f" ! Use DEBUG=True to see list of available services")
        
        return False, None
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Error verifying service: {str(e)}"
        log_error(
            'Service Verification',
            service_name,
            env_name,
            error_msg,
            f'Response: {getattr(response, "content", "No response content")}'
        )
        print(f" ! {error_msg}")
        return False, None

# Helper function to get team members
def get_phoenix_team_members(team_id, access_token):
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}
    api_url = construct_api_url(f"/v1/teams/{team_id}/users")
    
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    return response.json()


def remove_old_tags(phoenix_components, repos, override_list):
    """
    Removes old tags from Phoenix components by comparing the repository information.

    Args:
    - phoenix_components: List of Phoenix components fetched from the API.
    - repos: List of repositories.
    - override_list: List of overrides for repository names and subdomains.
    """
    print("Removing old tags")

    for repo in repos:
        
        # Apply overrides from the override list
        for repo_override in override_list:
            if repo['RepositoryName'] == repo_override['Key']:
                repo['Subdomain'] = repo_override['Value']
        
        # Check and remove old tags in phoenix_components
        for component in phoenix_components:
            if repo['RepositoryName'] == component['name']:
                print(f"Repo: {repo['RepositoryName']}")
                #get_tag_value("domain", component['tags'], repo['Domain'])
                #get_tag_value("subdomain", component['tags'], repo['Subdomain'])
                get_tag_value("pteam", component['tags'], repo['Team'])

def get_tag_value(tag_name, source_tags, expected_value):
    """
    Checks and removes or updates a tag if the current value does not match the expected value.

    Args:
    - tag_name: The name of the tag to check.
    - source_tags: The tags associated with the component.
    - expected_value: The expected value for the tag.
    """
    for tag in source_tags:
        if tag['key'] == tag_name:
            if tag['value'] != expected_value:
                try:
                    print(f"- Removing tag {tag['key']} {tag['value']}")
                    remove_tag(tag['id'], tag_name, tag['value'])
                except Exception as e:
                    print(f"Error removing tag for {tag_name}: {e}")

def remove_tag(tag_id, tag_key, tag_value,access_token):
    """
    Removes the specified tag by making a DELETE or PATCH API call.

    Args:
    - tag_id: The ID of the tag to remove.
    - tag_key: The key of the tag.
    - tag_value: The value of the tag.
    """
    # Payload for removing the tag
    payload = {
        "action": "delete",
        "tags": [
            {
                "id": tag_id,
                "key": tag_key,
                "value": tag_value
            }
        ]
    }
    if DEBUG:
        print(f"Payload being sent to /v1-component-tags: {json.dumps(payload, indent=2)}")

    api_url = construct_api_url("/v1/components/tags")
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}

    try:
        response = requests.patch(api_url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"Tag {tag_key} with value {tag_value} removed successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error removing tag: {e}")

def remove_tag_from_application(tag_id, tag_key, tag_value, application_id, headers):
    """
    Removes the specified tag by making a DELETE or PATCH API call.

    Args:
    - tag_id: The ID of the tag to remove.
    - tag_key: The key of the tag.
    - tag_value: The value of the tag.
    - application_id: The ID of the application having the tag
    """
    # Payload for removing the tag
    payload = {
        "action": "delete",
        "tags": [
            {
                "id": tag_id,
                "key": tag_key,
                "value": tag_value
            }
        ]
    }
    if DEBUG:
        print(f"Payload being sent to /v1-application-tags: {json.dumps(payload, indent=2)}")

    api_url = construct_api_url(f"/v1/applications/{application_id}/tags")


    try:
        response = requests.patch(api_url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"Tag {tag_key} with value {tag_value} removed successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error removing tag: {e}")

def remove_tag_from_component(tag_id, tag_key, tag_value, component_id, headers):
    """
    Removes the specified tag by making a PATCH API call.

    Args:
    - tag_id: The ID of the tag to remove.
    - tag_key: The key of the tag.
    - tag_value: The value of the tag.
    - component_id: The ID of the component having the tag
    """
    # Payload for removing the tag
    payload = {
        "action": "delete",
        "tags": [
            {
                "id": tag_id,
                "key": tag_key,
                "value": tag_value
            }
        ]
    }
    if DEBUG:
        print(f"Payload being sent to /v1-component-tags: {json.dumps(payload, indent=2)}")

    api_url = construct_api_url(f"/v1/components/{component_id}/tags")


    try:
        response = requests.patch(api_url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"Tag {tag_key} with value {tag_value} removed successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error removing tag: {e}")

def add_tag_to_application(tag_key, tag_value, application_id, headers):
    """
    Add the specified tag by making a PUT API call.

    Args:
    - tag_key: The key of the tag.
    - tag_value: The value of the tag.
    - application_id: The application to tag
    """
    # Payload for removing the tag
    payload = {
        "tags": [
            {
                "key": tag_key,
                "value": tag_value
            }
        ]
    }
    if DEBUG:
        print(f"Payload being sent to /v1-application-tags: {json.dumps(payload, indent=2)}")

    api_url = construct_api_url(f"/v1/applications/{application_id}/tags")


    try:
        response = requests.put(api_url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"Tag {tag_key} with value {tag_value} added successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error adding tag: {e}")

# Helper function to check if a member exists
@dispatch(str,dict,list,list)
def does_member_exist(user_email, team, hive_staff, all_team_access):
    """
    Checks if a team member exists in the provided lists (team, hive_staff, or all_team_access).
    """
    print(f"\n[Team member Verification]")
    print(f" └─ Team member: {user_email}")
    print(f" └─ Team: {team.get('TeamName', '')}")
    print(f" └─ Hive staff: {hive_staff}")
    print(f" └─ All team access: {all_team_access}")
    return any(user_email.lower() == member['EmailAddress'].lower() for member in team['TeamMembers']) or \
           user_email.lower() in (lc_all_team_access.lower() for lc_all_team_access in all_team_access) or \
           any(user_email.lower() == staff_member['Lead'].lower() or user_email.lower() in staff_member['Product'] for staff_member in hive_staff)



#other supporting functions 

def populate_applications_and_environments(headers):
    components = []

    try:
        print("Getting list of Phoenix Applications and Environments")
        api_url = construct_api_url("/v1/applications")
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()

        data = response.json()
        components = data.get('content', [])
        total_pages = data.get('totalPages', 1)

        for i in range(1, total_pages):
            api_url = construct_api_url(f"/v1/applications?pageNumber={i}")
            response = requests.get(api_url, headers=headers)
            components += response.json().get('content', [])
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to fetch apps/envs. Response: {response.content if hasattr(response, 'content') else 'N/A'}"
        log_error(
            'Fetching all apps/envs',
            'None',
            'N/A',
            error_msg,
            f'Response status: {response.status_code}'
        )
        print(f"└─ Error: {error_msg}")
        exit(1)

    return components

@dispatch(str, str, dict, int, dict)
def add_service(applicationSelectorName, env_id, service, tier, headers):
    service_name = service['Service']

    criticality = calculate_criticality(tier)
    print(f" > Attempting to add {service_name}")
    
    payload = {
        "name": service_name,
        "criticality": criticality,
        "applicationSelector": {
            "name": applicationSelectorName
        },
        "tags": []
    }

    if service.get('Ticketing', None):
        payload["ticketing"] = {
            "integrationName": service.get('Ticketing').get('IntegrationName', None),
            "projectName": service.get('Ticketing').get('Backlog')
        }

    if service.get('Messaging', None):
        payload["messaging"] = {
            "integrationName": service.get('Messaging').get('IntegrationName', None),
            "channelName": service.get('Messaging').get('Channel')
        }

    try:
        api_url = construct_api_url("/v1/components")
        response = requests.post(api_url, headers=headers, json=payload)
        
        # Even if we get a 409, we need to verify the service exists in the correct environment
        if response.status_code == 409:
            print(f" * Service creation returned 409 (conflict), verifying correct environment...")
            components = get_phoenix_components_in_environment(env_id, headers)
            service_exists = any(
                comp['name'].lower() == service_name.lower() 
                for comp in components
            )
            
            if service_exists:
                print(f" + Service {service_name} verified in correct environment")
                return True
            else:
                print(f" ! Service {service_name} exists but not in environment {applicationSelectorName}")
                return False
        
        response.raise_for_status()
        print(f" + Added Service: {service_name}")
        
        # Verify service was created with retries
        max_retries = 5
        base_delay = 3
        for attempt in range(max_retries):
            delay = base_delay * (2 ** attempt)
            print(f" * Verifying service creation (attempt {attempt + 1}/{max_retries}, waiting {delay}s)...")
            time.sleep(delay)
            
            try:
                components = get_phoenix_components_in_environment(env_id, headers)
                
                service_exists = any(
                    comp['name'].lower() == service_name.lower() 
                    for comp in components
                )
                
                if service_exists:
                    print(f" + Service {service_name} verified successfully")
                    return True
                else:
                    print(f" ! Service {service_name} not found in verification attempt {attempt + 1}")
                    if attempt == max_retries - 1:
                        print(f" ! Service {service_name} could not be verified after {max_retries} attempts")
                        return False
                    
            except requests.exceptions.RequestException as e:
                print(f" ! Error verifying service on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return False
                continue
        
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if hasattr(response, 'content'):
            print(f"Response content: {response.content}")
        return False

@dispatch(str, str, dict, int, str, dict)
def add_service(applicationSelectorName, env_id, service, tier, team, headers):
    service_name = service['Service']
    criticality = calculate_criticality(tier)
    print(f"\n[Service Creation]")
    print(f" └─ Environment: {applicationSelectorName}")
    print(f" └─ Service: {service_name}")
    print(f" └─ Team: {team}")
    
    try:
        # First verify if service exists in the target environment
        components = get_phoenix_components_in_environment(env_id, headers)
        
        if any(comp['name'].lower() == service_name.lower() for comp in components):
            print(f" + Service {service_name} already exists in {applicationSelectorName}")
            return True
            
        # Service doesn't exist in target environment, try to create it
        payload = {
            "name": service_name,
            "criticality": criticality,
            "applicationSelector": {
                "name": applicationSelectorName,
                "caseSensitive": False
            },
            "tags": [{"key": "pteam", "value": team}]
        }

        # Handle ticketing configuration
        if service.get('Ticketing'):
            ticketing = service['Ticketing']
            if isinstance(ticketing, list) and ticketing:
                ticketing_config = ticketing[0]  # Get first item from list
                payload["ticketing"] = {
                    "integrationName": ticketing_config.get('TIntegrationName') or ticketing_config.get('IntegrationName'),
                    "projectName": ticketing_config.get('Backlog')
                }

        # Handle messaging configuration
        if service.get('Messaging'):
            messaging = service['Messaging']
            if isinstance(messaging, list) and messaging:
                messaging_config = messaging[0]  # Get first item from list
                payload["messaging"] = {
                    "integrationName": messaging_config.get('MIntegrationName') or messaging_config.get('IntegrationName'),
                    "channelName": messaging_config.get('Channel')
                }
        
        api_url = construct_api_url("/v1/components")
        print(" * Sending service creation request...")
        print(f" * Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(api_url, headers=headers, json=payload)
        
        if response.status_code == 409:
            # Service exists somewhere else, try with a suffix
            unique_service = f"{service_name}-{applicationSelectorName.lower()}"
            print(f" ! Service {service_name} exists in another environment")
            print(f" * Attempting to create service as {unique_service}")
            
            payload["name"] = unique_service
            response = requests.post(api_url, headers=headers, json=payload)
        
        response.raise_for_status()
        created_service_name = payload["name"]
        print(f" + Service creation request successful: {created_service_name}")
        
        # Verify service was created with retries
        max_retries = 5
        base_delay = 3
        for attempt in range(max_retries):
            delay = base_delay * (2 ** attempt)
            print(f" * Verifying service creation (attempt {attempt + 1}/{max_retries}, waiting {delay}s)...")
            time.sleep(delay)
            
            try:
                all_components = get_phoenix_components_in_environment(env_id, headers)
                
                print(f" * Total components fetched: {len(all_components)}")
                print(" * Available components:")
                for comp in sorted(all_components, key=lambda x: x['name']):
                    print(f"   └─ {comp['name']}")
                
                if any(comp['name'].lower() == created_service_name.lower() for comp in all_components):
                    print(f" + Service {created_service_name} found in full component listing")
                    return True
                
                print(f" ! Service {created_service_name} not found in verification attempt {attempt + 1}")
                if attempt == max_retries - 1:
                    print(f" ! Service {created_service_name} could not be verified after {max_retries} attempts")
                    return False
                
            except requests.exceptions.RequestException as e:
                print(f" ! Error verifying service on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return False
                continue
        
        return False
        
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if hasattr(response, 'content'):
            print(f"Response content: {response.content}")
        return False
    
def update_service(service, existing_service_id, headers):
    payload = {}
    
    # Handle ticketing configuration first
    if service.get('Ticketing'):
        ticketing = service.get('Ticketing')
        if isinstance(ticketing, list) and ticketing:
            ticketing_config = ticketing[0]  # Get first item from list
            payload["ticketing"] = {
                "integrationName": ticketing_config.get('TIntegrationName') or ticketing_config.get('IntegrationName'),
                "projectName": ticketing_config.get('Backlog')
            }
            print(f" > Adding ticketing configuration for {service['Service']}")
    
    # Handle messaging configuration separately
    if service.get('Messaging'):
        try:
            messaging = service.get('Messaging')
            if isinstance(messaging, list) and messaging:
                messaging_config = messaging[0]  # Get first item from list
                integration_name = messaging_config.get('MIntegrationName') or messaging_config.get('IntegrationName')
                channel_name = messaging_config.get('Channel')
                
                if integration_name and channel_name:
                    messaging_payload = {
                        "messaging": {
                            "integrationName": integration_name,
                            "channelName": channel_name
                        }
                    }
                    print(f" > Adding messaging configuration for {service['Service']}")
                    print(f"   └─ Integration: {integration_name}")
                    print(f"   └─ Channel: {channel_name}")
                    
                    # Update messaging configuration
                    try:
                        api_url = construct_api_url(f"/v1/components/{existing_service_id}")
                        response = requests.patch(api_url, headers=headers, json=messaging_payload)
                        
                        if response.status_code == 400 and b'Channel not found' in response.content:
                            print(f" ! Warning: Slack channel '{channel_name}' not found. Please verify the channel exists and is accessible.")
                            log_error(
                                'Messaging Config',
                                service['Service'],
                                'N/A',
                                f"Channel '{channel_name}' not found",
                                f'Integration: {integration_name}'
                            )
                        else:
                            response.raise_for_status()
                            print(f" + Updated messaging for service: {service['Service']}")
                    except Exception as e:
                        print(f" ! Error updating messaging: {e}")
                        if hasattr(response, 'content'):
                            print(f"   └─ {response.content.decode()}")
                else:
                    print(f" ! Warning: Messaging configuration missing required fields")
                    print(f"   └─ MIntegrationName: {integration_name}")
                    print(f"   └─ Channel: {channel_name}")
        except Exception as e:
            print(f" ! Error processing messaging configuration: {e}")
    
    # Update ticketing if present
    if payload:
        try:
            api_url = construct_api_url(f"/v1/components/{existing_service_id}")
            response = requests.patch(api_url, headers=headers, json=payload)
            response.raise_for_status()
            print(f" + Updated ticketing for service: {service['Service']}")
        except Exception as e:
            print(f" ! Error updating ticketing: {e}")
            if hasattr(response, 'content'):
                print(f"   └─ {response.content.decode()}")
    
    time.sleep(1)  # Small delay between updates

def add_thirdparty_services(phoenix_components, application_environments, subdomain_owners, headers):
    services = [
        "Salesforce", #example of 3rd party app to add components and findings to 3rd parties
    ]

    env_name = "Thirdparty"
    env_id = get_environment_id(application_environments, env_name)

    if not env_id:
        print('Environment Thirdparty not found')
        return

    for service in services:
        if not environment_service_exist(env_id, phoenix_components, service):
            add_service(env_name, env_id, {"Service": service}, 5, "Thirdparty", subdomain_owners, headers)

def get_environment_id(application_environments, env_name):
    for environment in application_environments:
        if environment["name"] == env_name:
            return environment["id"]
    return None

def get_phoenix_team_members(team_id, headers):
    try:
        api_url = construct_api_url(f"/v1/teams/{team_id}/users")
        response = requests.get(api_url, headers=headers)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return []

def create_deployments(applications, environments, phoenix_apps_envs, headers):
    application_services = []
    # Track all available apps and services for validation
    available_apps = {app['name']: app['id'] for app in phoenix_apps_envs if app.get('type') == "APPLICATION"}
    available_services = {}
    
    print(f"\n[Deployment Operation]")
    print(f"└─ Found {len(applications)} applications to process")
    print(f"└─ Found {len(environments)} environments to process")
    print(f"└─ Found {len(phoenix_apps_envs)} Phoenix apps/envs")
    
    # Get all services for each environment with proper pagination
    all_services = get_phoenix_components(headers)
    for env in phoenix_apps_envs:
        if env.get('type') == "ENVIRONMENT":
            available_services[env['name']] = {svc['name']: svc['id'] for svc in all_services if svc['applicationId'] == env['id']}
            print(f"└─ Total services loaded for '{env['name']}': {len(available_services[env['name']])}")
    
    # Process each application
    for app in applications:
        app_name = app.get('AppName')
        if not app_name:
            continue
            
        if app_name not in available_apps:
            print(f"\n[Processing Application: {app_name}]")
            print(f"└─ Error: Application not found")
            continue
            
        deployment_set = app.get('Deployment_set')
        if not deployment_set:
            print(f"\n[Processing Application: {app_name}]")
            print(f"└─ Error: No deployment set defined")
            continue
            
        print(f"\n[Processing Application: {app_name}]")
        print(f"└─ Deployment Set: {deployment_set}")
        
        # Validate app exists
        if app_name not in available_apps:
            error_msg = f"Application '{app_name}' not found in available applications"
            log_error(
                'Deployment Creation',
                app_name,
                'N/A',
                error_msg,
                f'Available apps: {", ".join(sorted(available_apps.keys()))}'
            )
            print(f"└─ Error: {error_msg}")
            continue

        for env in environments:
            if not env.get('Services'):
                continue
            env_name = env.get('Name')
            
            print(f"\n  [Environment: {env_name}]")
            matched_services = 0
            total_services = len(env.get('Services', []))
            print(f"  └─ Processing {total_services} services")
            
            for service in env.get('Services', []):
                service_name = service.get('Service')
                service_deployment_set = service.get('Deployment_set', '').lower() if service.get('Deployment_set') else None
                service_deployment_tag = service.get('Deployment_tag', '').lower() if service.get('Deployment_tag') else None
                deployment_set_lower = deployment_set.lower()
                
                print(f"    └─ Checking service: {service_name}")
                print(f"       └─ Service Deployment Set: {service_deployment_set}")
                print(f"       └─ Service Deployment Tag: {service_deployment_tag}")
                print(f"       └─ Required Deployment Set: {deployment_set_lower}")
                
                # Check if service exists in this environment
                if env_name in available_services and service_name not in available_services[env_name]:
                    error_msg = f"Service '{service_name}' not found in environment '{env_name}'"
                    log_error(
                        'Deployment Creation',
                        f"{app_name} -> {service_name}",
                        env_name,
                        error_msg,
                        f'Available services: {", ".join(sorted(available_services[env_name].keys()))}'
                    )
                    print(f"       └─ Error: {error_msg}")
                    continue

                if service_deployment_set == deployment_set_lower:
                    print(f"       └─ ✓ Matched by Deployment_set")
                    application_services.append({
                        "applicationSelector": {
                            "name": app_name,
                            "caseSensitive": False
                        },
                        "serviceSelector": {
                            "name": service_name,
                            "caseSensitive": False
                        },
                        "environment": env_name
                    })
                    matched_services += 1
                elif service_deployment_tag == deployment_set_lower:
                    print(f"       └─ ✓ Matched by Deployment_tag")
                    application_services.append({
                        "applicationSelector": {
                            "name": app_name,
                            "caseSensitive": False
                        },
                        "serviceSelector": {
                            "tags": [
                                {
                                    "value": service.get('Deployment_tag')
                                }
                            ]
                        },
                        "environment": env_name
                    })
                    matched_services += 1
                else:
                    print(f"       └─ ✗ No match")
            
            print(f"  └─ Matched {matched_services} out of {total_services} services in environment {env_name}")
    
    total_deployments = len(application_services)
    print(f"\n[Deployment Summary]")
    print(f"└─ Total deployments to create: {total_deployments}")
    
    if total_deployments == 0:
        print("└─ No deployments to create, exiting")
        return

    batch_size = 10
    consecutive_400_errors = 0
    successful_deployments = 0
    failed_deployments = 0
    
    for i in range(0, len(application_services), batch_size):
        batch = application_services[i:i + batch_size]
        print(f"\n[Processing Batch {i//batch_size + 1}/{(total_deployments + batch_size - 1)//batch_size}]")
        
        for deployment in batch:
            app_name = deployment['applicationSelector']['name']
            app_id = available_apps.get(app_name)
            
            if not app_id:
                error_msg = f"Application '{app_name}' not found"
                log_error(
                    'Deployment Creation',
                    app_name,
                    deployment.get('environment', 'N/A'),
                    error_msg,
                    'Application missing during deployment'
                )
                print(f"└─ Error: {error_msg}")
                failed_deployments += 1
                continue

            use_service_name = 'name' in deployment['serviceSelector']
            service_info = deployment['serviceSelector']['name'] if use_service_name else str(deployment['serviceSelector']['tags'])
            
            retry_attempts = 3
            deployment_success = False
            last_error = None
            
            for attempt in range(retry_attempts):
                try:
                    deployment_payload = {"serviceSelector": deployment["serviceSelector"]}
                    api_url = construct_api_url(f"/v1/applications/{app_id}/deploy")
                    
                    if DEBUG:
                        print(f"\nSending deployment request:")
                        print(f"URL: {api_url}")
                        print(f"Payload: {json.dumps(deployment_payload, indent=2)}")
                    
                    response = requests.patch(api_url, headers=headers, json=deployment_payload)
                    
                    if DEBUG:
                        print(f"Response status: {response.status_code}")
                        print(f"Response content: {response.content}")
                    
                    response.raise_for_status()
                    print(f"└─ Successfully created deployment for application {app_name} and "
                          f"{'service name: ' + service_info if use_service_name else 'service tag: ' + service_info}")
                    consecutive_400_errors = 0
                    deployment_success = True
                    successful_deployments += 1
                    break
                    
                except requests.exceptions.RequestException as e:
                    last_error = str(e)
                    if response.status_code == 409:
                        print(f"└─ Deployment already exists for application {app_name} and "
                              f"{'service name: ' + service_info if use_service_name else 'service tag: ' + service_info}")
                        consecutive_400_errors = 0
                        deployment_success = True
                        successful_deployments += 1
                        break
                    elif response.status_code == 400:
                        error_content = response.content.decode() if hasattr(response, 'content') else 'No error details'
                        print(f"└─ Error 400: Bad request for deployment {app_name}. Details: {error_content}")
                        print(f"└─ Waiting for 2 seconds before retrying...")
                        time.sleep(2)
                        consecutive_400_errors += 1
                        if consecutive_400_errors > 3:
                            wait_time = random.randint(2, 6)
                            print(f"└─ More than 3 consecutive 400 errors. Waiting for {wait_time} seconds...")
                            time.sleep(wait_time)
                    else:
                        print(f"└─ Error: {e}")
                        if attempt < retry_attempts - 1:
                            print(f"└─ Retrying... (Attempt {attempt + 2}/{retry_attempts})")
                            time.sleep(0.5)
                        else:
                            print("└─ Failed after multiple attempts.")
            
            if not deployment_success:
                error_msg = f"Failed to create deployment after {retry_attempts} attempts"
                log_error(
                    'Deployment Creation',
                    f"{app_name} -> {service_info}",
                    deployment.get('environment', 'N/A'),
                    error_msg,
                    f'Last error: {last_error}'
                )
                print(f"└─ Error: {error_msg}")
                failed_deployments += 1

        time.sleep(1)  # Wait for 1 second after processing each batch
    
    print(f"\n[Final Deployment Summary]")
    print(f"└─ Total deployments processed: {total_deployments}")
    print(f"└─ Successful deployments: {successful_deployments}")
    print(f"└─ Failed deployments: {failed_deployments}")

def check_app_name_matches_service_name(app_name, service_name):
    if app_name.lower() == service_name.lower():
        return True
    similarity_ratio = Levenshtein.ratio(app_name, service_name)
    if similarity_ratio > AUTOLINK_DEPLOYMENT_SIMILARITY_THRESHOLD:
        print(f'Similarity ratio {similarity_ratio} between {app_name} and {service_name} is within threshold, adding deployment')
        return True
    else:
        if DEBUG:
            print(f'Similarity ratio {similarity_ratio} between {app_name} and {service_name} is NOT within threshold, NOT adding deployment')

    return False

def create_autolink_deployments(applications, environments, headers):
    deployments = []

    for app in applications:
        app_name = app.get("AppName")
        for env in environments:
            if not env.get('Services'):
                continue
            for service in env.get('Services'):
                service_name = service.get("Service")
                if check_app_name_matches_service_name(app_name, service_name):
                    deployments.append({
                        "applicationSelector": {
                            "name": app_name,
                        },
                        "serviceSelector": {
                            "name": service_name
                        }
                    })
    print(f'Number of deployments to add {len(deployments)}')

    batch_size = 10
    for i in range(0, len(deployments), batch_size):
        batch = deployments[i:i + batch_size]
        for deployment in batch:
            retry_attempts = 3  # Number of retry attempts
            for attempt in range(retry_attempts):
                try:
                    api_url = construct_api_url(f"/v1/applications/deploy")
                    response = requests.patch(api_url, headers=headers, json=deployment)
                    response.raise_for_status()
                    print(f" + Deployment for application {deployment['applicationSelector']['name']} to {deployment['serviceSelector']['name']} successful")
                    break  # Exit the retry loop if successful
                except requests.exceptions.RequestException as e:
                    if response.status_code == 409:
                        print(f" - Deployment for application {deployment['applicationSelector']['name']} to {deployment['serviceSelector']['name']} already exists.")
                        break  # No need to retry if the deployment already exists
                    elif response.status_code == 400:
                        print(f"Error 400: Bad request for deployment {deployment['applicationSelector']['name']} to {deployment['serviceSelector']['name']}. Waiting for 2 seconds before retrying...")
                        time.sleep(2)  # Wait for 2 seconds before retrying
                    else:
                        print(f"Error: {e}")
                        if attempt < retry_attempts - 1:
                            print(f"Retrying... (Attempt {attempt + 2}/{retry_attempts})")
                            time.sleep(0.5)  # Wait for 0.5 seconds before retrying
                        else:
                            print("Failed after multiple attempts.")
                            exit(1)
        time.sleep(1)  # Wait for 1 second after processing each batch

def get_assets(applicationEnvironmentId, type, headers):
    asset_request = {
        "requests": [
            {
                "type": type,
                "applicationEnvironmentId": applicationEnvironmentId
            }
        ]
    }
    try:
        print(f"Fetching assets for {applicationEnvironmentId} and {type}")
        api_url = construct_api_url(f"/v1/assets?pageNumber=0&pageSize=100")
        response = requests.post(api_url, headers=headers, json = asset_request)
        response.raise_for_status()

        data = response.json()
        assets = [asset['name'] for asset in data.get('content', [])]
        total_pages = data.get('totalPages', 1)
        for i in range(1, total_pages):
            api_url = construct_api_url(f"/v1/assets?pageNumber={i}&pageSize=100")
            response = requests.post(api_url, headers=headers, json = asset_request)
            new_assets = [asset['name'] for asset in response.json().get('content', [])]
            assets += new_assets

        return assets  

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        exit(1)

def group_assets_by_similar_name(assets):
    asset_groups = []
    for asset in assets:
        added_to_group = False
        for group in asset_groups:
            should_add_to_group = True
            for groupped_asset in group:
                if Levenshtein.ratio(asset, groupped_asset) < ASSET_NAME_SIMILARITY_THRESHOLD:
                    should_add_to_group = False
                    break
            if should_add_to_group:
                group.append(asset)
                added_to_group = True
                break
        if not added_to_group:
            asset_groups.append([asset,])
            continue
    return asset_groups

def create_components_from_assets(applicationEnvironments, phoenix_components, headers):
    types = ["CONTAINER", "CLOUD"]
    phoenix_component_names = [pcomponent.get('name') for pcomponent in phoenix_components]
    for type in types:
        already_suggested_components = set()
        for appEnv in applicationEnvironments:
            if appEnv.get('type') == "ENVIRONMENT":
                assets = get_assets(appEnv.get("id"), type, headers)
                asset_groups = group_assets_by_similar_name(assets)
                for group in asset_groups:
                    if len(group) > ASSET_GROUP_MIN_SIZE_FOR_COMPONENT_CREATION and not group[0] in already_suggested_components\
                        and not group[0] in phoenix_component_names:
                        answer = input(f"Would you like to create component {group[0]} in environment: {appEnv.get('name')}? [Y for yes] [N for no] [A for alter name]")
                        already_suggested_components.add(group[0])
                        component_name = group[0]
                        if answer == 'N':
                            continue
                        if answer == 'A':
                            component_name = input("Component name:")
                            already_suggested_components.add(component_name)
                        print(f"Created component with name {component_name} in environment: {appEnv.get('name')}")
                        component_to_create = {
                            "Status": None,
                            "Type": None,
                            "TeamNames": [next((tag['value'] for tag in appEnv['tags'] if 'value' in tag and 'key' in tag and tag['key'] == 'pteam'), None)],
                            "ComponentName": component_name
                        }
                        create_custom_component(appEnv['name'], component_to_create, headers)
                        print(f"Created component with name {component_name} in environment: {appEnv.get('name')}")

# Handle Repository Rule Creation for Components
def generate_descriptive_rule_name(component_name, filter_name, filter_value):
    """
    Generate a descriptive rule name based on the filter type and value.
    
    Args:
        component_name (str): Name of the component
        filter_name (str): Type of filter (e.g., 'keyLike', 'tags', etc.)
        filter_value: The value being filtered for
        
    Returns:
        str: A descriptive rule name
    """
    # Map filter names to more readable versions
    filter_name_map = {
        'keyLike': 'SEARCH',
        'tags': 'TAG',
        'repository': 'REPO',
        'cidr': 'CIDR',
        'fqdn': 'FQDN',
        'netbios': 'NETBIOS',
        'osNames': 'OS',
        'hostnames': 'HOST',
        'providerAccountId': 'ACCOUNT-ID',
        'providerAccountName': 'ACCOUNT-NAME',
        'resourceGroup': 'RESOURCE-GROUP',
        'assetType': 'ASSET-TYPE'
    }
    
    method = filter_name_map.get(filter_name, filter_name.upper())
    
    # Handle different types of filter values
    if isinstance(filter_value, list):
        if filter_name == 'tags':
            # Handle tag lists
            tag_values = []
            for tag in filter_value:
                if isinstance(tag, dict):
                    if 'key' in tag and 'value' in tag:
                        tag_values.append(f"{tag['key']}:{tag['value']}")
                    elif 'value' in tag:
                        tag_values.append(tag['value'])
            value_str = ', '.join(tag_values[:2])  # Limit to first 2 tags
            if len(tag_values) > 2:
                value_str += f" +{len(tag_values)-2}"
        else:
            # Handle other list types
            value_str = ', '.join(str(v) for v in filter_value[:2])
            if len(filter_value) > 2:
                value_str += f" +{len(filter_value)-2}"
    else:
        value_str = str(filter_value)
    
    # Truncate value_str if too long
    if len(value_str) > 50:
        value_str = value_str[:47] + "..."
    
    return f"R-{method} for {component_name} ({value_str})"

def create_component_rule(applicationName, componentName, filterName, filterValue, ruleName, headers):
    print(f"\n[Rule Operation]")
    print(f"└─ Application: {applicationName}")
    print(f"└─ Component: {componentName}")
    print(f"└─ Filter Type: {filterName}")
    
    if DEBUG:
        print("└─ Filter Value:", end=" ")
        if isinstance(filterValue, list):
            print(json.dumps(filterValue, indent=2))
        else:
            print(filterValue)

    # Map filter names to their correct API case-sensitive versions
    filter_name_mapping = {
        'keylike': 'keyLike',
        'searchname': 'keyLike',
        'searchName': 'keyLike',
        'osnames': 'osNames',
        'provideraccountid': 'providerAccountId',
        'provideraccountname': 'providerAccountName',
        'resourcegroup': 'resourceGroup',
        'assettype': 'assetType',
        'tags': 'tags'
    }

    # Special handling for tags
    if filterName.lower() == 'tags':
        if isinstance(filterValue, list) and all(isinstance(tag, dict) and ('value' in tag or ('key' in tag and 'value' in tag)) for tag in filterValue):
            filter_content = filterValue
        else:
            tags = filterValue if isinstance(filterValue, list) else [filterValue]
            filter_content = [{"value": tag} for tag in tags if tag and len(str(tag).strip()) >= 3]
    else:
        filter_content = filterValue

    api_filter_name = filter_name_mapping.get(filterName.lower(), filterName)

    if api_filter_name == 'keyLike' and isinstance(filter_content, (list, dict)):
        if isinstance(filter_content, list):
            filter_content = filter_content[0] if filter_content else ""
        elif isinstance(filter_content, dict):
            filter_content = str(filter_content.get('value', ''))

    # Generate descriptive rule name
    descriptive_rule_name = generate_descriptive_rule_name(componentName, api_filter_name, filter_content)
    print(f"└─ Generated Rule Name: {descriptive_rule_name}")

    rule = {
        "name": descriptive_rule_name,
        "filter": {api_filter_name: filter_content}
    }

    payload = {
        "selector": {
            "applicationSelector": {"name": applicationName, "caseSensitive": False},
            "componentSelector": {"name": componentName, "caseSensitive": False}
        },
        "rules": [rule]
    }

    if DEBUG:
        print("\nPayload:")
        print(json.dumps(payload, indent=2))
        print("-" * 80)

    # Enhanced retry configuration with smarter throttling
    max_retries = 5
    base_delay = 0   # Start with no delay
    max_delay = 30
    jitter_factor = 0.1
    
    def calculate_delay(consecutive_timeouts):
        if consecutive_timeouts == 0:
            return 0
        exponential_delay = min(max_delay, 2 ** (consecutive_timeouts - 1))
        jitter = random.uniform(0, jitter_factor * exponential_delay)
        return exponential_delay + jitter

    consecutive_timeouts = 0
    total_attempts = 0
    last_error = None
    current_delay = 0

    while total_attempts < max_retries:
        try:
            if current_delay > 0:
                print(f" * Rate limiting active - waiting {current_delay:.1f}s before retry {total_attempts + 1}/{max_retries}...")
                time.sleep(current_delay)

            api_url = construct_api_url("/v1/components/rules")
            
            request_headers = headers.copy()
            if consecutive_timeouts > 1:
                request_headers['X-Rate-Limit-Wait'] = str(int(current_delay))
                request_headers['X-Client-Timeout'] = str(max(30, current_delay * 2))
            
            timeout = max(30, current_delay * 2) if consecutive_timeouts > 0 else 30
            
            response = requests.post(api_url, headers=request_headers, json=payload, timeout=timeout)
            
            if response.status_code == 201:
                if consecutive_timeouts > 0:
                    print(f" + Success after {consecutive_timeouts} retries")
                print(f"└─ Rule created: {descriptive_rule_name}")
                if DEBUG:
                    print(f"   └─ Application: {applicationName}")
                    print(f"   └─ Component: {componentName}")
                    print(f"   └─ Filter: {json.dumps(rule['filter'], indent=2)}")
                # Log successful rule creation
                log_error(
                    'Rule Creation',
                    f"{componentName} -> {descriptive_rule_name}",
                    applicationName,
                    'Rule created successfully',
                    f'Filter: {json.dumps(rule["filter"])}' if DEBUG else None
                )
                return True
                
            elif response.status_code == 409:
                print(f"└─ Rule already exists: {descriptive_rule_name}")
                if DEBUG:
                    print(f"   └─ Application: {applicationName}")
                    print(f"   └─ Component: {componentName}")
                    print(f"   └─ Filter: {json.dumps(rule['filter'], indent=2)}")
                # Log existing rule
                log_error(
                    'Rule Update',
                    f"{componentName} -> {descriptive_rule_name}",
                    applicationName,
                    'Rule already exists',
                    f'Filter: {json.dumps(rule["filter"])}' if DEBUG else None
                )
                return True
                
            elif response.status_code in [503, 429]:
                consecutive_timeouts += 1
                last_error = f"{response.status_code} {'Service Unavailable' if response.status_code == 503 else 'Rate Limit'}"
                
                if response.status_code == 429 and 'Retry-After' in response.headers:
                    current_delay = int(response.headers['Retry-After'])
                else:
                    current_delay = calculate_delay(consecutive_timeouts)
                
                print(f" ! {last_error}. Throttling activated. (Attempt {total_attempts + 1}/{max_retries})")
                
            elif response.status_code == 404:
                last_error = "404 Not Found"
                print(f" ! Service not found. (Attempt {total_attempts + 1}/{max_retries})")
                consecutive_timeouts = 0
                current_delay = 0
                
            elif response.status_code == 400:
                error_msg = f"Bad request error: {response.content}"
                print(f"└─ Rule creation failed: {descriptive_rule_name}")
                if DEBUG:
                    print(f"   └─ Application: {applicationName}")
                    print(f"   └─ Component: {componentName}")
                    print(f"   └─ Error: {error_msg}")
                log_error(
                    'Rule Creation Failed',
                    f"{componentName} -> {descriptive_rule_name}",
                    applicationName,
                    error_msg,
                    f'Filter: {json.dumps(rule["filter"])}' if DEBUG else None
                )
                return False
                
            else:
                last_error = f"HTTP {response.status_code}"
                print(f" ! Unexpected error {response.status_code}. (Attempt {total_attempts + 1}/{max_retries})")
                consecutive_timeouts = 0
                current_delay = 0
            
        except requests.exceptions.Timeout:
            last_error = "Request timeout"
            print(f" ! Request timeout. (Attempt {total_attempts + 1}/{max_retries})")
            consecutive_timeouts += 1
            current_delay = calculate_delay(consecutive_timeouts)
            
        except requests.exceptions.RequestException as e:
            last_error = str(e)
            print(f" ! Network error: {str(e)}. (Attempt {total_attempts + 1}/{max_retries})")
            if "timeout" in str(e).lower():
                consecutive_timeouts += 1
                current_delay = calculate_delay(consecutive_timeouts)
            else:
                consecutive_timeouts = 0
                current_delay = 0
            
        total_attempts += 1
        
        if consecutive_timeouts >= 3:
            long_break = min(max_delay, 4 * calculate_delay(consecutive_timeouts))
            print(f" ! Multiple consecutive timeouts detected. Taking a {long_break:.1f}s break...")
            time.sleep(long_break)
            consecutive_timeouts = 1
            current_delay = calculate_delay(consecutive_timeouts)

    # Log final error after all retries exhausted
    print(f"└─ Rule creation failed after {max_retries} attempts: {descriptive_rule_name}")
    if DEBUG:
        print(f"   └─ Application: {applicationName}")
        print(f"   └─ Component: {componentName}")
        print(f"   └─ Last error: {last_error}")
    log_error(
        'Rule Creation Failed',
        f"{componentName} -> {ruleName}",
        applicationName,
        f"Failed after {max_retries} attempts. Last error: {last_error}",
        f'Filter: {json.dumps(rule["filter"])}' if DEBUG else None
    )
    return False

def create_user_for_application(existing_users_emails, newly_created_users_emails, email, access_token):
    email = email.lower()
    # try to get first and last name from email
    if email in existing_users_emails:
        print(f"User with email already registered: {email}")
        return
    
    if email in newly_created_users_emails:
        if DEBUG:
            print(f"User with email already created: {email}")
        return

    user_first_name, user_last_name = extract_user_name_from_email(email)
    if not user_first_name or not user_last_name:
        print(f'  ! Missing either first or last name, skipping user creation. \
              First Name: {user_first_name}. Last Name: {user_last_name}')
        return
    try:
        created_user = api_call_create_user(email, user_first_name, user_last_name, "ORG_USER", access_token)
        if created_user:
            return email
    except Exception as e:
        print(f'  ! Error creating user for application: {e}')
        log_error(
            'Create user for application',
            email,
            'N/A',
            f'Error creating user for application, error: {e}'
        )
        return


def api_call_create_user(email, first_name, last_name, role, access_token):
    """
    API call to create user in Phoenix
    
    Args:
        email (str): Email of a user
        first_name (str): First name of a user
        last_name (str): Last name of a user
        role (str): Role of a user. Allowed values ("ORG_ADMIN", "ORG_APP_ADMIN", "ORG_USER", 
                    "ORG_ADMIN_LITE", "ORG_SEC_ADMIN", "ORG_SEC_DEV")
        access_token: Access token
        
    Returns:
        str: Created user's email
    """
    validate_user_role(role)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "email": email, 
        "firstName": first_name, 
        "lastName": last_name, 
        "role": role
    }
    
    if DEBUG:
        print(f'Payload sent to create user {json.dumps(payload, indent=2)}')

    current_try = 0
    max_retries = 3

    while current_try < max_retries:
        try:
            api_url = construct_api_url(f"/v1/users")
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            print(f" + User {email} added")
            return payload
        except requests.exceptions.RequestException as e:
            if response.status_code == 400:
                log_error(
                    'Create user for application',
                    email,
                    'N/A',
                    f'Bad request when creating user, error: {e}'
                )
                print(f" ? Bad request when creating user for application, email {email}")
                break
            elif response.status_code == 409:
                log_error(
                    'Create user for application',
                    email,
                    'N/A',
                    'User already exists in platform with that email, please define another email'
                )
                print(f" - User already exists in platfrom with email: {email}, please choose another email")
                break
            elif response.status_code in [429, 503]: # Rate limit or service unavailable
                retry_after = int(response.headers.get('Retry-After', 5))
                print(f" * Rate limited, waiting {retry_after} seconds...")
                time.sleep(retry_after)
                current_try += 1
                continue
            elif response.status_code >= 500:  # Server error
                print(" * Server error, retrying after 5 seconds...")
                time.sleep(5)
                current_try += 1
                continue
            else:
                log_error(
                    'Create user for application',
                    email,
                    'N/A',
                    'Error when creating user, error: {e}'
                )
                print(f" ! Error creating user: {e}")
                break
    return

def load_users_from_phoenix(access_token):
    """
    Load all users from Phoenix with proper pagination and error handling.
    
    Args:
        access_token: API access token
        
    Returns:
        list: Complete list of all users across all pages
        
    Raises:
        requests.exceptions.RequestException: If there's an error fetching users
    """
    users = []
    page_size = 100
    page_number = 0
    total_pages = None
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    print("\n[User Listing]")
    print(" * Fetching all users with pagination...")
    
    while total_pages is None or page_number < total_pages:
        try:
            api_url = construct_api_url("/v1/users")
            params = {
                "pageSize": page_size,
                "pageNumber": page_number,
                "sort": "email,asc"  # Sort by email for consistent listing
            }
            
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Add users from current page
            page_users = data.get('content', [])
            users.extend(page_users)
            
            # Update total pages on first iteration
            if total_pages is None:
                total_pages = data.get('totalPages', 1)
                total_elements = data.get('totalElements', 0)
                print(f" * Found {total_elements} total users across {total_pages} pages")
            
            if DEBUG:
                print(f" * Fetched page {page_number + 1}/{total_pages} ({len(page_users)} users)")
                for user in page_users:
                    print(f"   - [Unknown] {user.get('email', 'No email')}")
            
            page_number += 1
            
            # Add small delay between pages to avoid rate limiting
            if page_number < total_pages:
                time.sleep(0.5)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching users page {page_number}: {str(e)}"
            log_error(
                'User Listing',
                'N/A',
                'N/A',
                error_msg,
                f'Response: {getattr(response, "content", "No response content")}'
            )
            print(f" ! {error_msg}")
            
            if response.status_code in [429, 503]:  # Rate limit or service unavailable
                retry_after = int(response.headers.get('Retry-After', 5))
                print(f" * Rate limited, waiting {retry_after} seconds...")
                time.sleep(retry_after)
                continue
            elif response.status_code >= 500:  # Server error
                print(" * Server error, retrying after 5 seconds...")
                time.sleep(5)
                continue
            else:
                raise  # Re-raise other exceptions
    
    print(f" * Total users fetched: {len(users)}")
    return users

def get_user_info(email, headers):
    """
    Get user information from Phoenix.
    
    Args:
        email: User's email address
        headers: Request headers containing authorization
        
    Returns:
        dict: User information if found, None otherwise
    """
    try:
        api_url = construct_api_url(f"/v1/users/{email}")
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 404:
            return None
            
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Error getting user info for {email}: {str(e)}")
        return None

def clean_user_name(name):
    """
    Clean user name by removing the User suffix if present.
    
    Args:
        name: User's name that might have User suffix
        
    Returns:
        str: Clean name without User suffix
    """
    if name and name.endswith(" User"):
        return name[:-5].strip()
    return name

def create_user_with_role(email, first_name, last_name, role, headers):
    """
    Create a user with a specific role.
    
    Args:
        email: User's email address
        first_name: User's first name
        last_name: User's last name
        role: User's role (SECURITY_CHAMPION, ENGINEERING_USER, APPLICATION_ADMIN, or ORG_USER)
        headers: Request headers containing authorization
    """
    if not email or not first_name or not last_name:
        print(f"⚠️ Error: Missing required user information for {email}")
        return None

    # Clean names to remove User suffix if present
    first_name = clean_user_name(first_name)
    last_name = clean_user_name(last_name)

    payload = {
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "role": role
    }

    if DEBUG:
        print(f"\nCreating user:")
        print(f"└─ Email: {email}")
        print(f"└─ Name: {first_name} {last_name}")
        print(f"└─ Role: {role}")

    try:
        api_url = construct_api_url("/v1/users")
        response = requests.post(api_url, headers=headers, json=payload)
        
        if response.status_code == 409:
            print(f" * User {email} already exists")
            # Check if we need to update the user's name
            existing_user = get_user_info(email, headers)
            if existing_user and (existing_user.get('firstName', '').endswith(' User') or 
                                existing_user.get('lastName', '').endswith(' User')):
                # Update user to remove User suffix
                update_payload = {
                    "firstName": first_name,
                    "lastName": last_name
                }
                update_response = requests.patch(api_url + f"/{email}", headers=headers, json=update_payload)
                if update_response.status_code == 200:
                    print(f" * Updated user name format for {email}")
            return None
        
        response.raise_for_status()
        print(f" + Created user: {email} with role {role}")
        return payload
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to create user {email}: {str(e)}"
        error_details = f'Response: {getattr(response, "content", "No response content")}\nPayload: {json.dumps(payload)}'
        log_error(
            'User Creation',
            email,
            'N/A',
            error_msg,
            error_details
        )
        print(f"⚠️ {error_msg}")
        if DEBUG:
            print(f"Response content: {response.content}")
        return None
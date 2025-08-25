import base64
import requests
import json
import time
import os
import Levenshtein
import random
from multipledispatch import dispatch

# Global tracking callback for main script reporting
component_tracking_callback = None

def set_component_tracking_callback(callback_func):
    """Set the callback function for tracking component operations from the main script"""
    global component_tracking_callback
    component_tracking_callback = callback_func

def track_application_component_operations(callback_func):
    """Configure component tracking for the main script reporting"""
    set_component_tracking_callback(callback_func)
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
ASSET_NAME_SIMILARITY_THRESHOLD = 0.8 # Levenshtein ratio for comparing asset name similarity (0.8 = 80% similarity)
ASSET_GROUP_MIN_SIZE_FOR_COMPONENT_CREATION = 3 # Minimal number of assets with similar name that will trigger component creation

APIdomain = "https://api.demo.appsecphx.io/" #change this with your specific domain
DEBUG = False #debug settings to trigger debug output 
access_token = None
headers = {}

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

def create_environment(environment, headers2):
    global headers
    if not headers:
        headers = headers2
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


def update_environment(environment, existing_environment, headers2):
    global headers
    if not headers:
        headers = headers2
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
def add_environment_services(repos, subdomains, environments, application_environments, phoenix_components, subdomain_owners, teams, access_token2):
    global access_token
    if not access_token:
        access_token = access_token2
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
def add_container_rule(image, subdomain, environment_name, access_token2):
    global access_token
    if not access_token:
        access_token = access_token2
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

def add_service_rule_batch(application_environments, environment, service, service_id, headers2):
    global headers
    if not headers:
        headers = headers2
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
        ('Tag_rule', 'tags', service.get('Tag_rule')),
        ('Tags_rule', 'tags', service.get('Tags_rule')),
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
                if rule_type in ['Tag', 'Tag_rule', 'Tags_rule']:
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
                                        f"Rule for {rule_type} {tag_parts[0]}:{tag_parts[1]} for {serviceName}", 
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
                                    f"Rule for {rule_type} {tag_parts[0]}:{tag_parts[1]} for {serviceName}", 
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
def add_service_rule(environment, service, tag_name, tag_value, access_token2):
    global access_token
    if not access_token:
        access_token = access_token2
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


def create_applications(applications, application_environments, phoenix_components, headers2):
    global headers
    if not headers:
        headers = headers2
    print('[Applications]')
    print(f'└─ Processing {len(applications)} applications from config')
    
    # Debug: Show existing applications
    existing_apps = [env for env in application_environments if env.get('type') == "APPLICATION"]
    print(f'└─ Found {len(existing_apps)} existing applications in Phoenix:')
    for app in existing_apps:
        print(f'   └─ {app.get("name", "Unknown")}')
    
    for application in applications:
        app_name = application['AppName']
        print(f'\n└─ Processing application: {app_name}')
        
        # Check if application exists
        existing_app = next((env for env in application_environments if env['name'] == app_name and env['type'] == "APPLICATION"), None)
        
        if not existing_app:
            print(f'   └─ Application does not exist, creating...')
            create_application(application, headers)
        else:
            print(f'   └─ Application exists (ID: {existing_app.get("id", "Unknown")}), updating...')
            try:
                update_application(application, application_environments, phoenix_components, headers)
            except Exception as e:
                error_msg = f"Failed to update application {app_name}: {str(e)}"
                log_error(
                    'Application Update Failed',
                    app_name,
                    'N/A',
                    error_msg,
                    f'Exception during update: {e}'
                )
                print(f'   └─ Error: {error_msg}')
                continue

def create_application(app, headers2):
    global headers
    if not headers:
        headers = headers2
    print(f"\n[Application Creation]")
    print(f"└─ Creating: {app['AppName']}")
    
    payload = {
        "name": app['AppName'],
        "type": "APPLICATION",
        "criticality": app['Criticality'],
        "tags": [],
        "owner": {"email": app['Responsable']}
    }
    
    print(f"└─ Debug - Criticality value: {app['Criticality']} (type: {type(app['Criticality'])})")
    print(f"└─ Debug - Owner email: '{app['Responsable']}' (type: {type(app['Responsable'])})")
    print(f"└─ Debug - App name: '{app['AppName']}' (length: {len(app['AppName'])})")

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
        print(f"└─ Debug - Adding team tag: pteam={team}")
    
    # Add tags from the Tag_label and Tags_label fields in YAML configuration
    print(f"└─ Processing application Tag_label field...")
    if app.get('Tag_label'):
        tag_label = app.get('Tag_label')
        print(f"└─ Found application Tag_label: {tag_label}")
        print(f"└─ Tag_label type: {type(tag_label)}")
        
        if isinstance(tag_label, str):
            # Handle single string tag
            processed_tag = process_tag_string(tag_label)
            payload['tags'].append(processed_tag)
            print(f"└─ Added application Tag_label: {processed_tag}")
        elif isinstance(tag_label, list):
            print(f"└─ Processing {len(tag_label)} application Tag_label entries...")
            for i, tag in enumerate(tag_label):
                print(f"└─ Processing application Tag_label[{i}]: '{tag}' (type: {type(tag)})")
                if isinstance(tag, str):
                    processed_tag = process_tag_string(tag)
                    payload['tags'].append(processed_tag)
                    print(f"└─ Added application Tag_label[{i}]: {processed_tag}")
                elif isinstance(tag, dict):
                    if 'key' in tag and 'value' in tag:
                        tag_dict = {"key": tag['key'], "value": tag['value']}
                        payload['tags'].append(tag_dict)
                        print(f"└─ Added application Tag_label[{i}] dict: {tag_dict}")
                    elif 'value' in tag:
                        tag_dict = {"value": tag['value']}
                        payload['tags'].append(tag_dict)
                        print(f"└─ Added application Tag_label[{i}] value-only: {tag_dict}")
    else:
        print(f"└─ No Tag_label field found in application")
    
    if app.get('Tags_label'):
        print(f"└─ Processing application Tags_label field...")
        for i, tag in enumerate(app.get('Tags_label')):
            print(f"└─ Processing application Tags_label[{i}]: '{tag}' (type: {type(tag)})")
            if isinstance(tag, str):
                # Handle string tags using helper function
                processed_tag = process_tag_string(tag)
                payload['tags'].append(processed_tag)
                print(f"└─ Added application Tags_label[{i}]: {processed_tag}")
            elif isinstance(tag, dict):
                # Handle dict tags that already have key/value structure
                if 'key' in tag and 'value' in tag:
                    tag_dict = {"key": tag['key'], "value": tag['value']}
                    payload['tags'].append(tag_dict)
                    print(f"└─ Added application Tags_label[{i}] dict: {tag_dict}")
                elif 'value' in tag:
                    tag_dict = {"value": tag['value']}
                    payload['tags'].append(tag_dict)
                    print(f"└─ Added application Tags_label[{i}] value-only: {tag_dict}")
    
    # Show final tag summary for application
    print(f"└─ FINAL APPLICATION TAG SUMMARY for {app['AppName']}:")
    print(f"└─ Total tags to be sent: {len(payload['tags'])}")
    for i, tag in enumerate(payload['tags']):
        if 'key' in tag and 'value' in tag:
            print(f"   {i+1:2d}. {tag['key']}: {tag['value']}")
        elif 'value' in tag:
            print(f"   {i+1:2d}. {tag['value']} (value only)")
    
    print(f"└─ Final payload:")
    print(json.dumps(payload, indent=2))

    app_id = None
    application_created = False
    
    try:
        api_url = construct_api_url("/v1/applications")
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"└─ Application created successfully")
        
        # Get the application ID from the response for tag addition
        app_response = response.json()
        app_id = app_response.get('id')
        application_created = True
        
    except requests.exceptions.RequestException as e:
        if response.status_code == 409:
            print(f"└─ Application {app['AppName']} already exists")
            # Application exists, get its ID for tag addition
            existing_apps = populate_applications_and_environments(headers)
            existing_app = next((app_item for app_item in existing_apps if app_item['name'] == app['AppName'] and app_item['type'] == 'APPLICATION'), None)
            if existing_app:
                app_id = existing_app.get('id')
                print(f"└─ Found existing application ID: {app_id}")
            else:
                print(f"└─ Could not find existing application ID for tag addition")
                # Log this as an error since we have tags to add but can't find the application
                if payload.get('tags'):
                    log_error(
                        'Application Tag Addition - ID Lookup Failed',
                        app['AppName'],
                        'N/A',
                        'Could not find existing application ID for tag addition',
                        f'Application name: {app["AppName"]}\nTags to add: {len(payload.get("tags", []))}\nTag details: {json.dumps(payload.get("tags", []), indent=2)}'
                    )
        elif response.status_code == 400 and b'Invalid user email' in response.content:
            # Handle invalid user email specifically
            user_email = app['Responsable']
            print(f"└─ ⚠️  Invalid user email: {user_email}")
            print(f"└─ 💡 This user doesn't exist in Phoenix platform")
            print(f"└─ 🔧 Consider:")
            print(f"   • Creating the user first in Phoenix")
            print(f"   • Using a valid existing user email")
            print(f"   • Enabling auto-user creation in config")
            
            # Try with a fallback default user if available
            fallback_email = "fc+mimecast@phoenix.security"  # Use the configured default
            print(f"└─ 🔄 Attempting to create application with fallback user: {fallback_email}")
            
            # Update payload with fallback user
            fallback_payload = payload.copy()
            fallback_payload["owner"]["email"] = fallback_email
            
            try:
                api_url = construct_api_url("/v1/applications")
                fallback_response = requests.post(api_url, headers=headers, json=fallback_payload)
                fallback_response.raise_for_status()
                print(f"└─ ✅ Application created successfully with fallback user")
                
                # Get the application ID from the response for tag addition
                app_response = fallback_response.json()
                app_id = app_response.get('id')
                application_created = True
                
            except requests.exceptions.RequestException as fallback_error:
                error_msg = f"Failed to create application even with fallback user: {str(fallback_error)}"
                print(f"└─ ❌ {error_msg}")
                log_error(
                    'Application Creation Failed - Invalid User',
                    app['AppName'],
                    'N/A',
                    f'Original user: {user_email}, Fallback user: {fallback_email}',
                    f'Original error: {response.content}\nFallback error: {fallback_response.content if "fallback_response" in locals() else "N/A"}'
                )
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
            print(f"└─ Response content: {getattr(response, 'content', 'No response content')}")
            print(f"└─ Payload sent: {json.dumps(payload, indent=2)}")
            return
    
    # Add tags separately using the dedicated tags endpoint if we have tags to add
    # This works for both newly created applications and existing ones
    if payload.get('tags') and app_id:
        print(f"└─ Adding {len(payload['tags'])} tags to application ID: {app_id}")
        if DEBUG:
            print(f"└─ DEBUG: Tags to add: {json.dumps(payload.get('tags'), indent=2)}")
        
        tags_attempted = 0
        tags_succeeded = 0
        tags_failed = 0
        tags_skipped = 0
        
        for i, tag in enumerate(payload['tags']):
            print(f"   └─ Processing tag {i+1}/{len(payload['tags'])}: {tag}")
            tags_attempted += 1
            
            if 'key' in tag and 'value' in tag:
                print(f"   └─ Adding key-value tag: {tag['key']}: {tag['value']}")
                try:
                    add_tag_to_application(tag['key'], tag['value'], app_id, headers)
                    tags_succeeded += 1
                except Exception as e:
                    tags_failed += 1
                    print(f"   └─ ❌ Tag addition failed: {e}")
            elif 'value' in tag:
                print(f"   └─ Adding value-only tag: {tag['value']}")
                try:
                    # For value-only tags, we'll use a custom call since the existing function requires a key
                    add_application_tag_custom(app_id, tag, headers)
                    tags_succeeded += 1
                except Exception as e:
                    tags_failed += 1
                    print(f"   └─ ❌ Tag addition failed: {e}")
            else:
                print(f"   └─ ⚠️ Skipping invalid tag format: {tag}")
                tags_skipped += 1
                # Log invalid tag format
                log_error(
                    'Application Tag Addition - Invalid Format',
                    f"App ID: {app_id} -> Invalid Tag",
                    'N/A',
                    'Skipping tag due to invalid format',
                    f'Tag data: {json.dumps(tag)}\nExpected format: {{"key": "string", "value": "string"}} or {{"value": "string"}}'
                )
        
        # Summary of tag addition results
        print(f"└─ 📊 Tag Addition Summary for {app['AppName']}:")
        print(f"   └─ Total attempted: {tags_attempted}")
        print(f"   └─ ✅ Succeeded: {tags_succeeded}")
        print(f"   └─ ❌ Failed: {tags_failed}")
        print(f"   └─ ⚠️ Skipped: {tags_skipped}")
        
        # Log summary if there were any failures
        if tags_failed > 0 or tags_skipped > 0:
            log_error(
                'Application Tag Addition Summary',
                f"{app['AppName']} (ID: {app_id})",
                'N/A',
                f'Tag addition completed with issues: {tags_failed} failed, {tags_skipped} skipped',
                f'Total attempted: {tags_attempted}\nSucceeded: {tags_succeeded}\nFailed: {tags_failed}\nSkipped: {tags_skipped}'
            )
    elif payload.get('tags') and not app_id:
        print(f"└─ ⚠️ Cannot add tags: Application ID not found")
        print(f"└─ DEBUG: Tags that would be added: {json.dumps(payload.get('tags'), indent=2)}")
        
        # Log this as an error since we have tags to add but no application ID
        log_error(
            'Application Tag Addition - No App ID',
            app['AppName'],
            'N/A',
            'Cannot add tags: Application ID not found',
            f'Application name: {app["AppName"]}\nTags to add: {len(payload.get("tags", []))}\nTag details: {json.dumps(payload.get("tags", []), indent=2)}'
        )
    elif not payload.get('tags'):
        print(f"└─ ℹ️ No tags to add to application")
    else:
        print(f"└─ ℹ️ No tag addition needed (no tags or no app ID)")
    
    time.sleep(2)
    
    # Create components if any
    if app.get('Components'):
        print(f"└─ Processing {len(app['Components'])} components")
        for component in app['Components']:
            create_custom_component(app['AppName'], component, headers)

def process_tag_string(tag_string):
    """Helper function to properly process tag strings, especially RiskFactor tags with multiple colons"""
    if ':' in tag_string:
        # Handle special case for RiskFactor tags with multiple colons
        if tag_string.startswith('RiskFactor:') and tag_string.count(':') >= 2:
            # Find the last colon to split key and value
            last_colon_index = tag_string.rfind(':')
            key = tag_string[:last_colon_index].strip()
            value = tag_string[last_colon_index + 1:].strip()
            return {"key": key, "value": value}
        else:
            # Standard key:value processing
            tag_parts = tag_string.split(':', 1)
            key = tag_parts[0].strip()
            value = tag_parts[1].strip()
            return {"key": key, "value": value}
    else:
        # Handle tags without key:value format
        return {"value": tag_string}

def add_application_tag_custom(app_id, tag, headers):
    """Add a single tag to an application using the tags endpoint"""
    try:
        api_url = construct_api_url(f"/v1/applications/{app_id}/tags")
        tags_payload = {"tags": [tag]}
        
        if DEBUG:
            print(f"   └─ DEBUG: Sending PUT request to {api_url}")
            print(f"   └─ DEBUG: Payload: {json.dumps(tags_payload, indent=2)}")
        
        response = requests.put(api_url, headers=headers, json=tags_payload)
        response.raise_for_status()
        
        if 'key' in tag and 'value' in tag:
            print(f"   └─ ✅ Successfully added tag {tag['key']}: {tag['value']}")
        else:
            print(f"   └─ ✅ Successfully added tag: {tag['value']}")
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to add tag to application: {str(e)}"
        print(f"   └─ ❌ Error adding tag: {error_msg}")
        
        # Log detailed error information
        tag_description = f"{tag.get('key', 'NO_KEY')}:{tag.get('value', 'NO_VALUE')}" if tag.get('key') else tag.get('value', 'INVALID_TAG')
        log_error(
            'Application Tag Addition',
            f"App ID: {app_id} -> Tag: {tag_description}",
            'N/A',
            error_msg,
            f'API URL: {api_url}\nPayload: {json.dumps(tags_payload)}\nResponse: {getattr(response, "content", "No response content")}'
        )
        
        if hasattr(response, 'content'):
            print(f"   └─ API Response: {response.content.decode()}")
        if hasattr(response, 'status_code'):
            print(f"   └─ Status Code: {response.status_code}")
    except Exception as e:
        error_msg = f"Unexpected error adding tag: {str(e)}"
        print(f"   └─ ❌ Unexpected error: {error_msg}")
        
        tag_description = f"{tag.get('key', 'NO_KEY')}:{tag.get('value', 'NO_VALUE')}" if tag.get('key') else tag.get('value', 'INVALID_TAG')
        log_error(
            'Application Tag Addition (Unexpected)',
            f"App ID: {app_id} -> Tag: {tag_description}",
            'N/A',
            error_msg,
            f'Tag data: {json.dumps(tag)}\nException type: {type(e).__name__}'
        )

def create_custom_component(applicationName, component, headers2):
    global headers
    if not headers:
        headers = headers2
    print(f"\n[Component Creation]")
    print(f"└─ Application: {applicationName}")
    print(f"└─ Component: {component['ComponentName']}")
    print(f"└─ Component Data: {component}")

    # Ensure valid tag values by filtering out empty or None 
    tags = []
    print(f"└─ Processing component tags...")
    
    if component.get('Status'):
        tags.append({"key": "Status", "value": component['Status']})
        print(f"└─ Added Status tag: Status = {component['Status']}")
    if component.get('Type'):
        tags.append({"key": "Type", "value": component['Type']})
        print(f"└─ Added Type tag: Type = {component['Type']}")

    # Add team tags
    for team in component.get('TeamNames', []):
        if team:  # Only add non-empty team names
            tags.append({"key": "pteam", "value": team})
            print(f"└─ Added Team tag: pteam = {team}")

    # Add domain and subdomain tags only if they are not None or empty
    if component.get('Domain'):
        tags.append({"key": "domain", "value": component['Domain']})
        print(f"└─ Added Domain tag: domain = {component['Domain']}")
    if component.get('SubDomain'):
        tags.append({"key": "subdomain", "value": component['SubDomain']})
        print(f"└─ Added Subdomain tag: subdomain = {component['SubDomain']}")
    
    # Add tags from the Tag_label and Tags_label fields in YAML configuration
    print(f"└─ Processing Tag_label field...")
    if component.get('Tag_label'):
        tag_label = component.get('Tag_label')
        print(f"└─ Found Tag_label: {tag_label}")
        print(f"└─ Tag_label type: {type(tag_label)}")
        
        if isinstance(tag_label, str):
            # Handle single string tag
            processed_tag = process_tag_string(tag_label)
            tags.append(processed_tag)
            print(f"└─ Processed single Tag_label: {processed_tag}")
        elif isinstance(tag_label, list):
            print(f"└─ Processing {len(tag_label)} Tag_label entries...")
            for i, tag in enumerate(tag_label):
                print(f"└─ Processing Tag_label[{i}]: '{tag}' (type: {type(tag)})")
                if isinstance(tag, str):
                    processed_tag = process_tag_string(tag)
                    tags.append(processed_tag)
                    print(f"└─ Added Tag_label[{i}]: {processed_tag}")
                elif isinstance(tag, dict):
                    if 'key' in tag and 'value' in tag:
                        tag_dict = {"key": tag['key'], "value": tag['value']}
                        tags.append(tag_dict)
                        print(f"└─ Added Tag_label[{i}] dict: {tag_dict}")
                    elif 'value' in tag:
                        tag_dict = {"value": tag['value']}
                        tags.append(tag_dict)
                        print(f"└─ Added Tag_label[{i}] value-only: {tag_dict}")
    else:
        print(f"└─ No Tag_label field found in component")
    
    if component.get('Tags_label'):
        for tag in component.get('Tags_label'):
            if isinstance(tag, str):
                # Handle string tags using helper function
                tags.append(process_tag_string(tag))
            elif isinstance(tag, dict):
                # Handle dict tags that already have key/value structure
                if 'key' in tag and 'value' in tag:
                    tags.append({"key": tag['key'], "value": tag['value']})
                elif 'value' in tag:
                    tags.append({"value": tag['value']})

    payload = {
        "applicationSelector": {
            "name": applicationName
        },
        "name": component['ComponentName'],
        "criticality": calculate_criticality(component.get('Tier', 5)),  # Calculate from Tier field
        "tags": tags
    }
    
    # Always show final tag summary for troubleshooting
    print(f"└─ FINAL TAG SUMMARY for component {component['ComponentName']}:")
    print(f"└─ Total tags to be sent: {len(tags)}")
    for i, tag in enumerate(tags):
        if 'key' in tag and 'value' in tag:
            print(f"   {i+1:2d}. {tag['key']}: {tag['value']}")
        elif 'value' in tag:
            print(f"   {i+1:2d}. {tag['value']} (value only)")
    
    if len(tags) == 0:
        print(f"└─ ⚠️  WARNING: No tags will be sent with this component!")

    # Handle ticketing configuration
    if component.get('Ticketing'):
        try:
            ticketing = component['Ticketing']
            if isinstance(ticketing, list):
                ticketing = ticketing[0] if ticketing else {}
            
            integration_name = ticketing.get('TIntegrationName')
            backlog = ticketing.get('Backlog')
            
            if integration_name and backlog:
                payload["ticketing"] = {
                    "integrationName": integration_name,
                    "projectName": backlog
                }
                print(f"└─ Adding ticketing configuration:")
                print(f"   └─ Integration: {integration_name}")
                print(f"   └─ Project: {backlog}")
            else:
                print(f"└─ Warning: Skipping ticketing configuration - missing required fields")
                print(f"   └─ TIntegrationName: {integration_name}")
                print(f"   └─ Backlog: {backlog}")
        except Exception as e:
            print(f"└─ Warning: Error processing ticketing configuration: {e}")
            print(f"└─ Continuing component creation without ticketing integration")

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

    # Always show the full payload being sent to the API
    print(f"└─ SENDING COMPONENT CREATION REQUEST:")
    print(f"└─ API URL: {construct_api_url('/v1/components')}")
    print(f"└─ Full Payload:")
    print(json.dumps(payload, indent=2))

    api_url = construct_api_url("/v1/components")

    try:
        print(f"└─ Making POST request to create component...")
        response = requests.post(api_url, headers=headers, json=payload)
        print(f"└─ API Response Status: {response.status_code}")
        print(f"└─ API Response Content: {response.content.decode('utf-8') if response.content else 'No content'}")
        response.raise_for_status()
        print(f"└─ ✅ Component created successfully")
        
        # Track successful component creation for main script reporting
        if component_tracking_callback:
            component_tracking_callback('components', 'create_component', f"{applicationName} -> {component['ComponentName']}", True)
        
        time.sleep(2)
    except requests.exceptions.RequestException as e:
        if response.status_code == 409:
            print(f"└─ Component already exists")
        elif response.status_code == 400:
            # Handle specific 400 errors
            try:
                error_response = response.json()
                error_message = error_response.get('error', 'Unknown error')
                
                if 'Integration not found' in error_message:
                    print(f"└─ ⚠️  Warning: Ticketing integration not found, retrying without ticketing...")
                    # Remove ticketing from payload and retry
                    payload_without_ticketing = payload.copy()
                    payload_without_ticketing.pop('ticketing', None)
                    
                    print(f"└─ Retrying component creation without ticketing integration...")
                    try:
                        retry_response = requests.post(api_url, headers=headers, json=payload_without_ticketing)
                        retry_response.raise_for_status()
                        print(f"└─ ✅ Component created successfully (without ticketing)")
                        
                        # Track successful component creation (retry) for main script reporting
                        if component_tracking_callback:
                            component_tracking_callback('components', 'create_component_retry', f"{applicationName} -> {component['ComponentName']}", True)
                        
                        time.sleep(2)
                    except requests.exceptions.RequestException as retry_e:
                        if retry_response.status_code == 409:
                            print(f"└─ Component already exists")
                        else:
                            error_msg = f"Failed to create component even without ticketing: {str(retry_e)}"
                            error_details = f'Response: {getattr(retry_response, "content", "No response content")}\nPayload: {json.dumps(payload_without_ticketing)}'
                            log_error(
                                'Component Creation (Retry)',
                                f"{applicationName} -> {component['ComponentName']}",
                                'N/A',
                                error_msg,
                                error_details
                            )
                            print(f"└─ Error: {error_msg}")
                            
                            # Track failed component creation for main script reporting
                            if component_tracking_callback:
                                component_tracking_callback('components', 'create_component', f"{applicationName} -> {component['ComponentName']}", False, error_msg)
                            
                            return
                else:
                    error_msg = f"Failed to create component: {error_message}"
                    error_details = f'Response: {response.content.decode()}\nPayload: {json.dumps(payload)}'
                    log_error(
                        'Component Creation',
                        f"{applicationName} -> {component['ComponentName']}",
                        'N/A',
                        error_msg,
                        error_details
                    )
                    print(f"└─ Error: {error_msg}")
                    
                    # Track failed component creation for main script reporting
                    if component_tracking_callback:
                        component_tracking_callback('components', 'create_component', f"{applicationName} -> {component['ComponentName']}", False, error_msg)
                    
                    return
            except (ValueError, KeyError):
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
                
                # Track failed component creation for main script reporting
                if component_tracking_callback:
                    component_tracking_callback('components', 'create_component', f"{applicationName} -> {component['ComponentName']}", False, error_msg)
                
                return
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
            
            # Track failed component creation for main script reporting
            if component_tracking_callback:
                component_tracking_callback('components', 'create_component', f"{applicationName} -> {component['ComponentName']}", False, error_msg)
            
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


def update_application(application, existing_apps_envs, existing_components, headers2):
    global headers
    if not headers:
        headers = headers2
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

def update_component(application, component, existing_component, headers2):
    global headers
    if not headers:
        headers = headers2
    print(f"\n[Component Update]")
    print(f"└─ Application: {application['AppName']}")
    print(f"└─ Component: {component['ComponentName']}")
    print(f"└─ Existing Component ID: {existing_component.get('id')}")
    print(f"└─ Component Data: {component}")

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

    # Build tags for the update
    tags = []
    
    # Add team tags
    for team in component.get('TeamNames', []):
        if team:  # Only add non-empty team names
            tags.append({"key": "pteam", "value": team})
    
    # Add domain and subdomain tags only if they are not None or empty
    if component.get('Domain'):
        tags.append({"key": "domain", "value": component['Domain']})
    if component.get('SubDomain'):
        tags.append({"key": "subdomain", "value": component['SubDomain']})
    
    # Add tags from the Tag_label and Tags_label fields in YAML configuration
    if component.get('Tag_label'):
        tag_label = component.get('Tag_label')
        if isinstance(tag_label, str):
            # Handle single string tag
            tags.append(process_tag_string(tag_label))
        elif isinstance(tag_label, list):
            for tag in tag_label:
                if isinstance(tag, str):
                    tags.append(process_tag_string(tag))
                elif isinstance(tag, dict):
                    if 'key' in tag and 'value' in tag:
                        tags.append({"key": tag['key'], "value": tag['value']})
                    elif 'value' in tag:
                        tags.append({"value": tag['value']})
    
    if component.get('Tags_label'):
        for tag in component.get('Tags_label'):
            if isinstance(tag, str):
                # Handle string tags using helper function
                tags.append(process_tag_string(tag))
            elif isinstance(tag, dict):
                # Handle dict tags that already have key/value structure
                if 'key' in tag and 'value' in tag:
                    tags.append({"key": tag['key'], "value": tag['value']})
                elif 'value' in tag:
                    tags.append({"value": tag['value']})

    payload = {
        "name": component['ComponentName'],
        "criticality": calculate_criticality(component.get('Tier', 5)),  # Calculate from Tier field
        "tags": tags
    }
    
    # Always show final tag summary for troubleshooting (UPDATE)
    print(f"└─ FINAL TAG SUMMARY for component UPDATE {component['ComponentName']}:")
    print(f"└─ Total tags to be sent: {len(tags)}")
    for i, tag in enumerate(tags):
        if 'key' in tag and 'value' in tag:
            print(f"   {i+1:2d}. {tag['key']}: {tag['value']}")
        elif 'value' in tag:
            print(f"   {i+1:2d}. {tag['value']} (value only)")
    
    if len(tags) == 0:
        print(f"└─ ⚠️  WARNING: No tags will be sent with this component update!")

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
            
            # Track successful component update
            if component_tracking_callback:
                component_tracking_callback('components', 'update_component', f"{application['AppName']} -> {component['ComponentName']}", True, None)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to update component: {str(e)}"
            
            # Check if this is an "Integration not found" error and retry without ticketing
            if response.status_code == 400 and "Integration not found" in str(response.content):
                print(f"└─ Integration not found error detected, retrying without ticketing...")
                
                # Create a copy of payload without ticketing
                retry_payload = payload.copy()
                if 'ticketing' in retry_payload:
                    del retry_payload['ticketing']
                    print(f"└─ Removed ticketing integration from payload")
                    
                try:
                    print(f"└─ Sending retry update payload (without ticketing):")
                    print(f"   └─ {json.dumps(retry_payload, indent=2)}")
                    retry_response = requests.patch(api_url, headers=headers, json=retry_payload)
                    retry_response.raise_for_status()
                    print(f"└─ Component updated successfully without ticketing integration")
                    
                    # Track successful component update retry
                    if component_tracking_callback:
                        component_tracking_callback('components', 'update_component_retry', f"{application['AppName']} -> {component['ComponentName']}", True, 'Integration not found, retried successfully without ticketing')
                        
                except requests.exceptions.RequestException as retry_e:
                    retry_error_msg = f"Failed to update component even without ticketing: {str(retry_e)}"
                    retry_error_details = f'Original error: {error_msg}\nRetry error: {retry_error_msg}\nOriginal payload: {json.dumps(payload)}\nRetry payload: {json.dumps(retry_payload)}\nRetry response: {getattr(retry_response, "content", "No response content")}'
                    
                    log_error(
                        'Component Update Retry Failed',
                        f"{application['AppName']} -> {component['ComponentName']}",
                        'N/A',
                        retry_error_msg,
                        retry_error_details
                    )
                    print(f"└─ Error: {retry_error_msg}")
                    if DEBUG:
                        print(f"└─ Retry response content: {getattr(retry_response, 'content', 'No response content')}")
                        
                    # Track failed component update retry
                    if component_tracking_callback:
                        component_tracking_callback('components', 'update_component_retry', f"{application['AppName']} -> {component['ComponentName']}", False, retry_error_msg)
                        
            else:
                # For other types of errors, log normally
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
                    
                # Track failed component update
                if component_tracking_callback:
                    component_tracking_callback('components', 'update_component', f"{application['AppName']} -> {component['ComponentName']}", False, error_msg)
    
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

def update_application_teams(existing_app, application, headers2):
    global headers
    if not headers:
        headers = headers2
    for team in filter(lambda tag: tag.get('key') == 'pteam', existing_app.get('tags')):
        if team.get('value') not in application.get('TeamNames'):
            remove_tag_from_application(team.get('id'), team.get('key'), team.get('value'), existing_app.get('id'), headers)

    for new_team in application.get('TeamNames'):
        if not next(filter(lambda team: team.get('key') == 'pteam' and team['value'] == new_team, existing_app.get('tags')), None):
            add_tag_to_application('pteam', new_team, existing_app.get('id'), headers)

def update_application_crit_owner(application, existing_application, headers2):
    global headers
    if not headers:
        headers = headers2
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

def create_component_rules(applicationName, component, headers2):
    global headers
    if not headers:
        headers = headers2
    # Helper function to validate value
    def is_valid_value(value):
        if value is None:
            return False
        if isinstance(value, str) and (not value.strip() or value.lower() == 'null'):
            return False
        return True

    # Note: Tag validation is now handled in create_custom_component and update_component

    # SearchName rule
    if component.get('SearchName') and is_valid_value(component.get('SearchName')):
        create_component_rule(applicationName, component['ComponentName'], 'keyLike', component['SearchName'], f"Rule for keyLike for {component['ComponentName']}", headers)

    # Tags rule - create asset matching rules for Tags field
    if component.get('Tags') and is_valid_value(component.get('Tags')):
        create_component_rule(applicationName, component['ComponentName'], 'tags', component['Tags'], f"Rule for tags for {component['ComponentName']}", headers)

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

    # MultiCondition rules - process after all other rules including tags
    if component.get('MultiConditionRule') and is_valid_value(component.get('MultiConditionRule')):
        create_multicondition_component_rules(applicationName, component['ComponentName'], [component.get('MultiConditionRule')], headers)    

    if component.get('MultiConditionRules') and is_valid_value(component.get('MultiConditionRules')):
        create_multicondition_component_rules(applicationName, component['ComponentName'], component.get('MultiConditionRules'), headers)
    
    # Handle MULTI_MultiConditionRules (the main variant used in YAML)
    if component.get('MULTI_MultiConditionRules') and is_valid_value(component.get('MULTI_MultiConditionRules')):
        create_multicondition_component_rules(applicationName, component['ComponentName'], component.get('MULTI_MultiConditionRules'), headers)

def create_multicondition_component_rules(applicationName, componentName, multiconditionRules, headers2):
    global headers
    if not headers:
        headers = headers2
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
                    
                    # Extract last 2 parts of each repository path
                    shortened_repository_names = []
                    for repo_name in repository_names:
                        if repo_name and isinstance(repo_name, str):
                            shortened_repo = extract_last_two_path_parts(repo_name)
                            shortened_repository_names.append(shortened_repo)
                    
                    rule['filter']['repository'] = shortened_repository_names
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
                # Handle Tag_rule and Tags_rule fields for asset matching
                if multicondition.get('Tag_rule'):
                    tag_rule_value = multicondition.get('Tag_rule')
                    if isinstance(tag_rule_value, str):
                        # Single tag rule
                        if ':' in tag_rule_value:
                            tag_parts = tag_rule_value.split(':', 1)
                            key = tag_parts[0].strip()
                            value = tag_parts[1].strip()
                            rule['filter']['tags'] = [{"key": key, "value": value}]
                        else:
                            rule['filter']['tags'] = [{"value": tag_rule_value}]
                    elif isinstance(tag_rule_value, list):
                        # Multiple tag rules
                        rule['filter']['tags'] = []
                        for tag in tag_rule_value:
                            if ':' in tag:
                                tag_parts = tag.split(':', 1)
                                key = tag_parts[0].strip()
                                value = tag_parts[1].strip()
                                rule['filter']['tags'].append({"key": key, "value": value})
                            else:
                                rule['filter']['tags'].append({"value": tag})
                if multicondition.get('Tags_rule'):
                    rule['filter']['tags'] = []
                    for tag in multicondition.get('Tags_rule'):
                        if ':' in tag:
                            tag_parts = tag.split(':', 1)
                            key = tag_parts[0].strip()
                            value = tag_parts[1].strip()
                            rule['filter']['tags'].append({"key": key, "value": value})
                        else:
                            rule['filter']['tags'].append({"value": tag})

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

def create_multicondition_service_rules(environmentName, serviceName, multiconditionRules, headers2):
    global headers
    if not headers:
        headers = headers2
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
            
            # Extract last 2 parts of each repository path and validate
            valid_repos = []
            for repo in repository_names:
                if is_valid_value(repo):
                    shortened_repo = extract_last_two_path_parts(repo)
                    valid_repos.append(shortened_repo)
            
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
                
        # Handle Tag_rule and Tags_rule fields for asset matching
        if multicondition.get('Tag_rule') and is_valid_value(multicondition.get('Tag_rule')):
            tag_rule_value = multicondition.get('Tag_rule')
            if isinstance(tag_rule_value, str):
                # Single tag rule
                if ':' in tag_rule_value:
                    tag_parts = tag_rule_value.split(':', 1)
                    key = tag_parts[0].strip()
                    value = tag_parts[1].strip()
                    rule['filter']['tags'] = [{"key": key, "value": value}]
                    filter_details.append(f"TAG_RULE:{key}={value}")
                else:
                    rule['filter']['tags'] = [{"value": tag_rule_value}]
                    filter_details.append(f"TAG_RULE:{tag_rule_value}")
            elif isinstance(tag_rule_value, list):
                # Multiple tag rules
                rule['filter']['tags'] = []
                tag_rule_details = []
                for tag in tag_rule_value:
                    if ':' in tag:
                        tag_parts = tag.split(':', 1)
                        key = tag_parts[0].strip()
                        value = tag_parts[1].strip()
                        rule['filter']['tags'].append({"key": key, "value": value})
                        tag_rule_details.append(f"{key}={value}")
                    else:
                        rule['filter']['tags'].append({"value": tag})
                        tag_rule_details.append(tag)
                filter_details.append(f"TAG_RULE:{','.join(tag_rule_details)}")
                
        if multicondition.get('Tags_rule') and is_valid_value(multicondition.get('Tags_rule')):
            rule['filter']['tags'] = []
            tag_rule_details = []
            for tag in multicondition.get('Tags_rule'):
                if ':' in tag:
                    tag_parts = tag.split(':', 1)
                    key = tag_parts[0].strip()
                    value = tag_parts[1].strip()
                    rule['filter']['tags'].append({"key": key, "value": value})
                    tag_rule_details.append(f"{key}={value}")
                else:
                    rule['filter']['tags'].append({"value": tag})
                    tag_rule_details.append(tag)
            filter_details.append(f"TAGS_RULE:{','.join(tag_rule_details)}")
                
        if multicondition.get('AssetType') and is_valid_value(multicondition.get('AssetType')):
            rule['filter']['assetType'] = str(multicondition.get('AssetType'))
            filter_details.append(f"ASSET:{multicondition.get('AssetType')}")
        
        provider_account_ids = []
        if multicondition.get('ProviderAccountId'):
            for providerAccountId in multicondition.get('ProviderAccountId', []):
                if is_valid_value(providerAccountId):
                    provider_account_ids.append(str(providerAccountId))
            rule['filter']['providerAccountId'] = provider_account_ids
            filter_details.append(f"PROVIDER_ACCOUNT_IDS:{provider_account_ids}")

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

def extract_last_two_path_parts(repo_path):
    """
    Extract the last 2 parts of a repository path.
    
    Args:
        repo_path (str): Full repository path like "gitlab.com/q2e/development/helix/io-code-review-assistant"
        
    Returns:
        str: Last 2 parts like "helix/io-code-review-assistant"
    """
    if not repo_path or not isinstance(repo_path, str):
        return repo_path
    
    # Split by '/' and get the last 2 parts
    parts = repo_path.strip().split('/')
    if len(parts) >= 2:
        return '/'.join(parts[-2:])
    else:
        return repo_path  # Return original if less than 2 parts

def get_repositories_from_component(component):
    """
    Get repository names from a component, handling all edge cases.
    Repository paths are shortened to show only the last 2 parts.
    
    Args:
        component (dict): The component dictionary that may contain repository information
        
    Returns:
        list: A list of valid repository names (shortened to last 2 parts), or an empty list if none are found
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
        
        # Extract last 2 parts of the path
        shortened_repo = extract_last_two_path_parts(repository)
        
        if len(shortened_repo) >= 3:  # Only return if length requirement is met
            if DEBUG:
                print(f"Valid repository found: {repository} -> {shortened_repo}")
            return [shortened_repo]
        if DEBUG:
            print(f"Repository too short: {shortened_repo}")
        return []
    
    # Handle list case
    if isinstance(repository, list):
        if DEBUG:
            print("Processing repository list")
        valid_repos = []
        for repo in repository:
            if repo and isinstance(repo, str):
                repo = repo.strip()
                if repo and repo.lower() != 'null':
                    # Extract last 2 parts of the path
                    shortened_repo = extract_last_two_path_parts(repo)
                    
                    if len(shortened_repo) >= 3:
                        if DEBUG:
                            print(f"Valid repository found in list: {repo} -> {shortened_repo}")
                        valid_repos.append(shortened_repo)
                    elif DEBUG:
                        print(f"Repository too short in list: {repo} -> {shortened_repo}")
                elif DEBUG:
                    print(f"Invalid repository in list: {repo}")
        return valid_repos
    
    # If we get here, repository is an unexpected type
    if DEBUG:
        print(f"Warning: Unexpected repository type: {type(repository)}")
    return []

# CreateRepositories Function
def create_repositories(repos, access_token2):
    global access_token
    if not access_token:
        access_token = access_token2
    # Iterate over the list of repositories and call the create_repo function
    for repo in repos:
        create_repo(repo, access_token)

# CreateRepo Function
def create_repo(repo, access_token2):
    global access_token
    if not access_token:
        access_token = access_token2
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}
    
    # Calculate criticality (assuming a function `calculate_criticality` exists)
    criticality = calculate_criticality(repo['Tier'])
    
    # Extract last 2 parts of repository path for cleaner names
    original_repo_name = repo['RepositoryName']
    shortened_repo_name = extract_last_two_path_parts(original_repo_name)
    
    # Create the payload, the function assume 1 repo per component with the component name being the repository this can be edited
    payload = {
        "repository": f"{shortened_repo_name}",
        "applicationSelector": {
            "name": repo['Subdomain'],
            "caseSensitive": False
        },
        "component": {
            "name": shortened_repo_name,
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
        print(f" + {shortened_repo_name} added (original: {original_repo_name}).")
    
    except requests.exceptions.RequestException as e:
        if response.status_code == 409:
            print(f" > Repo {shortened_repo_name} already exists (original: {original_repo_name})")
        else:
            print(f"Error: {e}")
            exit(1)

# AddCloudAssetRules Function
def add_cloud_asset_rules(repos, access_token2):
    global access_token
    if not access_token:
        access_token = access_token2
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}
    
    # Loop through each repository and modify domain if needed
    for repo in repos:
        # Extract last 2 parts of repository path for cleaner search terms
        shortened_repo_name = extract_last_two_path_parts(repo['RepositoryName'])
        search_term = f"*{shortened_repo_name}(*"
        cloud_asset_rule(repo['Subdomain'], search_term, "Production", access_token)

    # Adding rules for PowerPlatform with different environments
    #cloud_asset_rule("PowerPlatform", "powerplatform_prod", "Production", access_token)
    #cloud_asset_rule("PowerPlatform", "powerplatform_sim", "Sim", access_token)
    #cloud_asset_rule("PowerPlatform", "powerplatform_staging", "Staging", access_token)
    #cloud_asset_rule("PowerPlatform", "powerplatform_dev", "Development", access_token)

# CloudAssetRule Function
def cloud_asset_rule(name, search_term, environment_name, access_token2):
    global access_token
    if not access_token:
        access_token = access_token2
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

def create_teams(teams, pteams, access_token2):
    """
    This function iterates through a list of teams and adds new teams if they are not already present in `pteams`.

    Args:
    - teams: List of team objects to be added.
    - pteams: List of existing team objects to check if a team already exists.
    - access_token: Access token for API authentication.
    """
    global access_token
    if not access_token:
        access_token = access_token2
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}
    new_pteams = []
    
    # Iterate over the list of teams to be added
    for team in teams:
        found = False
        team_name = team.get('TeamName', '').strip()
        
        if not team_name:
            if DEBUG:
                print(f"└─ Skipping team with empty name: {team}")
            continue

        # Check if the team already exists in the existing pteams
        for pteam in pteams:
            if pteam['name'] == team_name:
                found = True
                if DEBUG:
                    print(f"└─ Team {team_name} already exists, skipping creation")
                break
        
        # If the team is not found and has a valid name, proceed to add it
        if not found:
            print("[Team]")
            print(f"└─ Creating: {team_name}")
            
            # Prepare the payload for creating the team
            payload = {
                "name": team_name,
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
                print(f"└─ Team created successfully: {team_name}")
            except requests.exceptions.RequestException as e:
                if response.status_code == 409:
                    print(f"└─ Team {team_name} already exists (409 Conflict)")
                    # Continue processing other teams instead of exiting
                    continue
                else:
                    error_msg = f"Failed to create team: {str(e)}"
                    error_details = f"Response: {getattr(response, 'content', 'No response content')}\nPayload: {json.dumps(payload)}"
                    log_error(
                        'Team Creation',
                        team_name,
                        'N/A',
                        error_msg,
                        error_details
                    )
                    print(f"Error: {error_msg}")
                    if DEBUG:
                        print(f"└─ Response content: {response.content}")
                    # Continue processing other teams instead of exiting completely
                    continue
    return new_pteams


def create_teams_from_pteams(applications, environments, pteams, access_token2):
    global access_token
    if not access_token:
        access_token = access_token2
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


def populate_phoenix_teams(access_token2):
    """
    This function retrieves the list of Phoenix teams by making a GET request to the /v1/teams endpoint.

    Args:
    - access_token: Access token for API authentication.

    Returns:
    - List of teams if the request is successful, otherwise exits with an error message.
    """
    global access_token
    if not access_token:
        access_token = access_token2
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
def create_team_rules(teams, pteams, access_token2):
    """
    This function iterates through a list of teams and creates team rules for teams
    that do not already exist in `pteams`.

    Args:
    - teams: List of team objects.
    - pteams: List of pre-existing teams to check if a team already exists.
    - access_token: Access token for API authentication.
    """   
    global access_token
    if not access_token:
        access_token = access_token2 
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

def create_team_rule(tag_name, tag_value, team_id, access_token2):
    """
    This function creates a team rule by adding tags to a team.

    Args:
    - tag_name: Name of the tag (e.g., "pteam").
    - tag_value: Value of the tag (e.g., the team name).
    - team_id: ID of the team.
    - access_token: API authentication token.
    """
    global access_token
    if not access_token:
        access_token = access_token2
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

def check_and_create_missing_users(teams, all_team_access, hive_staff, access_token2):
    """
        This function checks whether some user from teams or hives is missing and creates them.

        Args:
        - teams: List of target teams to check users for
        - all_team_access: list of all team access users
        - hive_staff: list of hives. Only Lead and Product users will be managed in this function
    """
    global access_token
    if not access_token:
        access_token = access_token2
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
def assign_users_to_team(p_teams, new_pteams, teams, all_team_access, hive_staff, access_token2):
    """
    This function assigns users to teams by checking if users are already part of the team, and adds or removes them accordingly.
    
    Args:
    - p_teams: List of Phoenix teams.
    - teams: List of target teams to manage.
    - all_team_access: List of users with full team access.
    - hive_staff: List of Hive team staff.
    - access_token: API authentication token.
    """
    global access_token
    if not access_token:
        access_token = access_token2
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
def api_call_assign_users_to_team(team_id, email, access_token2):
    """
    Assigns a user to a team by making a PUT request to the API.

    Args:
    - team_id: The ID of the team.
    - email: The email address of the user to be added to the team.
    - access_token: API authentication token.
    """
    global access_token
    if not access_token:
        access_token = access_token2
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
def delete_team_member(email, team_id, access_token2):
    """
    Removes a user from a team by making a DELETE request to the API.

    Args:
    - email: The email address of the user to be removed from the team.
    - team_id: The ID of the team.
    - access_token: API authentication token.
    """
    global access_token
    if not access_token:
        access_token = access_token2
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
def get_phoenix_components(access_token2):
    global access_token
    if not access_token:
        access_token = access_token2
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}
    return get_phoenix_components(headers)


@dispatch(dict)
def get_phoenix_components(headers2):
    """
    Fetches all Phoenix components with proper pagination handling.
    
    Args:
        headers: Request headers containing authorization
        
    Returns:
        list: Complete list of all components across all pages
    """
    global headers
    if not headers:
        headers = headers2
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


def get_phoenix_components_in_environment(env_id, access_token2):
    global access_token
    if not access_token:
        access_token = access_token2
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


def verify_service_exists(env_name, env_id, service_name, headers2, max_retries=5):
    """
    Verify if a service exists in an environment with thorough checking and pagination.
    """
    global headers
    if not headers:
        headers = headers2
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
def get_phoenix_team_members(team_id, access_token2):
    global access_token
    if not access_token:
        access_token = access_token2
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
        
        # Extract last 2 parts of repository path for comparison
        shortened_repo_name = extract_last_two_path_parts(repo['RepositoryName'])
        
        # Check and remove old tags in phoenix_components
        for component in phoenix_components:
            if shortened_repo_name == component['name']:
                print(f"Repo: {shortened_repo_name} (original: {repo['RepositoryName']})")
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


def remove_tag(tag_id, tag_key, tag_value,access_token2):
    """
    Removes the specified tag by making a DELETE or PATCH API call.

    Args:
    - tag_id: The ID of the tag to remove.
    - tag_key: The key of the tag.
    - tag_value: The value of the tag.
    """
    global access_token
    if not access_token:
        access_token = access_token2
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


def remove_tag_from_application(tag_id, tag_key, tag_value, application_id, headers2):
    """
    Removes the specified tag by making a DELETE or PATCH API call.

    Args:
    - tag_id: The ID of the tag to remove.
    - tag_key: The key of the tag.
    - tag_value: The value of the tag.
    - application_id: The ID of the application having the tag
    """
    global headers
    if not headers:
        headers = headers2
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


def remove_tag_from_component(tag_id, tag_key, tag_value, component_id, headers2):
    """
    Removes the specified tag by making a PATCH API call.

    Args:
    - tag_id: The ID of the tag to remove.
    - tag_key: The key of the tag.
    - tag_value: The value of the tag.
    - component_id: The ID of the component having the tag
    """
    global headers
    if not headers:
        headers = headers2
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


def add_tag_to_application(tag_key, tag_value, application_id, headers2):
    """
    Add the specified tag by making a PUT API call.

    Args:
    - tag_key: The key of the tag.
    - tag_value: The value of the tag.
    - application_id: The application to tag
    """
    global headers
    if not headers:
        headers = headers2
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
        error_msg = f"Error adding tag: {e}"
        print(f"   └─ ❌ {error_msg}")
        
        # Log detailed error information
        tag_description = f"{tag_key}:{tag_value}"
        log_error(
            'Application Tag Addition',
            f"App ID: {application_id} -> Tag: {tag_description}",
            'N/A',
            error_msg,
            f'API URL: {api_url}\nPayload: {json.dumps(payload)}\nResponse: {getattr(response, "content", "No response content")}'
        )
        
        if hasattr(response, 'content'):
            print(f"   └─ API Response: {response.content.decode()}")
        if hasattr(response, 'status_code'):
            print(f"   └─ Status Code: {response.status_code}")
    except Exception as e:
        error_msg = f"Unexpected error adding tag: {str(e)}"
        print(f"   └─ ❌ Unexpected error: {error_msg}")
        
        tag_description = f"{tag_key}:{tag_value}"
        log_error(
            'Application Tag Addition (Unexpected)',
            f"App ID: {application_id} -> Tag: {tag_description}",
            'N/A',
            error_msg,
            f'Exception type: {type(e).__name__}'
        )


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
def populate_applications_and_environments(headers2):
    global headers
    if not headers:
        headers = headers2
    components = []

    try:
        print("Getting list of Phoenix Applications and Environments")
        api_url = construct_api_url("/v1/applications")
        
        # Debug: Print the full request details
        if DEBUG:
            print(f"📡 API Request URL: {api_url}")
            print(f"📡 Request Headers: {headers}")
        
        response = requests.get(api_url, headers=headers)
        
        # Enhanced error handling for API compatibility issues
        if response.status_code != 200:
            print(f"⚠️  API returned status code: {response.status_code}")
            print(f"⚠️  Response content: {response.content}")
            
            # Check if this is the ENVIRONMENT_CLOUD enum error
            if b'ENVIRONMENT_CLOUD' in response.content:
                print("🔍 Detected ENVIRONMENT_CLOUD enum compatibility issue")
                print("💡 This appears to be an API version compatibility problem")
                print("🔄 Attempting alternative API approach...")
                
                # Try with different parameters or endpoint variations
                return handle_enum_compatibility_issue(headers)
        
        response.raise_for_status()

        data = response.json()
        components = data.get('content', [])
        total_pages = data.get('totalPages', 1)

        for i in range(1, total_pages):
            api_url = construct_api_url(f"/v1/applications?pageNumber={i}")
            response = requests.get(api_url, headers=headers)
            
            if response.status_code != 200:
                print(f"⚠️  Pagination request failed with status: {response.status_code}")
                break
                
            components += response.json().get('content', [])
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to fetch apps/envs. Response: {response.content if hasattr(response, 'content') else 'N/A'}"
        
        # Enhanced error reporting for debugging
        print(f"💥 Request Exception Details:")
        print(f"   └─ Exception type: {type(e).__name__}")
        print(f"   └─ Exception message: {str(e)}")
        if hasattr(response, 'status_code'):
            print(f"   └─ Response status: {response.status_code}")
        if hasattr(response, 'content'):
            print(f"   └─ Response content: {response.content}")
            
        log_error(
            'Fetching all apps/envs',
            'None',
            'N/A',
            error_msg,
            f'Response status: {response.status_code if hasattr(response, "status_code") else "Unknown"}\nException: {str(e)}'
        )
        print(f"└─ Error: {error_msg}")
        
        # Instead of exiting, try fallback approach
        print("🔄 Attempting fallback approach for applications/environments...")
        return handle_enum_compatibility_issue(headers)

    return components


def handle_enum_compatibility_issue(headers):
    """
    Fallback handler for API compatibility issues with enum values
    Returns minimal data structure to allow script to continue
    """
    print("🛠️  Handling API compatibility issue...")
    print("📝 This might be due to:")
    print("   • API version mismatch between client and server")
    print("   • Server-side enum definition changes")
    print("   • Backend configuration issues")
    
    # Return empty list to allow script to continue
    # This will mean no existing apps/environments are found,
    # so new ones will be created if configured
    print("⚠️  Returning empty applications/environments list")
    print("💡 Script will proceed assuming no existing apps/environments")
    
    return []

@dispatch(str, str, dict, int, dict)
def add_service(applicationSelectorName, env_id, service, tier, headers2):
    global headers
    if not headers:
        headers = headers2
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
def add_service(applicationSelectorName, env_id, service, tier, team, headers2):
    global headers
    if not headers:
        headers = headers2
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


def update_service(service, existing_service_id, headers2):
    global headers
    if not headers:
        headers = headers2
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


def add_thirdparty_services(phoenix_components, application_environments, subdomain_owners, headers2):
    global headers
    if not headers:
        headers = headers2
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


def get_phoenix_team_members(team_id, headers2):
    global headers
    if not headers:
        headers = headers2
    try:
        api_url = construct_api_url(f"/v1/teams/{team_id}/users")
        response = requests.get(api_url, headers=headers)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return []


def create_deployments(applications, environments, phoenix_apps_envs, headers2):
    global headers
    if not headers:
        headers = headers2
    application_services = []
    # Track all available apps and services for validation
    available_apps = {app['name']: app['id'] for app in phoenix_apps_envs if app.get('type') == "APPLICATION"}
    available_services = {}
    
    print(f"\n[Deployment Operation]")
    print(f"└─ Found {len(applications)} applications to process")
    print(f"└─ Found {len(environments)} environments to process")
    print(f"└─ Found {len(phoenix_apps_envs)} Phoenix apps/envs")
    
    # Debug: Show available applications
    print(f"└─ Available applications in Phoenix:")
    for app_name, app_id in available_apps.items():
        print(f"   └─ {app_name} (ID: {app_id})")
    
    # Debug: Show applications to process
    print(f"└─ Applications from config to process:")
    for app in applications:
        app_name = app.get('AppName', 'Unknown')
        deployment_set = app.get('Deployment_set', 'None')
        print(f"   └─ {app_name} (Deployment_set: {deployment_set})")
    
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


def create_autolink_deployments(applications, environments, headers2):
    global headers
    if not headers:
        headers = headers2
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


def get_assets(applicationEnvironmentId, type, headers2, include_tags=False):
    global headers
    if not headers:
        headers = headers2
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
        if include_tags:
            # Return full asset objects with tags for tag-based grouping
            assets = data.get('content', [])
        else:
            # Return just asset names for backward compatibility
            assets = [asset['name'] for asset in data.get('content', [])]
            
        total_pages = data.get('totalPages', 1)
        for i in range(1, total_pages):
            api_url = construct_api_url(f"/v1/assets?pageNumber={i}&pageSize=100")
            response = requests.post(api_url, headers=headers, json = asset_request)
            page_data = response.json()
            if include_tags:
                new_assets = page_data.get('content', [])
            else:
                new_assets = [asset['name'] for asset in page_data.get('content', [])]
            assets.extend(new_assets)

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


def get_asset_types_for_category(category):
    """
    Map user-friendly asset categories to Phoenix asset types.
    
    Args:
        category (str): User selected category ('all', 'cloud', 'code', 'infrastructure', 'web')
    
    Returns:
        list: List of Phoenix asset types to process
    """
    asset_type_mapping = {
        'all': ['REPOSITORY', 'SOURCE_CODE', 'BUILD', 'WEBSITE_API', 'CONTAINER', 'INFRA', 'CLOUD', 'WEB', 'FOSS', 'SAST'],
        'cloud': ['CLOUD', 'CONTAINER'],  # Cloud resources and containers
        'code': ['REPOSITORY', 'SOURCE_CODE', 'BUILD', 'FOSS', 'SAST'],  # Code-related assets
        'infrastructure': ['INFRA'],  # Infrastructure components
        'web': ['WEB', 'WEBSITE_API']  # Web assets and APIs
    }
    
    return asset_type_mapping.get(category.lower(), ['CONTAINER', 'CLOUD'])  # Default to original types


def get_asset_assignment_strategy(asset_type):
    """
    Determine how assets should be assigned based on their type.
    
    Args:
        asset_type (str): Phoenix asset type
        
    Returns:
        dict: Assignment strategy with target type and details
    """
    # CODE, WEB, BUILD assets go to APPLICATION COMPONENTS
    application_component_types = ['REPOSITORY', 'SOURCE_CODE', 'BUILD', 'WEB', 'WEBSITE_API', 'FOSS', 'SAST']
    
    # CLOUD, CONTAINER assets go to ENVIRONMENT SERVICES
    cloud_service_types = ['CLOUD', 'CONTAINER']
    
    # INFRA assets go to ENVIRONMENT SERVICES  
    infra_service_types = ['INFRA']
    
    if asset_type in application_component_types:
        return {
            'target': 'component',
            'description': f'{asset_type} assets → Application Components',
            'service_type': None
        }
    elif asset_type in cloud_service_types:
        return {
            'target': 'service',
            'description': f'{asset_type} assets → Environment Services (Cloud type)',
            'service_type': 'Cloud'
        }
    elif asset_type in infra_service_types:
        return {
            'target': 'service', 
            'description': f'{asset_type} assets → Environment Services (Infrastructure type)',
            'service_type': 'Infrastructure'
        }
    else:
        # Default fallback to component for unknown types
        return {
            'target': 'component',
            'description': f'{asset_type} assets → Application Components (default)',
            'service_type': None
        }


def is_environment_compatible_with_asset_type(env_subtype, asset_type, assignment_strategy):
    """
    Check if an environment type is compatible with an asset type assignment.
    
    Args:
        env_subtype (str): Environment subType (e.g., 'cloud', 'infrastructure', 'application')
        asset_type (str): Phoenix asset type
        assignment_strategy (dict): Assignment strategy from get_asset_assignment_strategy
        
    Returns:
        bool: True if compatible, False otherwise
    """
    # For application components, any environment is compatible
    if assignment_strategy['target'] == 'component':
        return True
    
    # For services, match environment subtype with service type
    if assignment_strategy['target'] == 'service':
        if assignment_strategy['service_type'] == 'Cloud':
            # Cloud and container assets should go to cloud-type environments
            return env_subtype.lower() in ['cloud', 'aws', 'azure', 'gcp', 'container']
        elif assignment_strategy['service_type'] == 'Infrastructure':
            # Infrastructure assets should go to infrastructure-type environments
            return env_subtype.lower() in ['infrastructure', 'infra', 'on-premise', 'datacenter']
    
    # Default to compatible for unknown cases
    return True


def show_creation_plan_and_confirm(creation_plan, silent_mode=False):
    """
    Show what will be created and get user confirmation.
    
    Args:
        creation_plan (dict): Dictionary containing planned creations
        silent_mode (bool): If True, auto-accept without prompting
        
    Returns:
        bool: True if user confirms, False otherwise
    """
    print("\n" + "="*80)
    print("🔍 CREATION PLAN PREVIEW")
    print("="*80)
    
    total_items = 0
    
    # Show environments to be created
    if creation_plan['environments']:
        print(f"\n🌍 ENVIRONMENTS TO CREATE ({len(creation_plan['environments'])})")
        for env_name, env_data in creation_plan['environments'].items():
            print(f"   📁 {env_name}")
            print(f"      Type: {env_data.get('type', 'Unknown')}")
            print(f"      Team: {env_data.get('team', 'Unknown')}")
            total_items += 1
    
    # Show services to be created
    if creation_plan['services']:
        print(f"\n🔧 SERVICES TO CREATE ({len(creation_plan['services'])})")
        for service_key, service_data in creation_plan['services'].items():
            print(f"   ⚙️  {service_data['name']} (in {service_data['environment']})")
            print(f"      Type: {service_data.get('service_type', 'Unknown')}")
            print(f"      Assets: {service_data.get('asset_count', 0)}")
            total_items += 1
    
    # Show applications to be created
    if creation_plan['applications']:
        print(f"\n📦 APPLICATIONS TO CREATE ({len(creation_plan['applications'])})")
        for app_name, app_data in creation_plan['applications'].items():
            print(f"   📱 {app_name}")
            print(f"      Team: {app_data.get('team', 'Unknown')}")
            total_items += 1
    
    # Show components to be created
    if creation_plan['components']:
        print(f"\n🧩 COMPONENTS TO CREATE ({len(creation_plan['components'])})")
        for comp_key, comp_data in creation_plan['components'].items():
            print(f"   🔗 {comp_data['name']} (in {comp_data['application']})")
            print(f"      Assets: {comp_data.get('asset_count', 0)}")
            total_items += 1
    
    print(f"\n📊 TOTAL ITEMS TO CREATE: {total_items}")
    print("="*80)
    
    if silent_mode:
        print("🔇 SILENT MODE: Auto-accepting creation plan")
        return True
    
    if total_items == 0:
        print("ℹ️  No items to create.")
        return False
    
    while True:
        try:
            response = input(f"\n❓ Do you want to proceed with creating these {total_items} items? (Y/yes/N/no): ").strip().lower()
            if response in ['y', 'yes']:
                print("✅ Creation confirmed by user")
                return True
            elif response in ['n', 'no']:
                print("❌ Creation cancelled by user")
                return False
            else:
                print("❌ Please enter 'Y' for yes or 'N' for no")
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled by user")
            return False


def execute_full_creation_plan(creation_plan, headers):
    """
    Execute the full creation plan: environments, services, applications, and components.
    
    Args:
        creation_plan (dict): Dictionary containing planned creations
        headers (dict): API headers for Phoenix requests
    """
    print(f"\n🏗️  EXECUTING FULL CREATION PLAN")
    print(f"="*60)
    
    created_count = 0
    failed_count = 0
    
    # Step 1: Create Environments
    if creation_plan['environments']:
        print(f"\n🌍 Creating {len(creation_plan['environments'])} environments...")
        for env_name, env_data in creation_plan['environments'].items():
            try:
                environment = {
                    'Name': env_name,
                    'Type': env_data['type'],
                    'Status': 'Production',
                    'Responsable': 'auto-generated@phoenix.com',
                    'Tier': 5,
                    'TeamName': env_data['team']
                }
                create_environment(environment, headers)
                print(f"   ✅ Created environment: {env_name}")
                created_count += 1
            except Exception as e:
                print(f"   ❌ Failed to create environment {env_name}: {str(e)}")
                failed_count += 1
    
    # Step 2: Create Applications (for components)
    if creation_plan['applications']:
        print(f"\n📦 Creating {len(creation_plan['applications'])} applications...")
        for app_name, app_data in creation_plan['applications'].items():
            try:
                # Note: Application creation logic would need to be implemented
                # For now, we'll just log what would be created
                print(f"   ℹ️  Would create application: {app_name} (team: {app_data['team']})")
                print(f"      Note: Application creation API call not implemented yet")
                created_count += 1
            except Exception as e:
                print(f"   ❌ Failed to create application {app_name}: {str(e)}")
                failed_count += 1
    
    # Step 3: Create Services (already created in the main flow, but we could add environment linking here)
    if creation_plan['services']:
        print(f"\n🔧 Services ({len(creation_plan['services'])}) already created in main flow")
    
    # Step 4: Create Components (already created in the main flow, but we could add application linking here)  
    if creation_plan['components']:
        print(f"\n🧩 Components ({len(creation_plan['components'])}) already created in main flow")
    
    print(f"\n📊 FULL CREATION SUMMARY")
    print(f"   ✅ Successfully created: {created_count}")
    print(f"   ❌ Failed to create: {failed_count}")
    print(f"="*60)


def extract_component_name_from_pattern(asset_names):
    """
    Extract a logical component name from a list of similar asset names.
    
    Examples:
        ['prod-db-mysql-01', 'prod-db-mysql-02', 'prod-db-mysql-03'] -> 'prod-db-mysql'
        ['web-server-staging-1', 'web-server-staging-2'] -> 'web-server-staging'
        ['nginx-01', 'nginx-02', 'nginx-03'] -> 'nginx'
        ['usb-hil-ntt-as-01-2c-a-13', 'usb-hil-ntt-as-02-2c-b-13'] -> 'usb-hil-ntt-as'
    
    Args:
        asset_names (list): List of similar asset names
    
    Returns:
        str: Extracted component name
    """
    if not asset_names:
        return "unknown-component"
    
    if len(asset_names) == 1:
        return asset_names[0]
    
    # Find common prefix by comparing all names
    common_prefix = asset_names[0]
    
    for name in asset_names[1:]:
        # Find the longest common prefix
        i = 0
        while i < min(len(common_prefix), len(name)) and common_prefix[i] == name[i]:
            i += 1
        common_prefix = common_prefix[:i]
    
    # Clean up the prefix by removing trailing separators and numbers
    import re
    
    # Remove trailing hyphens, underscores, and numbers with more intelligent pattern matching
    component_name = re.sub(r'[-_]+(?:\d+[-_]*)*$', '', common_prefix)
    
    # If the result is empty or too short, use more sophisticated extraction
    if len(component_name) < 3:
        # Try to extract meaningful parts from the first asset name
        first_asset = asset_names[0]
        
        # Remove common suffixes like numbers, rack identifiers, etc.
        component_name = re.sub(r'[-_](?:\d+[-_]*[a-z]*[-_]*\d*)+$', '', first_asset)
        
        # If still too short, try removing just the final numeric sequence
        if len(component_name) < 3:
            component_name = re.sub(r'[-_]?\d+$', '', first_asset)
    
    # Final fallback
    if len(component_name) < 3:
        component_name = asset_names[0]
    
    return component_name


def extract_environment_name_from_assets(asset_names, asset_type="INFRA"):
    """
    Extract a logical environment name from asset names.
    
    Examples:
        ['usb-hil-ntt-as-01', 'usb-hil-ntt-cs-02'] -> 'usb-hil-ntt'
        ['prod-web-01', 'prod-web-02'] -> 'prod'
        ['staging-db-mysql-01', 'staging-db-mysql-02'] -> 'staging'
    
    Args:
        asset_names (list): List of asset names
        asset_type (str): Asset type for context
    
    Returns:
        str: Extracted environment name
    """
    if not asset_names:
        return f"default-{asset_type.lower()}-environment"
    
    if len(asset_names) == 1:
        # For single asset, try to extract meaningful environment name
        import re
        name = asset_names[0]
        
        # Try to extract first 2-3 meaningful segments
        parts = re.split(r'[-_.]', name)
        if len(parts) >= 2:
            env_name = '-'.join(parts[:2])  # Take first 2 parts
        else:
            env_name = parts[0] if parts else name
            
        return env_name
    
    # Find common prefix for multiple assets
    common_prefix = asset_names[0]
    
    for name in asset_names[1:]:
        i = 0
        while i < min(len(common_prefix), len(name)) and common_prefix[i] == name[i]:
            i += 1
        common_prefix = common_prefix[:i]
    
    import re
    
    # Clean up the prefix and extract meaningful environment name
    # Remove trailing separators and numbers
    env_name = re.sub(r'[-_]+(?:\d+[-_]*)*$', '', common_prefix)
    
    # If too short, try to get first meaningful segments
    if len(env_name) < 3:
        first_asset = asset_names[0]
        parts = re.split(r'[-_.]', first_asset)
        
        # Take first 2-3 parts that make sense for environment naming
        meaningful_parts = []
        for part in parts[:3]:  # Limit to first 3 parts
            if part and not re.match(r'^\d+$', part):  # Skip pure numbers
                meaningful_parts.append(part)
            if len(meaningful_parts) >= 2:  # Stop after 2 meaningful parts
                break
        
        if meaningful_parts:
            env_name = '-'.join(meaningful_parts)
        else:
            env_name = parts[0] if parts else first_asset
    
    # Ensure minimum length and fallback
    if len(env_name) < 3:
        env_name = f"{asset_names[0].split('-')[0]}-{asset_type.lower()}"
    
    return env_name


def extract_responsible_user_from_assets(assets, autogroup_config):
    """
    Extract responsible user from asset tags based on autogroup configuration.
    
    Args:
        assets (list): List of assets with tags
        autogroup_config (dict): Autogroup configuration
    
    Returns:
        str: Responsible user email or None if not found/invalid
    """
    if not autogroup_config.get('extract_responsible_from_tags', True):
        return None
    
    # Get responsible tag keys to search for
    responsible_tag_key = autogroup_config.get('responsible_tag_key', 'owner')
    alternative_keys = autogroup_config.get('alternative_responsible_tag_keys', [])
    all_keys = [responsible_tag_key] + alternative_keys
    
    # Search for responsible user in asset tags
    responsible_users = set()
    
    for asset in assets:
        if 'tags' in asset:
            for tag in asset['tags']:
                tag_key = tag.get('key', '').lower()
                tag_value = tag.get('value', '').strip()
                
                if tag_key in [key.lower() for key in all_keys] and tag_value:
                    responsible_users.add(tag_value)
    
    # If multiple responsible users found, take the first one
    if responsible_users:
        responsible_user = list(responsible_users)[0]
        
        # Validate email format if enabled
        if autogroup_config.get('validate_responsible_email', True):
            if is_valid_email(responsible_user):
                return responsible_user
            elif autogroup_config.get('fallback_to_default_responsible', True):
                print(f"⚠️  Invalid email format for responsible user: {responsible_user}, using default")
                return None
            else:
                return None
        else:
            return responsible_user
    
    return None


def is_valid_email(email):
    """
    Validate email address format.
    
    Args:
        email (str): Email address to validate
    
    Returns:
        bool: True if valid email format, False otherwise
    """
    import re
    
    # Basic email validation pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def get_responsible_user_for_type(asset_type, assets, autogroup_config):
    """
    Get the appropriate responsible user for a given asset type.
    
    Args:
        asset_type (str): Type of asset (environment, application, service, component)
        assets (list): List of assets to extract responsible user from
        autogroup_config (dict): Autogroup configuration
    
    Returns:
        str: Responsible user email
    """
    # Try to extract from asset tags first
    extracted_user = extract_responsible_user_from_assets(assets, autogroup_config)
    
    if extracted_user:
        return extracted_user
    
    # Fall back to default based on asset type
    default_key = f'default_{asset_type}_responsible'
    return autogroup_config.get(default_key, 'auto-admin@company.com')


def load_autogroup_config(resource_folder):
    """
    Load autogroup configuration from autogroup.ini file.
    
    Args:
        resource_folder (str): Path to the Resources folder
        
    Returns:
        dict: Configuration dictionary with autogroup settings
    """
    import configparser
    import os
    
    config = {}
    config_file_path = os.path.join(resource_folder, 'autogroup.ini')
    
    if not os.path.exists(config_file_path):
        print(f"ℹ️  AutoGroup config file not found: {config_file_path}")
        print("ℹ️  Using default name-based grouping. Copy autogroup.ini.example to autogroup.ini to enable tag-based grouping.")
        return {
            'enable_tag_based_grouping': False,
            'base_tag_key': 'team-name',
            'alternative_tag_keys': ['pteam', 'owner', 'project'],
            'application_naming_strategy': 'tag_value',
            'custom_application_prefix': 'app',
            'component_name_similarity_threshold': 0.8,
            'component_min_assets_per_component': 2,
            'create_separate_applications_per_tag': True,
            'fallback_for_untagged_assets': 'default_group',
            'default_group_name': 'untagged-assets',
            # Responsible users defaults
            'default_environment_responsible': 'auto-admin@company.com',
            'default_application_responsible': 'auto-admin@company.com',
            'default_service_responsible': 'auto-admin@company.com',
            'default_component_responsible': 'auto-admin@company.com',
            'extract_responsible_from_tags': True,
            'responsible_tag_key': 'owner',
            'alternative_responsible_tag_keys': ['responsible', 'admin', 'lead', 'manager'],
            'validate_responsible_email': True,
            'fallback_to_default_responsible': True
        }
    
    try:
        parser = configparser.ConfigParser()
        parser.read(config_file_path)
        
        if 'tag_based_grouping' in parser:
            section = parser['tag_based_grouping']
            
            config['enable_tag_based_grouping'] = section.getboolean('enable_tag_based_grouping', False)
            config['base_tag_key'] = section.get('base_tag_key', 'team-name')
            
            # Parse alternative tag keys
            alt_keys = section.get('alternative_tag_keys', 'pteam,owner,project')
            config['alternative_tag_keys'] = [key.strip() for key in alt_keys.split(',') if key.strip()]
            
            config['application_naming_strategy'] = section.get('application_naming_strategy', 'tag_value')
            config['custom_application_prefix'] = section.get('custom_application_prefix', 'app')
            config['component_name_similarity_threshold'] = section.getfloat('component_name_similarity_threshold', 0.8)
            config['component_min_assets_per_component'] = section.getint('component_min_assets_per_component', 2)
            config['create_separate_applications_per_tag'] = section.getboolean('create_separate_applications_per_tag', True)
            config['fallback_for_untagged_assets'] = section.get('fallback_for_untagged_assets', 'default_group')
            config['default_group_name'] = section.get('default_group_name', 'untagged-assets')
            
            print(f"✅ Loaded autogroup configuration from: {config_file_path}")
            print(f"   📋 Tag-based grouping: {'enabled' if config['enable_tag_based_grouping'] else 'disabled'}")
            if config['enable_tag_based_grouping']:
                print(f"   🏷️  Base tag key: {config['base_tag_key']}")
                print(f"   📱 Application naming: {config['application_naming_strategy']}")
        else:
            print(f"⚠️  Warning: [tag_based_grouping] section not found in {config_file_path}")
            config['enable_tag_based_grouping'] = False
        
        # Load responsible users configuration
        if 'responsible_users' in parser:
            section = parser['responsible_users']
            
            config['default_environment_responsible'] = section.get('default_environment_responsible', 'auto-admin@company.com')
            config['default_application_responsible'] = section.get('default_application_responsible', 'auto-admin@company.com')
            config['default_service_responsible'] = section.get('default_service_responsible', 'auto-admin@company.com')
            config['default_component_responsible'] = section.get('default_component_responsible', 'auto-admin@company.com')
            config['extract_responsible_from_tags'] = section.getboolean('extract_responsible_from_tags', True)
            config['responsible_tag_key'] = section.get('responsible_tag_key', 'owner')
            
            # Parse alternative responsible tag keys
            alt_responsible_keys = section.get('alternative_responsible_tag_keys', 'responsible,admin,lead,manager')
            config['alternative_responsible_tag_keys'] = [key.strip() for key in alt_responsible_keys.split(',') if key.strip()]
            
            config['validate_responsible_email'] = section.getboolean('validate_responsible_email', True)
            config['fallback_to_default_responsible'] = section.getboolean('fallback_to_default_responsible', True)
            
            print(f"   👤 Default environment responsible: {config['default_environment_responsible']}")
            print(f"   👤 Extract responsible from tags: {'enabled' if config['extract_responsible_from_tags'] else 'disabled'}")
            if config['extract_responsible_from_tags']:
                print(f"   🏷️  Responsible tag key: {config['responsible_tag_key']}")
        else:
            # Set defaults if section not found
            config.update({
                'default_environment_responsible': 'auto-admin@company.com',
                'default_application_responsible': 'auto-admin@company.com',
                'default_service_responsible': 'auto-admin@company.com',
                'default_component_responsible': 'auto-admin@company.com',
                'extract_responsible_from_tags': True,
                'responsible_tag_key': 'owner',
                'alternative_responsible_tag_keys': ['responsible', 'admin', 'lead', 'manager'],
                'validate_responsible_email': True,
                'fallback_to_default_responsible': True
            })
            
    except Exception as e:
        print(f"❌ Error reading autogroup config file {config_file_path}: {e}")
        print("ℹ️  Using default settings")
        config['enable_tag_based_grouping'] = False
    
    return config


def group_assets_by_tags(assets, autogroup_config):
    """
    Group assets by common tag values.
    
    Args:
        assets (list): List of asset objects with tags
        autogroup_config (dict): Autogroup configuration
        
    Returns:
        dict: Dictionary with tag values as keys and asset lists as values
    """
    base_tag_key = autogroup_config['base_tag_key']
    alternative_keys = autogroup_config['alternative_tag_keys']
    fallback_behavior = autogroup_config['fallback_for_untagged_assets']
    default_group_name = autogroup_config['default_group_name']
    
    tag_groups = {}
    untagged_assets = []
    
    print(f"🏷️  Grouping assets by tag key: {base_tag_key}")
    print(f"📋 Alternative tag keys: {', '.join(alternative_keys)}")
    
    for asset in assets:
        asset_tags = asset.get('tags', [])
        tag_value = None
        found_tag_key = None
        
        # Look for the base tag key first
        for tag in asset_tags:
            if tag.get('key') == base_tag_key and tag.get('value'):
                tag_value = tag['value']
                found_tag_key = base_tag_key
                break
        
        # If base tag not found, try alternative keys
        if not tag_value:
            for alt_key in alternative_keys:
                for tag in asset_tags:
                    if tag.get('key') == alt_key and tag.get('value'):
                        tag_value = tag['value']
                        found_tag_key = alt_key
                        break
                if tag_value:
                    break
        
        if tag_value:
            if tag_value not in tag_groups:
                tag_groups[tag_value] = []
            tag_groups[tag_value].append(asset)
            if DEBUG:
                print(f"   📌 Asset '{asset.get('name', 'Unknown')}' → group '{tag_value}' (key: {found_tag_key})")
        else:
            untagged_assets.append(asset)
            if DEBUG:
                print(f"   ⚠️  Asset '{asset.get('name', 'Unknown')}' has no matching tags")
    
    # Handle untagged assets based on fallback behavior
    if untagged_assets:
        print(f"⚠️  Found {len(untagged_assets)} assets without matching tags")
        
        if fallback_behavior == 'default_group':
            tag_groups[default_group_name] = untagged_assets
            print(f"   📦 Added untagged assets to default group: {default_group_name}")
        elif fallback_behavior == 'skip':
            print(f"   ⏭️  Skipping {len(untagged_assets)} untagged assets")
        # 'name_based' fallback is handled in the main function
    
    print(f"📊 Created {len(tag_groups)} tag-based groups:")
    for tag_value, assets_in_group in tag_groups.items():
        print(f"   🏷️  '{tag_value}': {len(assets_in_group)} assets")
    
    return tag_groups, untagged_assets


def generate_application_name_from_tag(tag_value, tag_key, autogroup_config):
    """
    Generate application name based on tag value and naming strategy.
    
    Args:
        tag_value (str): The tag value
        tag_key (str): The tag key used
        autogroup_config (dict): Autogroup configuration
        
    Returns:
        str: Generated application name
    """
    strategy = autogroup_config['application_naming_strategy']
    custom_prefix = autogroup_config['custom_application_prefix']
    
    if strategy == 'tag_value':
        return tag_value
    elif strategy == 'tag_key_value':
        return f"{tag_key}-{tag_value}"
    elif strategy == 'custom_prefix':
        return f"{custom_prefix}-{tag_value}"
    else:
        return tag_value  # Default fallback


def group_assets_by_similar_name_within_tag_group(assets, similarity_threshold=0.8):
    """
    Group assets by name similarity within a tag-based group.
    This is used after tag-based grouping to create components within each tag group.
    
    Args:
        assets (list): List of asset objects from the same tag group
        similarity_threshold (float): Similarity threshold for name matching
        
    Returns:
        list: List of asset name groups
    """
    import Levenshtein
    
    asset_names = [asset.get('name', '') for asset in assets]
    asset_groups = []
    
    for asset_name in asset_names:
        added_to_group = False
        for group in asset_groups:
            should_add_to_group = True
            for grouped_asset_name in group:
                if Levenshtein.ratio(asset_name, grouped_asset_name) < similarity_threshold:
                    should_add_to_group = False
                    break
            if should_add_to_group:
                group.append(asset_name)
                added_to_group = True
                break
        if not added_to_group:
            asset_groups.append([asset_name])
    
    return asset_groups


def prompt_grouping_method_selection(autogroup_config):
    """
    Prompt user to select grouping method: name-based or tag-based.
    
    Args:
        autogroup_config (dict): Autogroup configuration
        
    Returns:
        str: Selected method ('name_based' or 'tag_based')
    """
    print("\\n" + "="*60)
    print("ASSET GROUPING METHOD SELECTION")
    print("="*60)
    
    if not autogroup_config['enable_tag_based_grouping']:
        print("ℹ️  Tag-based grouping is disabled in autogroup.ini")
        print("📋 Using name-based grouping (assets grouped by name similarity)")
        return 'name_based'
    
    print("\\nSelect asset grouping method:")
    print("\\n1. 🏷️  TAG-BASED   - Group assets by common tag values")
    print("2. 📝 NAME-BASED   - Group assets by name similarity (original method)")
    
    print(f"\\nTag-Based Grouping Details:")
    print(f"- Base tag key: {autogroup_config['base_tag_key']}")
    print(f"- Alternative keys: {', '.join(autogroup_config['alternative_tag_keys'])}")
    print(f"- Application naming: {autogroup_config['application_naming_strategy']}")
    print(f"- Separate apps per tag: {'Yes' if autogroup_config['create_separate_applications_per_tag'] else 'No'}")
    
    while True:
        try:
            choice = input("\\nEnter your choice (1-2): ").strip()
            
            if choice == '1':
                print("\\n✅ Selected: TAG-BASED grouping")
                print(f"🏷️  Will group assets by '{autogroup_config['base_tag_key']}' tag values")
                return 'tag_based'
            elif choice == '2':
                print("\\n✅ Selected: NAME-BASED grouping")
                print("📝 Will group assets by name similarity patterns")
                return 'name_based'
            else:
                print("❌ Invalid choice. Please enter 1 or 2.")
                
        except KeyboardInterrupt:
            print("\\n\\n❌ Operation cancelled by user")
            return None
        except Exception as e:
            print(f"❌ Error: {e}. Please try again.")


def prompt_asset_type_selection():
    """
    Prompt user to select which asset types to process.
    
    Returns:
        str: Selected category ('all', 'cloud', 'code', 'infrastructure', 'web')
    """
    print("\n" + "="*60)
    print("ASSET TYPE SELECTION FOR COMPONENT CREATION")
    print("="*60)
    print("\nSelect which asset types to process:")
    print("\n1. 🌐 ALL        - All asset types (comprehensive scan)")
    print("2. ☁️  CLOUD      - Cloud resources and containers")
    print("3. 💻 CODE       - Repository and source code assets")
    print("4. 🏗️  INFRASTRUCTURE - Infrastructure components")
    print("5. 🌍 WEB        - Web applications and APIs")
    
    print("\nAsset Type Details:")
    print("- CLOUD: CLOUD, CONTAINER")
    print("- CODE: REPOSITORY, SOURCE_CODE, BUILD, FOSS, SAST")
    print("- INFRASTRUCTURE: INFRA")
    print("- WEB: WEB, WEBSITE_API")
    print("- ALL: All above types")
    
    while True:
        try:
            choice = input("\nEnter your choice (1-5): ").strip()
            
            choice_mapping = {
                '1': 'all',
                '2': 'cloud', 
                '3': 'code',
                '4': 'infrastructure',
                '5': 'web'
            }
            
            if choice in choice_mapping:
                selected = choice_mapping[choice]
                asset_types = get_asset_types_for_category(selected)
                print(f"\n✅ Selected: {selected.upper()}")
                print(f"📋 Will process asset types: {', '.join(asset_types)}")
                return selected
            else:
                print("❌ Invalid choice. Please enter 1, 2, 3, 4, or 5.")
                
        except KeyboardInterrupt:
            print("\n\n❌ Operation cancelled by user")
            return None
        except Exception as e:
            print(f"❌ Error: {e}. Please try again.")


def create_components_from_assets(applicationEnvironments, phoenix_components, headers2, cli_config=None):
    global headers
    if not headers:
        headers = headers2
    
    # Load autogroup configuration
    resource_folder = os.path.join(os.path.dirname(__file__), '..', 'Resources')
    autogroup_config = load_autogroup_config(resource_folder)
    
    # Check if full creation mode is enabled
    create_automatically_groups = cli_config.get('create_automatically_groups', False) if cli_config else False
    silent_mode = cli_config.get('silent', False) if cli_config else False
    
    # Override configuration with CLI parameters if provided
    if cli_config:
        print("🔧 Using CLI configuration parameters")
        
        # Override tag configuration if provided
        if cli_config.get('tag_base'):
            autogroup_config['base_tag_key'] = cli_config['tag_base']
            print(f"   🏷️  CLI override - base tag key: {cli_config['tag_base']}")
        
        if cli_config.get('tag_alternative'):
            alt_keys = [key.strip() for key in cli_config['tag_alternative'].split(',') if key.strip()]
            autogroup_config['alternative_tag_keys'] = alt_keys
            print(f"   🏷️  CLI override - alternative tag keys: {', '.join(alt_keys)}")
        
        # Determine grouping method
        grouping_method = cli_config.get('grouping_method', 'name_based')  # Default to name_based
        print(f"   🎯 CLI override - grouping method: {grouping_method}")
        
        if not grouping_method:
            print("❌ No grouping method selected. Exiting component creation.")
            return []
        
        # Determine asset type
        if cli_config.get('asset_type'):
            selected_category = cli_config['asset_type']
            print(f"   📂 CLI override - asset type: {selected_category}")
        else:
            # Prompt user for asset type selection if not specified via CLI
            selected_category = prompt_asset_type_selection()
            if not selected_category:
                print("❌ No asset type selected. Exiting component creation.")
                return []
    else:
        # Interactive mode - prompt user for selections
        print("🎮 Interactive mode - prompting for user selections")
        
        # Prompt user for grouping method selection
        grouping_method = prompt_grouping_method_selection(autogroup_config)
        if not grouping_method:
            print("❌ No grouping method selected. Exiting component creation.")
            return []
        
        # Prompt user for asset type selection
        selected_category = prompt_asset_type_selection()
        if not selected_category:
            print("❌ No asset type selected. Exiting component creation.")
            return []
    
    types = get_asset_types_for_category(selected_category)
    phoenix_component_names = [pcomponent.get('name') for pcomponent in phoenix_components]
    auto_created_components = []  # Track created components for YAML export
    
    print(f"\n🚀 Starting component creation for asset types: {', '.join(types)}")
    print(f"📊 Processing {len(applicationEnvironments)} environments...")
    print(f"🎯 Using {grouping_method.upper().replace('_', '-')} grouping method")
    
    if create_automatically_groups:
        print(f"🏗️  Full creation mode: Will create environments, services, applications, and components")
        print(f"🔇 Silent mode: {'ENABLED (auto-accept)' if silent_mode else 'DISABLED (will prompt for confirmation)'}")
    
    if grouping_method == 'tag_based':
        return create_components_from_assets_tag_based(applicationEnvironments, phoenix_components, types, autogroup_config, headers, create_automatically_groups, silent_mode)
    else:
        return create_components_from_assets_name_based(applicationEnvironments, phoenix_components, types, headers, create_automatically_groups, silent_mode, autogroup_config)


def create_components_from_assets_name_based(applicationEnvironments, phoenix_components, types, headers, create_automatically_groups=False, silent_mode=False, autogroup_config=None):
    """Enhanced name-based component creation logic with logical environment grouping"""
    phoenix_component_names = [pcomponent.get('name') for pcomponent in phoenix_components]
    auto_created_components = []
    
    # Track what will be created for preview
    creation_plan = {
        'environments': {},
        'services': {},
        'applications': {},
        'components': {}
    }
    
    # Collect all assets from all environments first, then group them logically
    all_assets_by_type = {}
    
    print(f"\n🔍 Collecting assets from all environments for logical grouping...")
    
    for type in types:
        print(f"\n📂 Collecting {type} assets from all environments...")
        all_assets_by_type[type] = []
        
        for appEnv in applicationEnvironments:
            env_name = appEnv.get('name')
            env_id = appEnv.get('id')
            env_subtype = appEnv.get('subtype', 'CLOUD').upper()
            
            print(f"🔍 Checking environment: {env_name} (Type: {env_subtype})")
            
            # Get assignment strategy for this asset type
            assignment_strategy = get_asset_assignment_strategy(type)
            
            # Skip if environment not compatible with asset type
            if not is_environment_compatible_with_asset_type(env_subtype, type, assignment_strategy):
                print(f"   ⏭️  Skipping {env_name} - environment type '{env_subtype}' not compatible with asset type '{type}'")
                continue
            
            # Fetch assets for this environment and type
            assets = get_assets(env_id, type, headers, include_tags=True)
            if assets:
                print(f"   📋 Found {len(assets)} {type} assets in {env_name}")
                # Add environment context to each asset
                for asset in assets:
                    asset['source_env_name'] = env_name
                    asset['source_env_id'] = env_id
                    asset['source_env_subtype'] = env_subtype
                all_assets_by_type[type].extend(assets)
            else:
                print(f"   📋 No {type} assets found in {env_name}")
    
    # Now process each asset type with logical environment grouping
    for type in types:
        if not all_assets_by_type.get(type):
            print(f"\n⚠️  No {type} assets found across all environments")
            continue
            
        print(f"\n📂 Processing asset type: {type} ({len(all_assets_by_type[type])} total assets)")
        assets = all_assets_by_type[type]
        
        # Get assignment strategy
        assignment_strategy = get_asset_assignment_strategy(type)
        print(f"   🎯 Assignment strategy: {assignment_strategy['description']}")
        
        # Group assets by name similarity
        asset_names = [asset['name'] for asset in assets]
        similar_asset_groups = group_assets_by_name_similarity(asset_names, ASSET_NAME_SIMILARITY_THRESHOLD)
        
        print(f"   📊 Found {len(similar_asset_groups)} asset groups based on name similarity")
        
        # Group similar assets by logical environments
        logical_environments = {}
        already_suggested_components = set()
        
        for asset_group_names in similar_asset_groups:
            if len(asset_group_names) >= ASSET_GROUP_MIN_SIZE_FOR_COMPONENT_CREATION:
                # Get full asset objects for this group
                asset_group = [asset for asset in assets if asset['name'] in asset_group_names]
                
                # Extract logical environment name from this asset group
                logical_env_name = extract_environment_name_from_assets(asset_group_names, type)
                
                if logical_env_name not in logical_environments:
                    logical_environments[logical_env_name] = {
                        'name': logical_env_name,
                        'type': type,
                        'asset_groups': [],
                        'source_environments': set()
                    }
                
                # Add source environments
                for asset in asset_group:
                    logical_environments[logical_env_name]['source_environments'].add(asset['source_env_name'])
                
                logical_environments[logical_env_name]['asset_groups'].append(asset_group)
        
        # Process each logical environment
        for logical_env_name, logical_env_data in logical_environments.items():
            print(f"\n🌍 Processing Logical Environment: {logical_env_name}")
            print(f"   📊 Asset Groups: {len(logical_env_data['asset_groups'])}")
            print(f"   📁 Source Environments: {', '.join(logical_env_data['source_environments'])}")
            
            # Process each asset group within this logical environment
            for asset_group in logical_env_data['asset_groups']:
                asset_names = [asset['name'] for asset in asset_group]
                sample_assets = asset_names[:3]
                
                # Extract intelligent component name
                suggested_component_name = extract_component_name_from_pattern(asset_names)
                
                # Skip if already suggested
                if suggested_component_name in already_suggested_components:
                    print(f"   ⚠️  Skipping {suggested_component_name} - already exists or suggested")
                    continue
                
                already_suggested_components.add(suggested_component_name)
                
                print(f"\n💡 COMPONENT SUGGESTION")
                print(f"   Logical Environment: {logical_env_name}")
                print(f"   Asset Type: {type}")
                print(f"   Assets Found: {len(asset_group)} similar assets")
                print(f"   Sample Assets: {', '.join(sample_assets)}{'...' if len(asset_names) > 3 else ''}")
                print(f"")
                print(f"   Suggested Component: {suggested_component_name}")
                
                if silent_mode:
                    print(f"\n   🤖 SILENT MODE: Auto-accepting component '{suggested_component_name}'")
                    answer = 'Y'
                else:
                    answer = input(f"\n   Create component '{suggested_component_name}'? [Y=yes, N=no, A=alter name]: ").strip().upper()
                
                if answer == 'Y':
                    component_name = suggested_component_name
                elif answer == 'A':
                    component_name = input("   Enter component name: ").strip()
                    if not component_name:
                        print("   ❌ Invalid component name. Skipping.")
                        continue
                else:
                    print("   ⏭️  Skipping component creation")
                    continue
                
                print(f"   🔧 Creating component: {component_name}")
                
                # Get team names from assets if available
                team_names = []
                for asset in asset_group:
                    if 'tags' in asset:
                        for tag in asset['tags']:
                            if tag.get('key') == 'pteam':
                                team_value = tag.get('value')
                                if team_value and team_value not in team_names:
                                    team_names.append(team_value)
                
                print(f"   👥 Team assignments: {team_names if team_names else 'None'}")
                
                try:
                    if assignment_strategy['target'] == 'service':
                        # Create service in logical environment
                        print(f"\n[Service Creation]")
                        print(f" └─ Logical Environment: {logical_env_name}")
                        print(f" └─ Service: {component_name}")
                        print(f" └─ Team: {team_names[0] if team_names else 'default-team'}")
                        
                        service_to_create = {
                            "Service": component_name,
                            "Type": assignment_strategy['service_type'],
                            "Tier": 5,
                            "TeamNames": team_names
                        }
                        
                        team_name = team_names[0] if team_names else "default-team"
                        
                        # Create service in the logical environment
                        add_service(logical_env_name, logical_env_name, service_to_create, 5, team_name, headers)
                        print(f"   ✅ Successfully created ENVIRONMENT SERVICE: {component_name} in {logical_env_name} (Type: {assignment_strategy['service_type']})")
                        
                        # Store service info for creation plan
                        auto_created_components.append({
                            'environment_name': logical_env_name,
                            'application_name': logical_env_name,
                            'component_name': component_name,
                            'team_names': team_names,
                            'status': None,
                            'type': None,
                            'asset_count': len(asset_group),
                            'asset_type': type,
                            'original_group_name': asset_names[0],
                            'suggested_name': suggested_component_name,
                            'sample_assets': asset_names[:5],
                            'grouping_method': 'name_based',
                            'assignment_strategy': assignment_strategy['target'],
                            'service_type': assignment_strategy.get('service_type'),
                            'asset_names': asset_names,  # Store ALL asset names for MULTI_MultiConditionRules
                            'environment_subtype': type,
                            'responsible_user': get_responsible_user_for_type('service', asset_group, autogroup_config or {})
                        })
                    else:
                        # Create component in application (existing logic for non-service assets)
                        component_result = create_custom_component(
                            logical_env_name, 
                            component_name,
                            team_names,
                            headers
                        )
                        
                        if component_result:
                            print(f"   ✅ Successfully created APPLICATION COMPONENT: {component_name}")
                            
                            auto_created_components.append({
                                'environment_name': logical_env_name,
                                'application_name': logical_env_name,
                                'component_name': component_name,
                                'team_names': team_names,
                                'status': None,
                                'type': None,
                                'asset_count': len(asset_group),
                                'asset_type': type,
                                'original_group_name': asset_names[0],
                                'suggested_name': suggested_component_name,
                                'sample_assets': asset_names[:5],
                                'grouping_method': 'name_based',
                                'assignment_strategy': 'component',
                                'asset_names': asset_names,
                                'environment_subtype': type,
                                'responsible_user': get_responsible_user_for_type('component', asset_group, autogroup_config or {})
                            })
                        else:
                            print(f"   ❌ Failed to create component {component_name}")
                            
                except Exception as e:
                    print(f"   ❌ Failed to create component {component_name}: {str(e)}")
    
    # Handle full creation mode
    if create_automatically_groups and auto_created_components:
        print(f"\n🏗️  FULL CREATION MODE - Preparing creation plan...")
        
        # Build creation plan from auto_created_components
        for component in auto_created_components:
            env_name = component.get('environment_name', 'Unknown')
            app_name = component.get('application_name', env_name)
            comp_name = component.get('component_name', 'Unknown')
            assignment_strategy = component.get('assignment_strategy', 'component')
            
            if assignment_strategy == 'service':
                # For services, we need environments
                if env_name not in creation_plan['environments']:
                    creation_plan['environments'][env_name] = {
                        'type': component.get('environment_subtype', 'CLOUD').upper(),
                        'team': component.get('team_names', ['auto-generated'])[0] if component.get('team_names') else 'auto-generated'
                    }
                
                # Add service
                service_key = f"{env_name}::{comp_name}"
                creation_plan['services'][service_key] = {
                    'name': comp_name,
                    'environment': env_name,
                    'service_type': component.get('service_type', 'Cloud'),
                    'asset_count': component.get('asset_count', 0)
                }
            else:
                # For components, we need applications
                if app_name not in creation_plan['applications']:
                    creation_plan['applications'][app_name] = {
                        'team': component.get('team_names', ['auto-generated'])[0] if component.get('team_names') else 'auto-generated'
                    }
                
                # Add component
                component_key = f"{app_name}::{comp_name}"
                creation_plan['components'][component_key] = {
                    'name': comp_name,
                    'application': app_name,
                    'asset_count': component.get('asset_count', 0)
                }
        
        # Show preview and execute if confirmed
        show_creation_preview(creation_plan, silent_mode)
        
        if silent_mode or creation_plan:
            execute_full_creation_plan(creation_plan, headers)
    
    return auto_created_components



def create_components_from_assets_tag_based(applicationEnvironments, phoenix_components, types, autogroup_config, headers, create_automatically_groups=False, silent_mode=False):
    """New tag-based component creation logic with proper asset type routing"""
    import os
    
    phoenix_component_names = [pcomponent.get('name') for pcomponent in phoenix_components]
    auto_created_components = []
    
    # Track what will be created for preview
    creation_plan = {
        'environments': {},
        'services': {},
        'applications': {},
        'components': {}
    }
    
    for type in types:
        print(f"\n📂 Processing asset type: {type}")
        
        # Determine asset assignment strategy based on asset type
        assignment_strategy = get_asset_assignment_strategy(type)
        print(f"   🎯 Assignment strategy: {assignment_strategy['description']}")
        
        # Collect all assets from all environments for this asset type
        all_assets = []
        for appEnv in applicationEnvironments:
            if appEnv.get('type') == "ENVIRONMENT":
                env_name = appEnv.get('name', 'Unknown')
                env_subtype = appEnv.get('subType', 'Unknown')
                
                # Check if this environment type is compatible with the asset type
                if not is_environment_compatible_with_asset_type(env_subtype, type, assignment_strategy):
                    print(f"   ⏭️  Skipping {env_name} - environment type '{env_subtype}' not compatible with asset type '{type}'")
                    continue
                
                assets = get_assets(appEnv.get("id"), type, headers, include_tags=True)
                
                # Add environment context to each asset
                for asset in assets:
                    asset['source_environment'] = env_name
                    asset['source_environment_id'] = appEnv.get('id')
                    asset['source_environment_subtype'] = env_subtype
                
                all_assets.extend(assets)
                print(f"   📋 Collected {len(assets)} {type} assets from {env_name} (Type: {env_subtype})")
                if DEBUG and assets:
                    print(f"   🔍 DEBUG: Sample assets from {env_name}: {', '.join([asset.get('name', 'Unknown') for asset in assets[:5]])}")
        
        if not all_assets:
            print(f"   ℹ️  No {type} assets found across all environments")
            continue
        
        print(f"   📊 Total {type} assets collected: {len(all_assets)}")
        
        # Group assets by tags
        tag_groups, untagged_assets = group_assets_by_tags(all_assets, autogroup_config)
        
        # Process each tag group
        for tag_value, assets_in_group in tag_groups.items():
            print(f"\n🏷️  Processing tag group: '{tag_value}' ({len(assets_in_group)} assets)")
            
            # Generate application name for this tag group
            application_name = generate_application_name_from_tag(tag_value, autogroup_config['base_tag_key'], autogroup_config)
            print(f"   📱 Application name: {application_name}")
            
            # Group assets within this tag group by name similarity for component creation
            asset_names_in_group = [asset.get('name', '') for asset in assets_in_group]
            component_groups = group_assets_by_similar_name_within_tag_group(
                assets_in_group, 
                autogroup_config['component_name_similarity_threshold']
            )
            
            print(f"   🔍 Found {len(component_groups)} potential component groups within tag group")
            
            for component_group in component_groups:
                if len(component_group) >= autogroup_config['component_min_assets_per_component']:
                    # Extract component name from this group
                    suggested_component_name = extract_component_name_from_pattern(component_group)
                    
                    # Check if component already exists
                    if suggested_component_name in phoenix_component_names:
                        print(f"      ⚠️  Skipping {suggested_component_name} - component already exists")
                        continue
                    
                    print(f"\n      💡 COMPONENT SUGGESTION (Tag-Based)")
                    print(f"         Tag Group: {tag_value}")
                    print(f"         Application: {application_name}")
                    print(f"         Asset Type: {type}")
                    print(f"         Assets Found: {len(component_group)} similar assets")
                    print(f"         Sample Assets: {', '.join(component_group[:3])}{'...' if len(component_group) > 3 else ''}")
                    print(f"         Suggested Component: {suggested_component_name}")
                    
                    if silent_mode:
                        print(f"\n         🤖 SILENT MODE: Auto-accepting component '{suggested_component_name}' in application '{application_name}'")
                        answer = 'Y'
                    else:
                        answer = input(f"\n         Create component '{suggested_component_name}' in application '{application_name}'? [Y=yes, N=no, A=alter name]: ").strip().upper()
                    
                    component_name = suggested_component_name
                    
                    if answer == 'N':
                        print(f"         ❌ Skipped component creation")
                        continue
                    elif answer == 'A' and not silent_mode:
                        component_name = input(f"         Enter custom component name: ").strip()
                        if not component_name:
                            print(f"         ❌ Empty name provided, skipping")
                            continue
                    
                    # Use tag value as team name (or extract from assets)
                    team_names = [tag_value] if tag_value != autogroup_config['default_group_name'] else []
                    
                    print(f"         🔧 Creating component: {component_name}")
                    print(f"         👥 Team assignments: {', '.join(team_names) if team_names else 'None'}")
                    
                    component_to_create = {
                        "Status": None,
                        "Type": None,
                        "TeamNames": team_names,
                        "ComponentName": component_name
                    }
                    
                    try:
                        # Route to appropriate creation function based on assignment strategy
                        if assignment_strategy['target'] == 'component':
                            create_custom_component(application_name, component_to_create, headers)
                            print(f"         ✅ Successfully created APPLICATION COMPONENT: {component_name} in application: {application_name}")
                            if DEBUG:
                                print(f"         🔍 DEBUG: Component assigned to APPLICATION: {application_name}")
                                print(f"         🔍 DEBUG: Assets from environments: {', '.join(set(asset.get('source_environment', 'Unknown') for asset in component_group))}")
                        else:
                            # For services, we need to create them in the appropriate environments
                            # Group assets by source environment for service creation
                            env_asset_groups = {}
                            for asset in component_group:
                                env_name = asset.get('source_environment', 'Unknown')
                                env_id = asset.get('source_environment_id')
                                env_subtype = asset.get('source_environment_subtype', 'Unknown')
                                if env_name not in env_asset_groups:
                                    env_asset_groups[env_name] = {
                                        'assets': [],
                                        'env_id': env_id,
                                        'env_subtype': env_subtype
                                    }
                                env_asset_groups[env_name]['assets'].append(asset)
                            
                            # Create service in each relevant environment
                            for env_name, env_data in env_asset_groups.items():
                                service_to_create = {
                                    "Service": component_name,
                                    "Type": assignment_strategy['service_type'],
                                    "Tier": 5,  # Default tier
                                    "TeamNames": team_names
                                }
                                # Use the team name from the first available team
                                team_name = team_names[0] if team_names else "default-team"
                                add_service(env_name, env_data['env_id'], service_to_create, 5, team_name, headers)
                                print(f"         ✅ Successfully created ENVIRONMENT SERVICE: {component_name} in {env_name} (Type: {assignment_strategy['service_type']})")
                                if DEBUG:
                                    print(f"         🔍 DEBUG: Service assigned to ENVIRONMENT: {env_name} (SubType: {env_data['env_subtype']})")
                                    print(f"         🔍 DEBUG: Assets assigned: {', '.join([asset.get('name', 'Unknown') for asset in env_data['assets'][:5]])}")
                        
                        # Track the created component/service for YAML export
                        auto_created_components.append({
                            'environment_name': application_name,
                            'application_name': application_name,
                            'component_name': component_name,
                            'team_names': team_names,
                            'status': None,
                            'type': None,
                            'asset_count': len(component_group),
                            'asset_type': type,
                            'original_group_name': component_group[0] if isinstance(component_group[0], str) else component_group[0].get('name', 'Unknown'),
                            'suggested_name': suggested_component_name,
                            'sample_assets': [asset.get('name', 'Unknown') if isinstance(asset, dict) else asset for asset in component_group[:5]],
                            'grouping_method': 'tag_based',
                            'tag_group': tag_value,
                            'tag_key': autogroup_config['base_tag_key'],
                            'assignment_strategy': assignment_strategy['target'],
                            'service_type': assignment_strategy.get('service_type')
                        })
                    except Exception as e:
                        print(f"         ❌ Failed to create component {component_name}: {str(e)}")
                else:
                    print(f"      ⏭️  Skipping group with {len(component_group)} assets (below minimum of {autogroup_config['component_min_assets_per_component']})")
        
        # Handle untagged assets if fallback is name_based
        if untagged_assets and autogroup_config['fallback_for_untagged_assets'] == 'name_based':
            print(f"\n📝 Processing {len(untagged_assets)} untagged assets with name-based grouping")
            asset_names = [asset.get('name', '') for asset in untagged_assets]
            asset_groups = group_assets_by_similar_name(asset_names)
            
            for group in asset_groups:
                if len(group) > ASSET_GROUP_MIN_SIZE_FOR_COMPONENT_CREATION:
                    suggested_component_name = extract_component_name_from_pattern(group)
                    
                    if suggested_component_name not in phoenix_component_names:
                        print(f"\n   💡 UNTAGGED ASSET COMPONENT SUGGESTION")
                        print(f"      Assets Found: {len(group)} similar assets")
                        print(f"      Sample Assets: {', '.join(group[:3])}{'...' if len(group) > 3 else ''}")
                        print(f"      Suggested Component: {suggested_component_name}")
                        
                        if silent_mode:
                            print(f"\n      🤖 SILENT MODE: Auto-accepting component '{suggested_component_name}' for untagged assets")
                            answer = 'Y'
                        else:
                            answer = input(f"\n      Create component '{suggested_component_name}' for untagged assets? [Y=yes, N=no, A=alter name]: ").strip().upper()
                        
                        component_name = suggested_component_name
                        if answer == 'N':
                            continue
                        elif answer == 'A' and not silent_mode:
                            component_name = input(f"      Enter custom component name: ").strip()
                            if not component_name:
                                continue
                        
                        component_to_create = {
                            "Status": None,
                            "Type": None,
                            "TeamNames": [],
                            "ComponentName": component_name
                        }
                        
                        try:
                            # Use first asset's source environment for untagged assets
                            source_env = next((asset['source_environment'] for asset in untagged_assets 
                                             if asset.get('name') in group), 'default-environment')
                            
                            create_custom_component(source_env, component_to_create, headers)
                            print(f"      ✅ Successfully created component: {component_name}")
                            
                            auto_created_components.append({
                                'environment_name': source_env,
                                'application_name': source_env,
                                'component_name': component_name,
                                'team_names': [],
                            'status': None,
                            'type': None,
                            'asset_count': len(group),
                            'asset_type': type,
                                'original_group_name': group[0],
                                'suggested_name': suggested_component_name,
                                'sample_assets': group[:5],
                                'grouping_method': 'name_based_fallback',
                                'tag_group': 'untagged'
                            })
                        except Exception as e:
                            print(f"      ❌ Failed to create component {component_name}: {str(e)}")
    
    print(f"\n🎯 TAG-BASED COMPONENT/SERVICE CREATION SUMMARY")
    print(f"   Total items created: {len(auto_created_components)}")
    if auto_created_components:
        print(f"   Asset types processed: {', '.join(set(comp['asset_type'] for comp in auto_created_components))}")
        tag_groups_used = set(comp.get('tag_group', 'N/A') for comp in auto_created_components)
        print(f"   Tag groups processed: {', '.join(tag_groups_used)}")
        applications_created = set(comp['application_name'] for comp in auto_created_components)
        print(f"   Applications affected: {len(applications_created)} ({', '.join(list(applications_created)[:3])}{'...' if len(applications_created) > 3 else ''})")
        
        # Show breakdown by assignment strategy
        components_count = len([comp for comp in auto_created_components if comp.get('assignment_strategy') == 'component'])
        services_count = len([comp for comp in auto_created_components if comp.get('assignment_strategy') == 'service'])
        print(f"   📦 Application Components: {components_count}")
        print(f"   🔧 Environment Services: {services_count}")
        
        # Show service type breakdown if any services were created
        if services_count > 0:
            service_types = [comp.get('service_type') for comp in auto_created_components if comp.get('service_type')]
            service_type_counts = {stype: service_types.count(stype) for stype in set(service_types)}
            for stype, count in service_type_counts.items():
                print(f"      - {stype} Services: {count}")
    
    # Handle full creation mode (same as name-based)
    if create_automatically_groups and auto_created_components:
        print(f"\n🏗️  FULL CREATION MODE - Preparing creation plan...")
        
        # Build creation plan from auto_created_components
        for component in auto_created_components:
            env_name = component.get('environment_name', 'Unknown')
            app_name = component.get('application_name', env_name)
            comp_name = component.get('component_name', 'Unknown')
            assignment_strategy = component.get('assignment_strategy', 'component')
            
            if assignment_strategy == 'service':
                # For services, we need environments
                if env_name not in creation_plan['environments']:
                    creation_plan['environments'][env_name] = {
                        'type': component.get('environment_subtype', 'CLOUD').upper(),
                        'team': component.get('team_names', ['auto-generated'])[0] if component.get('team_names') else 'auto-generated'
                    }
                
                # Add service
                service_key = f"{env_name}::{comp_name}"
                creation_plan['services'][service_key] = {
                    'name': comp_name,
                    'environment': env_name,
                    'service_type': component.get('service_type', 'Cloud'),
                    'asset_count': component.get('asset_count', 0)
                }
            else:
                # For components, we need applications
                if app_name not in creation_plan['applications']:
                    creation_plan['applications'][app_name] = {
                        'team': component.get('team_names', ['auto-generated'])[0] if component.get('team_names') else 'auto-generated'
                    }
                
                # Add component
                comp_key = f"{app_name}::{comp_name}"
                creation_plan['components'][comp_key] = {
                    'name': comp_name,
                    'application': app_name,
                    'asset_count': component.get('asset_count', 0)
                }
        
        # Show plan and get confirmation
        if show_creation_plan_and_confirm(creation_plan, silent_mode):
            print(f"\n🚀 EXECUTING FULL CREATION...")
            execute_full_creation_plan(creation_plan, headers)
        else:
            print(f"\n❌ Full creation cancelled. Only component/service creation was performed.")
    
    return auto_created_components


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


def create_component_rule(applicationName, componentName, filterName, filterValue, ruleName, headers2):
    global headers
    if not headers:
        headers = headers2
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
                # Success - no need to log to errors.log
                return True
                
            elif response.status_code == 409:
                print(f"└─ Rule already exists: {descriptive_rule_name}")
                if DEBUG:
                    print(f"   └─ Application: {applicationName}")
                    print(f"   └─ Component: {componentName}")
                    print(f"   └─ Filter: {json.dumps(rule['filter'], indent=2)}")
                # Rule already exists - this is not an error condition
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


def create_user_for_application(existing_users_emails, newly_created_users_emails, email, access_token2):
    global access_token
    if not access_token:
        access_token = access_token2
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


def api_call_create_user(email, first_name, last_name, role, access_token2):
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
    global access_token
    if not access_token:
        access_token = access_token2
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


def load_users_from_phoenix(access_token2):
    """
    Load all users from Phoenix with proper pagination and error handling.
    
    Args:
        access_token: API access token
        
    Returns:
        list: Complete list of all users across all pages
        
    Raises:
        requests.exceptions.RequestException: If there's an error fetching users
    """
    global access_token
    if not access_token:
        access_token = access_token2
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


def get_user_info(email, headers2):
    """
    Get user information from Phoenix.
    
    Args:
        email: User's email address
        headers: Request headers containing authorization
        
    Returns:
        dict: User information if found, None otherwise
    """
    global headers
    if not headers:
        headers = headers2
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

def create_user_with_role(email, first_name, last_name, role, headers2):
    """
    Create a user with a specific role.
    
    Args:
        email: User's email address
        first_name: User's first name
        last_name: User's last name
        role: User's role (SECURITY_CHAMPION, ENGINEERING_USER, APPLICATION_ADMIN, or ORG_USER)
        headers: Request headers containing authorization
    """
    global headers
    if not headers:
        headers = headers2
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
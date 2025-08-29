import base64
import requests
import json
import time
import Levenshtein
import random
import os
from datetime import datetime
from multipledispatch import dispatch

# Global tracking callback for main script reporting
component_tracking_callback = None

# Debug response saving
DEBUG_SAVE_RESPONSE = False
DEBUG_JSON_TO_SAVE = 10  # Default limit per operation type
DEBUG_RUN_ID = None  # Will be set when debug mode is enabled
DEBUG_DOMAIN_NAME = None  # Will be extracted from API domain
debug_response_counter = {}

def set_component_tracking_callback(callback_func):
    """Set the callback function for tracking component operations from the main script"""
    global component_tracking_callback
    component_tracking_callback = callback_func

def track_application_component_operations(callback_func):
    """Configure component tracking for the main script reporting"""
    set_component_tracking_callback(callback_func)

def extract_domain_name(api_domain):
    """
    Extract domain name from API URL for folder naming
    Examples:
    - api.bv.securityphoenix.cloud -> bv
    - api.demo.appsecphx.io -> demo
    - api.custom.phoenix.com -> custom
    - localhost:8080 -> localhost
    """
    try:
        # Remove protocol if present
        domain = api_domain.replace('https://', '').replace('http://', '')
        
        # Remove port if present
        domain = domain.split(':')[0]
        
        # Split by dots and look for the pattern api.{name}.{rest}
        parts = domain.split('.')
        if len(parts) >= 3 and parts[0] == 'api':
            return parts[1]  # Return the second part (domain name)
        elif len(parts) >= 2:
            return parts[0]  # Fallback to first part
        elif len(parts) == 1:
            return parts[0]  # Single domain like 'localhost'
        else:
            return 'unknown'
    except Exception:
        return 'unknown'

def initialize_debug_session(api_domain):
    """Initialize debug session with run ID and domain name"""
    global DEBUG_RUN_ID, DEBUG_DOMAIN_NAME
    
    # Generate run ID in yymmddhhmm format
    DEBUG_RUN_ID = datetime.now().strftime("%y%m%d%H%M")
    
    # Extract domain name
    DEBUG_DOMAIN_NAME = extract_domain_name(api_domain)
    
    print(f"🐛 Debug session initialized: {DEBUG_DOMAIN_NAME}_{DEBUG_RUN_ID}")

def save_debug_response(operation_type, response_data, request_data=None, endpoint=None, additional_info=None):
    """
    Save API response to a JSON file for debugging purposes
    
    Args:
        operation_type: Type of operation (deployment, component_creation, application_creation, team_fetch, team_creation)
        response_data: The response data to save
        request_data: Optional request data to include
        endpoint: Optional API endpoint information
        additional_info: Optional additional information to include in filename
    """
    if not DEBUG_SAVE_RESPONSE:
        return
        
    global debug_response_counter
    
    # Initialize counter for this operation type
    if operation_type not in debug_response_counter:
        debug_response_counter[operation_type] = 0
    
    # Check if we've reached the limit for this operation type (0 means unlimited)
    if DEBUG_JSON_TO_SAVE > 0 and debug_response_counter[operation_type] >= DEBUG_JSON_TO_SAVE:
        # Only show the limit message once per operation type
        if debug_response_counter[operation_type] == DEBUG_JSON_TO_SAVE:
            print(f"🐛 Reached limit of {DEBUG_JSON_TO_SAVE} saved responses for {operation_type}")
        return  # Skip saving if limit reached
    
    debug_response_counter[operation_type] += 1
    
    # Create run-specific debug directory if it doesn't exist
    if DEBUG_RUN_ID is None or DEBUG_DOMAIN_NAME is None:
        print("⚠️  Debug session not initialized - using default folder")
        debug_dir = "debug_responses"
    else:
        debug_dir = f"debug_responses/{DEBUG_DOMAIN_NAME}_{DEBUG_RUN_ID}"
    
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
        if DEBUG_RUN_ID and DEBUG_DOMAIN_NAME:
            print(f"📁 Created debug directory: {debug_dir}")
        else:
            print(f"📁 Created debug_responses directory")
    
    # Create filename with timestamp and counter
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if additional_info:
        filename = f"{operation_type}_{timestamp}_{debug_response_counter[operation_type]:03d}_{additional_info}.json"
    else:
        filename = f"{operation_type}_{timestamp}_{debug_response_counter[operation_type]:03d}.json"
    filepath = os.path.join(debug_dir, filename)
    
    # Prepare debug data
    debug_data = {
        "timestamp": datetime.now().isoformat(),
        "operation_type": operation_type,
        "endpoint": endpoint,
        "request_data": request_data,
        "response_data": response_data,
        "counter": debug_response_counter[operation_type]
    }
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"🐛 Saved {operation_type} response to: {filename}")
    except Exception as e:
        print(f"⚠️  Failed to save debug response for {operation_type}: {str(e)}")

def save_initial_cache_debug(env_name, env_id, env_services_cache):
    """
    Save initial environment services cache to debug folder for analysis.
    This helps debug cache consistency issues.
    """
    if not DEBUG_SAVE_RESPONSE:
        return
        
    try:
        # Use same debug directory structure as save_debug_response
        if DEBUG_RUN_ID is None or DEBUG_DOMAIN_NAME is None:
            debug_dir = "debug_responses"
        else:
            debug_dir = f"debug_responses/{DEBUG_DOMAIN_NAME}_{DEBUG_RUN_ID}"
        
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        
        # Generate timestamp and filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_env_name = env_name.lower().replace(' ', '_').replace('-', '_')
        filename = f"initial_cache_{safe_env_name}_{timestamp}_001.json"
        filepath = os.path.join(debug_dir, filename)
        
        # Prepare cache data for saving
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "operation_type": "initial_cache",
            "environment_name": env_name,
            "environment_id": env_id,
            "cache_size": len(env_services_cache),
            "services": {
                service_name: {
                    "id": service_data.get('id'),
                    "name": service_data.get('name'),
                    "applicationId": service_data.get('applicationId'),
                    "type": service_data.get('type', 'Unknown')
                }
                for service_name, service_data in env_services_cache.items()
            }
        }
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False, default=str)
            
        print(f"└─ 💾 Saved initial cache: {filename} ({len(env_services_cache)} services)")
        
    except Exception as e:
        print(f"⚠️  Failed to save initial cache debug: {e}")

def validate_initial_cache_completeness(env_name, env_id, env_services_cache, services_list):
    """
    Validate that the initial cache contains expected services and warn about potential issues.
    """
    if not DEBUG_SAVE_RESPONSE:
        return
        
    try:
        # Check if key services from configuration are missing from cache
        missing_services = []
        expected_services = [svc.get('Service', '') for svc in services_list if svc.get('Service')]
        
        for service_name in expected_services:
            if service_name.lower() not in env_services_cache:
                missing_services.append(service_name)
        
        if missing_services:
            print(f"\n⚠️  CACHE VALIDATION WARNING for {env_name}:")
            print(f"└─ {len(missing_services)} services from YAML config missing from initial cache")
            print(f"└─ This indicates cache was loaded before services were created")
            print(f"└─ Missing services: {missing_services[:10]}")
            if len(missing_services) > 10:
                print(f"└─ ... and {len(missing_services) - 10} more")
            print(f"└─ 🔄 Cache refresh mechanism will handle these during processing\n")
        else:
            print(f"✅ Cache validation passed: All {len(expected_services)} expected services found in initial cache")
            
    except Exception as e:
        print(f"⚠️  Cache validation failed: {e}")

def save_cache_refresh_debug(env_name, env_id, old_cache, services_processed, total_services):
    """
    Save cache refresh event for debugging cache consistency.
    """
    if not DEBUG_SAVE_RESPONSE:
        return
        
    try:
        # Use same debug directory structure
        if DEBUG_RUN_ID is None or DEBUG_DOMAIN_NAME is None:
            debug_dir = "debug_responses"
        else:
            debug_dir = f"debug_responses/{DEBUG_DOMAIN_NAME}_{DEBUG_RUN_ID}"
        
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        
        # Generate timestamp and filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_env_name = env_name.lower().replace(' ', '_').replace('-', '_')
        filename = f"cache_refresh_before_{safe_env_name}_{timestamp}_{services_processed:03d}.json"
        filepath = os.path.join(debug_dir, filename)
        
        # Prepare cache refresh data (before refresh)
        refresh_data = {
            "timestamp": datetime.now().isoformat(),
            "operation_type": "cache_refresh_before",
            "environment_name": env_name,
            "environment_id": env_id,
            "services_processed_in_cycle": services_processed,
            "total_services_processed": total_services,
            "old_cache_size": len(old_cache),
            "trigger": f"Every {services_processed} services",
            "quick_check_interval": services_processed,
            "old_cache_service_names": list(old_cache.keys())[:50],  # More service names for analysis
            "note": "Cache state before refresh - will be cleared and refetched with full pagination"
        }
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(refresh_data, f, indent=2, ensure_ascii=False, default=str)
            
        print(f"  └─ 💾 Saved cache refresh event: {filename}")
        
    except Exception as e:
        print(f"⚠️  Failed to save cache refresh debug: {e}")

def save_service_list_debug(env_name, env_id, services_list, total_services_count, env_services_cache):
    """
    Save service list from configuration to debug folder for analysis in YAML format.
    """
    if not DEBUG_SAVE_RESPONSE:
        return
        
    try:
        # Use same debug directory structure
        if DEBUG_RUN_ID is None or DEBUG_DOMAIN_NAME is None:
            debug_dir = "debug_responses"
        else:
            debug_dir = f"debug_responses/{DEBUG_DOMAIN_NAME}_{DEBUG_RUN_ID}"
        
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        
        # Generate timestamp and filename in YAML format
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"full-list-service_{timestamp}"
        filepath = os.path.join(debug_dir, filename)
        
        # Calculate missing services for accurate cache validation
        missing_services = []
        expected_services = [svc.get('Service', '') for svc in services_list if svc.get('Service')]
        
        for service_name in expected_services:
            if service_name.lower() not in env_services_cache:
                missing_services.append(service_name)
        
        # Create YAML-like content similar to the example file
        yaml_content = []
        yaml_content.append("")
        yaml_content.append("")
        
        if missing_services:
            yaml_content.append(f"⚠️  CACHE VALIDATION WARNING for {env_name}:")
            yaml_content.append(f"└─ {len(missing_services)} services from YAML config missing from initial cache")
            yaml_content.append(f"└─ This indicates cache was loaded before services were created")
            yaml_content.append(f"└─ Missing services: {missing_services[:10]}")
            if len(missing_services) > 10:
                yaml_content.append(f"└─ ... and {len(missing_services) - 10} more")
            yaml_content.append(f"└─ 🔄 Cache refresh mechanism will handle these during processing")
        else:
            yaml_content.append(f"✅ Cache validation passed: All {len(expected_services)} expected services found in initial cache")
        
        yaml_content.append("")
        yaml_content.append("└─ Services to process:")
        
        # Add service list in the same format as the example
        for i, service in enumerate(services_list, 1):
            service_name = service.get('Service', 'Unknown')
            service_type = service.get('Type', 'Unknown')
            deployment_set = service.get('Deployment_set', 'None')
            yaml_content.append(f"   {i:2d}. {service_name} (Type: {service_type}, Deployment_set: {deployment_set})")
        
        yaml_content.append("")
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(yaml_content))
            
        print(f"└─ 💾 Saved service list debug: {filename} ({len(services_list)} services)")
        
    except Exception as e:
        print(f"⚠️  Failed to save service list debug: {e}")

def save_component_list_debug(applications, total_components_count):
    """
    Save component list from applications to debug folder for analysis.
    """
    if not DEBUG_SAVE_RESPONSE:
        return
        
    try:
        # Use same debug directory structure
        if DEBUG_RUN_ID is None or DEBUG_DOMAIN_NAME is None:
            debug_dir = "debug_responses"
        else:
            debug_dir = f"debug_responses/{DEBUG_DOMAIN_NAME}_{DEBUG_RUN_ID}"
        
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        
        # Generate timestamp and filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"component_list_{timestamp}_001.json"
        filepath = os.path.join(debug_dir, filename)
        
        # Prepare component list data
        component_list_data = {
            "timestamp": datetime.now().isoformat(),
            "operation_type": "component_list_debug",
            "total_applications": len(applications),
            "total_components_count": total_components_count,
            "applications": []
        }
        
        # Add detailed component information
        global_component_index = 0
        for app_index, app in enumerate(applications, 1):
            app_info = {
                "app_index": app_index,
                "app_name": app.get('AppName', 'Unknown'),
                "components_count": len(app.get('Components', [])),
                "components": []
            }
            
            if app.get('Components'):
                for comp_index, component in enumerate(app['Components'], 1):
                    global_component_index += 1
                    component_info = {
                        "component_index_in_app": comp_index,
                        "global_component_index": global_component_index,
                        "component_name": component.get('ComponentName', 'Unknown'),
                        "component_type": component.get('Type', 'Unknown'),
                        "repositories": component.get('Repositories', []),
                        "raw_data": component
                    }
                    app_info["components"].append(component_info)
            
            component_list_data["applications"].append(app_info)
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(component_list_data, f, indent=2, ensure_ascii=False, default=str)
            
        print(f"└─ 💾 Saved component list debug: {filename} ({total_components_count} components)")
        
    except Exception as e:
        print(f"⚠️  Failed to save component list debug: {e}")

def save_comprehensive_cache_debug(env_name, env_id, env_services_cache, application_environments, phoenix_components, applications=None, services_list=None):
    """
    Save comprehensive cache state including all services, components, applications, and environments.
    """
    if not DEBUG_SAVE_RESPONSE:
        return
        
    try:
        # Use same debug directory structure
        if DEBUG_RUN_ID is None or DEBUG_DOMAIN_NAME is None:
            debug_dir = "debug_responses"
        else:
            debug_dir = f"debug_responses/{DEBUG_DOMAIN_NAME}_{DEBUG_RUN_ID}"
        
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
        
        # Generate timestamp and filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive-cache-state_{timestamp}"
        filepath = os.path.join(debug_dir, filename)
        
        # Create comprehensive cache content
        cache_content = []
        cache_content.append("")
        cache_content.append("=== COMPREHENSIVE CACHE STATE DEBUG ===")
        cache_content.append(f"Timestamp: {datetime.now().isoformat()}")
        cache_content.append(f"Environment: {env_name} (ID: {env_id})")
        cache_content.append("")
        
        # SECTION 1: ENVIRONMENT CACHE SUMMARY
        cache_content.append("📦 ENVIRONMENT CACHE SUMMARY:")
        cache_content.append(f"└─ Environment: {env_name}")
        cache_content.append(f"└─ Environment ID: {env_id}")
        cache_content.append(f"└─ Cached Services Count: {len(env_services_cache)}")
        cache_content.append("")
        
        # SECTION 2: ALL ENVIRONMENTS IN SYSTEM
        environments = [env for env in application_environments if env.get('type') == 'ENVIRONMENT']
        applications_list = [env for env in application_environments if env.get('type') == 'APPLICATION']
        
        cache_content.append(f"🏗️  ALL ENVIRONMENTS IN SYSTEM ({len(environments)} total):")
        for i, env in enumerate(environments, 1):
            env_name_display = env.get('name', 'Unknown')
            env_id_display = env.get('id', 'Unknown')
            cache_content.append(f"   {i:2d}. {env_name_display} (ID: {env_id_display})")
        cache_content.append("")
        
        # SECTION 3: ALL APPLICATIONS IN SYSTEM
        cache_content.append(f"📱 ALL APPLICATIONS IN SYSTEM ({len(applications_list)} total):")
        for i, app in enumerate(applications_list, 1):
            app_name_display = app.get('name', 'Unknown')
            app_id_display = app.get('id', 'Unknown')
            cache_content.append(f"   {i:2d}. {app_name_display} (ID: {app_id_display})")
        cache_content.append("")
        
        # SECTION 4: ALL SERVICES IN CURRENT ENVIRONMENT CACHE
        cache_content.append(f"⚙️  CACHED SERVICES IN {env_name} ({len(env_services_cache)} total):")
        for i, (service_name_lower, service_data) in enumerate(env_services_cache.items(), 1):
            service_id = service_data.get('id', 'Unknown')
            service_name = service_data.get('name', service_name_lower)
            cache_content.append(f"   {i:3d}. {service_name} (ID: {service_id})")
        cache_content.append("")
        
        # SECTION 5: ALL COMPONENTS IN SYSTEM
        cache_content.append(f"🔧 ALL COMPONENTS IN SYSTEM ({len(phoenix_components)} total):")
        for i, component in enumerate(phoenix_components, 1):
            comp_name = component.get('name', 'Unknown')
            comp_id = component.get('id', 'Unknown')
            comp_app_id = component.get('applicationId', 'Unknown')
            cache_content.append(f"   {i:4d}. {comp_name} (ID: {comp_id}, App: {comp_app_id})")
        cache_content.append("")
        
        # SECTION 6: SERVICES FROM YAML CONFIGURATION (if provided)
        if services_list:
            cache_content.append(f"📋 SERVICES FROM YAML CONFIG ({len(services_list)} total):")
            for i, service in enumerate(services_list, 1):
                service_name = service.get('Service', 'Unknown')
                service_type = service.get('Type', 'Unknown')
                deployment_set = service.get('Deployment_set', 'None')
                cache_content.append(f"   {i:3d}. {service_name} (Type: {service_type}, Deployment_set: {deployment_set})")
            cache_content.append("")
        
        # SECTION 7: APPLICATIONS FROM YAML CONFIGURATION (if provided)
        if applications:
            total_components = sum(len(app.get('Components', [])) for app in applications)
            cache_content.append(f"📱 APPLICATIONS FROM YAML CONFIG ({len(applications)} apps, {total_components} components total):")
            for i, app in enumerate(applications, 1):
                app_name = app.get('AppName', 'Unknown')
                components_count = len(app.get('Components', []))
                cache_content.append(f"   {i:2d}. {app_name} ({components_count} components)")
                if app.get('Components'):
                    for j, component in enumerate(app['Components'], 1):
                        comp_name = component.get('ComponentName', 'Unknown')
                        cache_content.append(f"       {j:2d}. {comp_name}")
            cache_content.append("")
        
        # SECTION 8: CACHE VALIDATION
        if services_list:
            missing_services = []
            expected_services = [svc.get('Service', '') for svc in services_list if svc.get('Service')]
            
            for service_name in expected_services:
                if service_name.lower() not in env_services_cache:
                    missing_services.append(service_name)
            
            cache_content.append("🔍 CACHE VALIDATION RESULTS:")
            if missing_services:
                cache_content.append(f"└─ ⚠️  {len(missing_services)} services from YAML missing from cache:")
                for i, missing_svc in enumerate(missing_services[:20], 1):
                    cache_content.append(f"   {i:2d}. {missing_svc}")
                if len(missing_services) > 20:
                    cache_content.append(f"   ... and {len(missing_services) - 20} more")
            else:
                cache_content.append(f"└─ ✅ All {len(expected_services)} expected services found in cache")
            cache_content.append("")
        
        cache_content.append("=== END COMPREHENSIVE CACHE STATE ===")
        cache_content.append("")
        
        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(cache_content))
            
        print(f"└─ 💾 Saved comprehensive cache debug: {filename}")
        
    except Exception as e:
        print(f"⚠️  Failed to save comprehensive cache debug: {e}")

from providers.Utils import group_repos_by_subdomain, calculate_criticality, extract_user_name_from_email, validate_user_role
import logging

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
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
access_token = None
headers = {}

# Global cache for components to reduce API calls in quick-check mode
_component_cache = {
    'data': None,
    'timestamp': None,
    'ttl': 300  # 5 minutes cache TTL
}

# Global cache for environment services to optimize service creation
_environment_services_cache = {
    'data': {},  # env_id -> {service_name_lower: service_data}
    'timestamp': {},  # env_id -> timestamp
    'ttl': 300  # 5 minutes cache TTL
}

# Global cache for applications and components verification
_application_verification_cache = {
    'applications': {},  # app_name -> app_data
    'components': {},    # (app_name, component_name) -> component_data
    'timestamp': None,
    'ttl': 300  # 5 minutes cache TTL
}

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
        return True
    except requests.exceptions.RequestException as e:
        # Handle 409 conflicts gracefully (environment already exists)
        if hasattr(response, 'status_code') and response.status_code == 409:
            response_content = getattr(response, 'content', b'').decode() if hasattr(response, 'content') else ''
            if 'must be unique' in response_content or 'already exists' in response_content:
                print(f"└─ Environment '{environment['Name']}' already exists (409 Conflict)")
                print(f"└─ This is expected behavior - environment will be used as-is")
                print(f"└─ Continuing with service creation...")
                return True  # Return success for existing environments
        
        # Handle other errors
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
        
        # For non-409 errors, re-raise to ensure proper error handling
        if not (hasattr(response, 'status_code') and response.status_code == 409):
            raise e
        return False


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
def add_environment_services(repos, subdomains, environments, application_environments, phoenix_components, subdomain_owners, teams, access_token2, track_operation_callback=None, quick_check_interval=10, silent_mode=False):
    global access_token
    if not access_token:
        access_token = access_token2
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}

    print(f"\n[Service Creation Process Started]")
    print(f"└─ Processing {len(environments)} environments")
    
    # Count total services across all environments
    total_services_count = 0
    for env in environments:
        if env.get('Services'):
            total_services_count += len(env['Services'])
    
    print(f"└─ Total services to process: {total_services_count}")
    
    # Environment counter
    current_environment = 0
    
    # Quick-check mode information
    if silent_mode:
        print(f"└─ 🔇 Silent mode enabled: Service validation suppressed during processing")
    elif quick_check_interval > 1:
        print(f"└─ ⚡ Quick-check mode enabled: Validating every {quick_check_interval} services")
    else:
        print(f"└─ 🔍 Full validation mode: Validating every service")
    
    total_services_processed = 0
    services_pending_validation = []
    
    for environment in environments:
        current_environment += 1
        env_name = environment['Name']
        env_id = get_environment_id(application_environments, env_name)
        if not env_id:
            print(f"[Services] Environment {current_environment}/{len(environments)}: {env_name} doesn't have ID! Skipping service and rule creation")
            continue
        print(f"\n[Services] Environment {current_environment}/{len(environments)}: {env_name} (ID: {env_id})")
        
        if not environment.get('Services'):
            print(f"└─ No services defined for environment {env_name}")
            continue
            
        services_list = environment['Services']
        print(f"└─ Found {len(services_list)} services to process in {env_name}")
        
        # OPTIMIZATION: Pre-load all services for this environment into cache
        print(f"└─ Pre-loading services cache for environment {env_name}...")
        env_services_cache = get_environment_services_cached(env_id, headers)
        print(f"└─ Environment cache loaded with {len(env_services_cache)} existing services")
        
        # DEBUGGING: Save initial cache to debug folder
        save_initial_cache_debug(env_name, env_id, env_services_cache)
        
        # DEBUGGING: Save service list from configuration  
        save_service_list_debug(env_name, env_id, services_list, total_services_count, env_services_cache)
        
        # DEBUGGING: Save comprehensive cache state with all entities
        save_comprehensive_cache_debug(env_name, env_id, env_services_cache, application_environments, phoenix_components, services_list=services_list)
        
        # VALIDATION: Check for known missing services that should be in cache
        validate_initial_cache_completeness(env_name, env_id, env_services_cache, services_list)
        
        # Initialize cache refresh counter for this environment
        cache_refresh_counter = 0
        
        # Log all services that will be processed
        print(f"└─ Services to process:")
        for i, svc in enumerate(services_list, 1):
            svc_name = svc.get('Service', 'Unknown')
            svc_type = svc.get('Type', 'Unknown')
            svc_deployment_set = svc.get('Deployment_set', 'None')
            print(f"   {i:2d}. {svc_name} (Type: {svc_type}, Deployment_set: {svc_deployment_set})")

        for service in environment['Services']:
                team_name = service.get('TeamName', None)
                service_name = service['Service']
                service_type = service.get('Type', 'Unknown')
                deployment_set = service.get('Deployment_set', 'None')
                
                total_services_processed += 1
                cache_refresh_counter += 1
                
                # CACHE REFRESH: Only refresh cache every quick_check_interval services to reduce API calls
                if cache_refresh_counter >= quick_check_interval:
                    if not silent_mode:
                        print(f"\n  🔄 Cache refresh cycle reached ({cache_refresh_counter} services in {env_name})")
                        print(f"  └─ Refreshing environment cache to include newly created services...")
                    
                    # Save cache refresh event for debugging
                    save_cache_refresh_debug(env_name, env_id, env_services_cache, cache_refresh_counter, total_services_processed)
                    
                    # Store old cache size for comparison
                    old_cache_size = len(env_services_cache)
                    
                    # OPTIMIZATION: Force fresh fetch with full pagination to get complete dataset
                    env_services_cache = get_environment_services_cached(env_id, headers, force_refresh=True)  # Force refresh with global cache clear
                    cache_refresh_counter = 0  # Reset counter
                    
                    new_cache_size = len(env_services_cache)
                    services_added = new_cache_size - old_cache_size
                    
                    if not silent_mode:
                        if services_added > 0:
                            print(f"  └─ ✅ Cache refreshed: {old_cache_size} → {new_cache_size} services (+{services_added} new)")
                        else:
                            print(f"  └─ ✅ Cache refreshed with {new_cache_size} services (no changes)")
                
                if not silent_mode:
                    print(f"\n  [Processing Service {total_services_processed}/{total_services_count}: {service_name}]")
                    print(f"  └─ Type: {service_type}")
                    print(f"  └─ Team: {team_name}")
                    print(f"  └─ Deployment Set: {deployment_set}")
                    print(f"  └─ Environment: {env_name} (ID: {env_id})")
                
                # Store service info for potential validation
                service_info = {
                    'service': service,
                    'service_name': service_name,
                    'env_name': env_name,
                    'env_id': env_id,
                    'count': total_services_processed
                }
                services_pending_validation.append(service_info)
                
                # OPTIMIZATION: Use cache lookup instead of API call
                if not silent_mode:
                    print(f"  └─ Checking if service already exists in cache...")
                
                exists, service_data = service_exists_in_cache(service_name, env_id, env_services_cache, headers, fallback_check=True)
                service_id = service_data.get('id') if service_data else None
                
                if not exists:
                    if not silent_mode and DEBUG:
                        print(f"  └─ 🔍 Cache miss: {service_name} not found in {len(env_services_cache)} cached services")
                    if not silent_mode:
                        print(f"  └─ ❌ Service does not exist, attempting to create...")
                        print(f"  └─ Service details for creation:")
                        print(f"     └─ Name: {service_name}")
                        print(f"     └─ Type: {service_type}")
                        print(f"     └─ Tier: {service.get('Tier', 'Unknown')}")
                        print(f"     └─ Team: {team_name}")
                        print(f"     └─ Environment: {env_name} (ID: {env_id})")
                    elif total_services_processed % 50 == 0:  # Progress indicator in silent mode
                        print(f"  🔄 Processed {total_services_processed} services...")
                    
                    creation_success = False
                    service_id = None
                    try:
                        if team_name:
                            if not silent_mode:
                                print(f"  └─ Creating service with team: {team_name}")
                            creation_success, service_id = add_service(env_name, env_id, service, service['Tier'], team_name, headers)
                        else:
                            if not silent_mode:
                                print(f"  └─ Creating service without team")
                            creation_success, service_id = add_service(env_name, env_id, service, service['Tier'], headers)
                        
                        if not silent_mode:
                            if creation_success:
                                print(f"  └─ ✅ Service {service_name} created successfully (ID: {service_id})")
                            else:
                                print(f"  └─ ❌ Service {service_name} creation failed (returned False)")
                        
                        # Track service creation operation
                        if track_operation_callback:
                            if creation_success:
                                track_operation_callback('services', 'create_service', f"{service_name} ({env_name})", True)
                            else:
                                track_operation_callback('services', 'create_service', f"{service_name} ({env_name})", False, "Service creation failed")
                                
                    except NotImplementedError as e:
                        error_msg = f"NotImplementedError creating service {service_name}: {e}"
                        if not silent_mode:
                            print(f"  └─ ❌ {error_msg}")
                        if track_operation_callback:
                            track_operation_callback('services', 'create_service', f"{service_name} ({env_name})", False, str(e))
                        continue
                    except Exception as e:
                        error_msg = f"Unexpected error creating service {service_name}: {e}"
                        if not silent_mode:
                            print(f"  └─ ❌ {error_msg}")
                        if track_operation_callback:
                            track_operation_callback('services', 'create_service', f"{service_name} ({env_name})", False, str(e))
                        continue
                        
                    if not creation_success:
                        if not silent_mode:
                            print(f"  └─ ❌ Failed to create service {service_name}, skipping rule creation")
                        continue
                else:
                    if not silent_mode:
                        print(f"  └─ ✅ Service already exists (ID: {service_id})")
                
                # OPTIMIZATION: Add created service to cache, but don't force full cache refresh
                if not exists and creation_success:  # Service was just created
                    # Add to local cache only (lightweight update)
                    new_service_data = {
                        'id': service_id,
                        'name': service_name,
                        'applicationId': env_id
                    }
                    # Update only the local env_services_cache for immediate lookup
                    env_services_cache[service_name.lower()] = new_service_data
                    exists = True  # Update status for rule creation logic
                    if not silent_mode and DEBUG:
                        print(f"  └─ ✅ Added {service_name} to local cache")
                
                # At this point, service exists (either created or was already there)
                if not silent_mode:
                    print(f"  └─ Service {service_name} verified, updating service and rules...")
                
                # OPTIMIZATION: Only update service and rules if we have a valid service_id
                if service_id and exists:
                    update_service(service, service_id, headers)
                    if track_operation_callback:
                        track_operation_callback('services', 'update_service', f"{service_name} ({env_name})", True)
                    
                    # Always update rules if service exists and is verified
                    add_service_rule_batch(application_environments, environment, service, service_id, headers)
                
                if not silent_mode:
                    time.sleep(1)  # Add small delay between operations in verbose mode

    # Final validation phase for silent mode or quick-check mode
    if silent_mode or quick_check_interval > 1:
        print(f"\n[Final Validation Phase]")
        print(f"└─ Validating {len(services_pending_validation)} services that were processed...")
        
        validation_success = 0
        validation_failed = 0
        
        for service_info in services_pending_validation:
            service_name = service_info['service_name']
            env_name = service_info['env_name']
            env_id = service_info['env_id']
            
            exists, service_id = verify_service_exists(env_name, env_id, service_name, headers)
            if exists:
                validation_success += 1
            else:
                validation_failed += 1
                if not silent_mode:  # Only show details if not in silent mode
                    print(f"   ❌ Service {service_name} in {env_name} - validation failed")
        
        print(f"└─ Final validation results:")
        print(f"   ✅ Successfully validated: {validation_success} services")
        if validation_failed > 0:
            print(f"   ❌ Failed validation: {validation_failed} services")
        print(f"   📊 Success rate: {(validation_success/(validation_success+validation_failed)*100):.1f}%")

    print(f"\n[Service Creation Process Completed]")
    print(f"└─ Finished processing {total_services_processed} services across all environments")


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
    
    # Count total components across all applications
    total_components_count = 0
    for app in applications:
        if app.get('Components'):
            total_components_count += len(app['Components'])
    
    print(f'└─ Total components to process: {total_components_count}')
    
    # DEBUGGING: Save component list from configuration
    save_component_list_debug(applications, total_components_count)
    
    # DEBUGGING: Save comprehensive cache state for applications and components
    # Note: We'll call this when we have an environment context
    
    # Debug: Show existing applications
    existing_apps = [env for env in application_environments if env.get('type') == "APPLICATION"]
    print(f'└─ Found {len(existing_apps)} existing applications in Phoenix:')
    for app in existing_apps:
        print(f'   └─ {app.get("name", "Unknown")}')
    
    # PHASE 2 OPTIMIZATION: Track applications for batch verification
    created_applications = []
    updated_applications = []
    
    # Component processing counter
    global_component_processed = 0
    
    # Application processing counter
    current_application = 0
    
    for application in applications:
        current_application += 1
        app_name = application['AppName']
        print(f'\n└─ Processing application {current_application}/{len(applications)}: {app_name}')
        
        # Check if application exists
        existing_app = next((env for env in application_environments if env['name'] == app_name and env['type'] == "APPLICATION"), None)
        
        if not existing_app:
            print(f'   └─ Application does not exist, creating...')
            create_application(application, headers)
            created_applications.append(application)
        else:
            print(f'   └─ Application exists (ID: {existing_app.get("id", "Unknown")}), updating...')
            try:
                update_application(application, application_environments, phoenix_components, headers)
                updated_applications.append(application)
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
    
    # PHASE 2 OPTIMIZATION: Batch verify created applications
    if created_applications:
        print(f'\n[Batch Verification Phase]')
        try:
            verification_results = verify_application_creation_batch(created_applications, headers)
            
            failed_apps = verification_results.get('failed', [])
            if failed_apps:
                print(f'└─ ⚠️  {len(failed_apps)} applications failed verification:')
                for app in failed_apps:
                    print(f'   └─ ❌ {app.get("AppName", "Unknown")}')
            else:
                print(f'└─ ✅ All {len(created_applications)} created applications verified successfully')
        
        except Exception as e:
            print(f'└─ ⚠️  Batch verification failed: {e}')
            print(f'└─ Individual verification may be needed')

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
        
        # Save debug response if enabled
        response_data = response.json() if response.content else {"status": "created", "message": "Application created successfully"}
        save_debug_response(
            operation_type="application_creation",
            response_data=response_data,
            request_data=payload,
            endpoint="/v1/applications"
        )
        
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
            global_component_processed += 1
            create_custom_component(app['AppName'], component, headers, global_component_processed, total_components_count)

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

def create_custom_component(applicationName, component, headers2, component_number=None, total_components=None):
    global headers
    if not headers:
        headers = headers2
    print(f"\n[Component Creation]")
    if component_number and total_components:
        print(f"└─ Processing Component {component_number}/{total_components}: {component['ComponentName']}")
    else:
        print(f"└─ Component: {component['ComponentName']}")
    print(f"└─ Application: {applicationName}")
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
        
        # Save debug response if enabled
        response_data = response.json() if response.content else {"status": "created", "message": "Component created successfully"}
        save_debug_response(
            operation_type="component_creation",
            response_data=response_data,
            request_data=payload,
            endpoint="/v1/components"
        )
        
        # Track successful component creation for main script reporting
        if component_tracking_callback:
            component_tracking_callback('components', 'create_component', f"{applicationName} -> {component['ComponentName']}", True)
        
        time.sleep(2)
    except requests.exceptions.RequestException as e:
        if response.status_code == 409:
            # Component name conflict - determine if it's a legitimate duplicate or cross-application naming
            print(f"└─ Component name '{component['ComponentName']}' conflicts with existing component - analyzing...")
            
            try:
                # Check if component exists in the TARGET application (legitimate duplicate)
                print(f"└─ Checking if component exists in target application '{applicationName}'...")
                
                # Get all components for verification
                all_components = get_phoenix_components_lazy(headers)
                
                # Get applications to map names to IDs
                print(f"└─ Getting application list to resolve application ID...")
                app_list_response = requests.get(construct_api_url("/v1/applications"), headers=headers)
                applications = app_list_response.json().get('content', []) if app_list_response.status_code == 200 else []
                
                # Find target application ID by name
                target_app_id = None
                for app in applications:
                    if app.get('name', '').lower() == applicationName.lower():
                        target_app_id = app.get('id')
                        print(f"└─ Found target application ID: {target_app_id}")
                        break
                
                if not target_app_id:
                    print(f"└─ ⚠️ Could not find application ID for '{applicationName}'")
                    print(f"└─ Assuming cross-application conflict")
                
                # Find all components with the same name
                matching_components = []
                for comp in all_components:
                    if comp.get('name', '').lower() == component['ComponentName'].lower():
                        matching_components.append(comp)
                        print(f"└─ Found component '{comp['name']}' in application ID: {comp.get('applicationId')}")
                
                # Check if any exist in our target application
                same_app_components = [comp for comp in matching_components if comp.get('applicationId') == target_app_id]
                
                if same_app_components:
                    # COMPONENT UPDATE: Component exists in same application - check if rules can be updated
                    existing_component = same_app_components[0]
                    print(f"└─ ✓ COMPONENT UPDATE: Component '{component['ComponentName']}' already exists in target application '{applicationName}'")
                    print(f"└─ ✓ Business rule: Check if rules can be updated for existing component")
                    print(f"└─ ✓ Using existing component for rule updates (ID: {existing_component.get('id')})")
                    
                    if component_tracking_callback:
                        component_tracking_callback('components', 'component_update', f"{applicationName} -> {component['ComponentName']}", True)
                    return
                    
                elif matching_components:
                    # Component exists in DIFFERENT application - this should be allowed
                    print(f"└─ Component '{component['ComponentName']}' exists in different application(s)")
                    print(f"└─ This is allowed - components can have same name across applications")
                    
                    # Use application-specific naming to avoid global conflicts
                    unique_component_name = f"{component['ComponentName']}-{applicationName.lower()}"
                    print(f"└─ Creating component with application-specific name: {unique_component_name}")
                    
                    # Update payload and retry
                    payload["name"] = unique_component_name
                    print(f"└─ Retrying with unique name: {unique_component_name}")
                    
                    retry_response = requests.post(api_url, headers=headers, json=payload)
                    if retry_response.status_code in [200, 201]:
                        print(f"└─ ✅ Created application-specific component: {unique_component_name}")
                        if component_tracking_callback:
                            component_tracking_callback('components', 'create_component_unique', f"{applicationName} -> {unique_component_name}", True)
                        return
                    elif retry_response.status_code == 409:
                        print(f"└─ Application-specific component already exists: {unique_component_name}")
                        if component_tracking_callback:
                            component_tracking_callback('components', 'component_exists', f"{applicationName} -> {unique_component_name}", True)
                        return
                    else:
                        print(f"└─ Failed to create application-specific component: {retry_response.status_code}")
                        
            except Exception as analysis_error:
                print(f"└─ Error analyzing component conflict: {analysis_error}")
                print(f"└─ Treating as existing component")
                
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
        # PHASE 1 OPTIMIZATION: Use batch rule creation
        rule_batch = RuleBatch(applicationName, component['ComponentName'])
        
        # Collect rules first for verification
        collected_rules = []
        create_component_rules_batch(applicationName, component, headers)
        
        # PHASE 2 OPTIMIZATION: Verify rules were created correctly
        if rule_batch.rules:
            try:
                verification_results = verify_rules_creation_batch(
                    applicationName, 
                    component['ComponentName'], 
                    rule_batch.rules, 
                    headers
                )
                
                failed_rules = verification_results.get('failed', [])
                if failed_rules:
                    print(f"└─ ⚠️  {len(failed_rules)} rules failed verification")
                else:
                    print(f"└─ ✅ All rules verified successfully")
                    
            except Exception as verify_error:
                print(f"└─ ⚠️  Rule verification failed: {verify_error}")
        
    except Exception as e:
        error_msg = f"Failed to create component rules: {str(e)}"
        log_error(
            'Component Rules Creation',
            f"{applicationName} -> {component['ComponentName']}",
            'N/A',
            error_msg
        )
        print(f"└─ Warning: {error_msg}")
        
        # Fallback to original individual rule creation
        try:
            print(f"└─ 🔄 Falling back to individual rule creation...")
            create_component_rules(applicationName, component, headers)
        except Exception as fallback_error:
            print(f"└─ ❌ Fallback also failed: {fallback_error}")


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
                global_component_processed += 1
                existing_component = next((comp for comp in existing_components 
                                        if comp['name'] == component['ComponentName'] 
                                        and comp['applicationId'] == existing_app['id']), None)
                if existing_component:
                    print(f"   └─ Updating component {global_component_processed}/{total_components_count}: {component['ComponentName']}")
                    update_component(application, component, existing_component, headers)
                else:
                    print(f"   └─ Creating new component {global_component_processed}/{total_components_count}: {component['ComponentName']}")
                    create_custom_component(application['AppName'], component, headers, global_component_processed, total_components_count)
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
        # PHASE 1 OPTIMIZATION: Use batch rule creation
        try:
            create_component_rules_batch(application['AppName'], component, headers)
        except Exception as e:
            print(f"└─ ⚠️  Batch rule creation failed, using fallback: {e}")
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
                response_data = response.json()
                team['id'] = response_data['id']
                new_pteams.append(response_data)
                print(f"└─ Team created successfully: {team_name}")
                
                # Save debug response if enabled
                save_debug_response(
                    operation_type="team_creation",
                    response_data=response_data,
                    request_data=payload,
                    endpoint="/v1/teams"
                )
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
        
        response_data = response.json()
        teams_content = response_data.get('content', [])
        
        # Save debug response if enabled
        save_debug_response(
            operation_type="team_fetch",
            response_data=response_data,
            request_data=None,  # GET request has no body
            endpoint="/v1/teams"
        )
        
        # Return the content of the response (team list)
        return teams_content
    
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
    """
    Legacy function that converts access token to headers format.
    Now redirects to the enhanced pagination implementation.
    """
    global access_token
    if not access_token:
        access_token = access_token2
    headers = {'Authorization': f"Bearer {access_token}", 'Content-Type': 'application/json'}
    return get_phoenix_components(headers)


def _is_cache_valid():
    """Check if the component cache is still valid"""
    import time
    return (_component_cache['data'] is not None and 
            _component_cache['timestamp'] is not None and 
            time.time() - _component_cache['timestamp'] < _component_cache['ttl'])

def _update_component_cache(components):
    """Update the component cache with new data"""
    import time
    _component_cache['data'] = components
    _component_cache['timestamp'] = time.time()

def clear_component_cache():
    """Clear the component cache to force fresh data on next fetch"""
    _component_cache['data'] = None
    _component_cache['timestamp'] = None
    print("🗑️  Component cache cleared - next fetch will retrieve fresh data")

def force_fresh_component_fetch(headers):
    """
    Force a fresh fetch of all components, bypassing cache.
    Useful for testing the pagination improvements.
    """
    clear_component_cache()
    print("\n🔄 Forcing fresh component fetch...")
    return get_phoenix_components(headers)

def validate_service_dataset_completeness(headers):
    """
    Validate that service fetching and caching is working with complete dataset.
    Returns statistics about the services and environments.
    """
    print("\n📊 Validating Service Dataset Completeness...")
    
    # Force fresh fetch to get latest data
    all_components = force_fresh_component_fetch(headers)
    
    # Analyze the dataset
    env_breakdown = {}
    total_services = len(all_components)
    
    for service in all_components:
        app_id = service.get('applicationId', 'Unknown')
        env_breakdown[app_id] = env_breakdown.get(app_id, 0) + 1
    
    print(f"✅ Total services in system: {total_services}")
    print(f"✅ Number of environments: {len(env_breakdown)}")
    print(f"✅ Top 10 environments by service count:")
    
    for i, (app_id, count) in enumerate(sorted(env_breakdown.items(), key=lambda x: x[1], reverse=True)[:10], 1):
        print(f"   {i:2d}. Environment {app_id}: {count} services")
    
    return {
        'total_services': total_services,
        'environments': len(env_breakdown),
        'env_breakdown': env_breakdown,
        'all_services': all_components
    }

def test_environment_filtering(env_id, headers):
    """
    Test environment filtering to ensure it's working correctly.
    
    Args:
        env_id: Environment ID to test
        headers: Authentication headers
        
    Returns:
        dict: Test results
    """
    print(f"\n🧪 Testing Environment Filtering for ID: {env_id}")
    
    # Get all services
    all_services = get_phoenix_components_lazy(headers)
    print(f" * Total services in system: {len(all_services)}")
    
    # Filter by environment using our function
    env_services = get_phoenix_components_in_environment(env_id, headers)
    print(f" * Services in environment {env_id}: {len(env_services)}")
    
    # Validate filtering
    invalid_services = [s for s in env_services if s.get('applicationId') != env_id]
    if invalid_services:
        print(f" ❌ FILTERING ERROR: {len(invalid_services)} services have wrong environment ID!")
        for svc in invalid_services[:3]:
            print(f"   └─ {svc.get('name')} has applicationId: {svc.get('applicationId')}")
    else:
        print(f" ✅ Environment filtering working correctly")
    
    # Test double filtering (should yield same result)
    double_filtered = [s for s in all_services if s.get('applicationId') == env_id]
    if len(double_filtered) == len(env_services):
        print(f" ✅ Consistent filtering results")
    else:
        print(f" ❌ Inconsistent filtering: {len(double_filtered)} vs {len(env_services)}")
    
    return {
        'env_id': env_id,
        'total_services': len(all_services),
        'env_services_count': len(env_services),
        'filtering_errors': len(invalid_services),
        'consistent_filtering': len(double_filtered) == len(env_services)
    }

def analyze_service_locations(service_name, headers):
    """
    Analyze where a service exists across environments and applications.
    
    Args:
        service_name: Name of the service to analyze
        headers: Authentication headers
        
    Returns:
        dict: Analysis results showing all locations
    """
    print(f"\n🔍 Analyzing Service Locations for: {service_name}")
    
    all_services = get_phoenix_components_lazy(headers)
    service_name_lower = service_name.lower()
    
    # Find all instances of this service
    matching_services = [s for s in all_services if s['name'].lower() == service_name_lower]
    
    if not matching_services:
        print(f" ❌ Service '{service_name}' not found anywhere in the system")
        return {'found': False, 'locations': []}
    
    print(f" ✅ Found {len(matching_services)} instance(s) of service '{service_name}':")
    
    locations = []
    for i, svc in enumerate(matching_services, 1):
        app_id = svc.get('applicationId', 'Unknown')
        svc_id = svc.get('id', 'Unknown')
        
        # Determine if this looks like an environment or application
        if len(app_id) > 30 and app_id.count('-') >= 4:
            location_type = "Environment"
        else:
            location_type = "Application"
        
        location_info = {
            'service_id': svc_id,
            'location_id': app_id,
            'location_type': location_type,
            'service_name': svc.get('name')
        }
        locations.append(location_info)
        
        print(f"   {i}. {location_type}: {app_id}")
        print(f"      └─ Service ID: {svc_id}")
        print(f"      └─ Service Name: {svc.get('name')}")
    
    # Categorize by type
    environments = [loc for loc in locations if loc['location_type'] == 'Environment']
    applications = [loc for loc in locations if loc['location_type'] == 'Application']
    
    print(f"\n📊 Summary:")
    print(f" * Found in {len(environments)} environment(s)")
    print(f" * Found in {len(applications)} application(s)")
    
    return {
        'found': True,
        'total_instances': len(matching_services),
        'environments': environments,
        'applications': applications,
        'locations': locations
    }

def validate_cross_environment_service_creation(service_name, env1_name, env1_id, env2_name, env2_id, headers):
    """
    Validate that services can be created with the same name in different environments.
    This tests the core business rule: same names allowed across environments.
    
    Args:
        service_name: Service name to test
        env1_name, env1_id: First environment
        env2_name, env2_id: Second environment  
        headers: Authentication headers
        
    Returns:
        dict: Validation results
    """
    print(f"\n🧪 Testing Cross-Environment Service Creation")
    print(f" * Service: {service_name}")
    print(f" * Environment 1: {env1_name} ({env1_id})")
    print(f" * Environment 2: {env2_name} ({env2_id})")
    
    results = {
        'service_name': service_name,
        'env1': {'name': env1_name, 'id': env1_id, 'exists': False, 'service_id': None},
        'env2': {'name': env2_name, 'id': env2_id, 'exists': False, 'service_id': None},
        'cross_env_allowed': False,
        'same_env_duplicate_blocked': False
    }
    
    # Check current state
    print(f"\n📊 Current State Analysis:")
    
    # Check environment 1
    exists1, service1_id = verify_service_exists(env1_name, env1_id, service_name, headers)
    results['env1']['exists'] = exists1
    results['env1']['service_id'] = service1_id
    print(f" * {env1_name}: {'✅ EXISTS' if exists1 else '❌ NOT FOUND'}")
    
    # Check environment 2  
    exists2, service2_id = verify_service_exists(env2_name, env2_id, service_name, headers)
    results['env2']['exists'] = exists2
    results['env2']['service_id'] = service2_id
    print(f" * {env2_name}: {'✅ EXISTS' if exists2 else '❌ NOT FOUND'}")
    
    # Analyze cross-environment behavior
    if exists1 and exists2:
        print(f"\n✅ VALIDATION PASSED: Service exists in both environments")
        print(f" * This proves cross-environment services are working correctly")
        results['cross_env_allowed'] = True
    elif exists1 or exists2:
        print(f"\n⚠️  PARTIAL: Service exists in one environment but not the other")
        print(f" * This is normal and shows environment isolation is working")
        results['cross_env_allowed'] = True
    else:
        print(f"\n❌ Service not found in either environment")
        
    # Check for environment-specific versions
    env1_specific = f"{service_name}-{env1_name.lower()}"
    env2_specific = f"{service_name}-{env2_name.lower()}"
    
    print(f"\n🔍 Checking Environment-Specific Versions:")
    exists1_specific, _ = verify_service_exists(env1_name, env1_id, env1_specific, headers)
    exists2_specific, _ = verify_service_exists(env2_name, env2_id, env2_specific, headers)
    
    print(f" * {env1_specific}: {'✅ EXISTS' if exists1_specific else '❌ NOT FOUND'}")
    print(f" * {env2_specific}: {'✅ EXISTS' if exists2_specific else '❌ NOT FOUND'}")
    
    return results

def validate_component_duplicate_detection(component_name, app1_name, app2_name, headers):
    """
    Validate that component duplicate detection works correctly.
    Tests the rule: same component name in same application = blocked, different applications = allowed.
    
    Args:
        component_name: Component name to test
        app1_name: First application name
        app2_name: Second application name
        headers: Authentication headers
        
    Returns:
        dict: Validation results
    """
    print(f"\n🧪 Testing Component Duplicate Detection")
    print(f" * Component: {component_name}")
    print(f" * Application 1: {app1_name}")
    print(f" * Application 2: {app2_name}")
    
    results = {
        'component_name': component_name,
        'app1': {'name': app1_name, 'components': [], 'has_component': False},
        'app2': {'name': app2_name, 'components': [], 'has_component': False},
        'cross_app_allowed': False,
        'same_app_duplicate_properly_handled': False
    }
    
    # Get all components and applications
    all_components = get_phoenix_components_lazy(headers)
    
    # Get applications to map names to IDs
    app_list_response = requests.get(construct_api_url("/v1/applications"), headers=headers)
    applications = app_list_response.json().get('content', []) if app_list_response.status_code == 200 else []
    
    # Find application IDs
    app1_id = None
    app2_id = None
    for app in applications:
        if app.get('name', '').lower() == app1_name.lower():
            app1_id = app.get('id')
        elif app.get('name', '').lower() == app2_name.lower():
            app2_id = app.get('id')
    
    print(f"\n📊 Application Analysis:")
    print(f" * {app1_name} ID: {app1_id}")
    print(f" * {app2_name} ID: {app2_id}")
    
    # Find all instances of this component
    matching_components = [comp for comp in all_components 
                          if comp.get('name', '').lower() == component_name.lower()]
    
    print(f"\n🔍 Component Instance Analysis:")
    print(f" * Found {len(matching_components)} instance(s) of component '{component_name}':")
    
    for i, comp in enumerate(matching_components, 1):
        comp_app_id = comp.get('applicationId')
        comp_id = comp.get('id')
        
        # Determine which application this belongs to
        app_name = "Unknown"
        if comp_app_id == app1_id:
            app_name = app1_name
            results['app1']['components'].append(comp)
            results['app1']['has_component'] = True
        elif comp_app_id == app2_id:
            app_name = app2_name
            results['app2']['components'].append(comp)
            results['app2']['has_component'] = True
        else:
            # Find application name for this ID
            for app in applications:
                if app.get('id') == comp_app_id:
                    app_name = app.get('name', 'Unknown')
                    break
        
        print(f"   {i}. Application: {app_name} (ID: {comp_app_id})")
        print(f"      └─ Component ID: {comp_id}")
    
    # Analyze cross-application behavior
    if results['app1']['has_component'] and results['app2']['has_component']:
        print(f"\n✅ CROSS-APPLICATION SUCCESS: Component exists in both applications")
        print(f" * This proves cross-application components are working correctly")
        results['cross_app_allowed'] = True
    elif results['app1']['has_component'] or results['app2']['has_component']:
        print(f"\n⚠️  PARTIAL: Component exists in one application but not the other")
        print(f" * This is normal and shows application isolation is working")
        results['cross_app_allowed'] = True
    else:
        print(f"\n❌ Component not found in either application")
    
    # Check for same-application duplicate handling
    app1_count = len(results['app1']['components'])
    app2_count = len(results['app2']['components'])
    
    if app1_count > 1 or app2_count > 1:
        print(f"\n🚫 SAME-APPLICATION DUPLICATES DETECTED:")
        if app1_count > 1:
            print(f" * {app1_name}: {app1_count} instances (should be 1)")
        if app2_count > 1:
            print(f" * {app2_name}: {app2_count} instances (should be 1)")
        print(f" * This indicates duplicate detection may not be working properly")
        results['same_app_duplicate_properly_handled'] = False
    else:
        print(f"\n✅ SAME-APPLICATION DUPLICATES: Properly handled (max 1 per application)")
        results['same_app_duplicate_properly_handled'] = True
    
    return results

def _is_service_cache_valid(env_id):
    """Check if the service cache for a specific environment is still valid"""
    import time
    return (env_id in _environment_services_cache['data'] and 
            env_id in _environment_services_cache['timestamp'] and 
            time.time() - _environment_services_cache['timestamp'][env_id] < _environment_services_cache['ttl'])

def _update_service_cache(env_id, services):
    """Update the service cache for a specific environment"""
    import time
    if env_id not in _environment_services_cache['data']:
        _environment_services_cache['data'][env_id] = {}
    
    # Create lookup dictionary with lowercase names for fast access
    service_lookup = {}
    for service in services:
        service_name_lower = service['name'].lower()
        service_lookup[service_name_lower] = service
    
    _environment_services_cache['data'][env_id] = service_lookup
    _environment_services_cache['timestamp'][env_id] = time.time()

def clear_service_cache(env_id=None):
    """Clear the service cache for specific environment or all environments"""
    if env_id:
        if env_id in _environment_services_cache['data']:
            del _environment_services_cache['data'][env_id]
        if env_id in _environment_services_cache['timestamp']:
            del _environment_services_cache['timestamp'][env_id]
        # IMPORTANT: Also clear global component cache to ensure fresh fetch with pagination
        clear_component_cache()
    else:
        _environment_services_cache['data'] = {}
        _environment_services_cache['timestamp'] = {}
        # Clear global component cache when clearing all service caches
        clear_component_cache()

def get_environment_services_cached(env_id, headers, force_refresh=False):
    """
    Get all services for an environment with caching.
    Returns a dictionary with lowercase service names as keys.
    
    Args:
        env_id: Environment ID
        headers: Request headers
        force_refresh: If True, bypass cache and fetch fresh data
    """
    # Check if we have valid cached data for this environment (unless forced refresh)
    if not force_refresh and _is_service_cache_valid(env_id):
        cached_services = _environment_services_cache['data'][env_id]
        print(f" * Using cached services for environment {env_id} ({len(cached_services)} services)")
        return cached_services
    
    # Cache miss or forced refresh - fetch fresh data
    if force_refresh:
        print(f" * Force refreshing services for environment {env_id}...")
        # Clear global component cache to ensure fresh pagination
        clear_component_cache()
    else:
        print(f" * Fetching services for environment {env_id}...")
    
    services = get_phoenix_components_in_environment(env_id, headers)
    
    # Update cache
    _update_service_cache(env_id, services)
    
    print(f" * Environment cache updated with {len(_environment_services_cache['data'][env_id])} services")
    return _environment_services_cache['data'][env_id]

def _is_application_verification_cache_valid():
    """Check if the application verification cache is still valid"""
    import time
    return (_application_verification_cache['timestamp'] is not None and 
            time.time() - _application_verification_cache['timestamp'] < _application_verification_cache['ttl'])

def _update_application_verification_cache(applications, components):
    """Update the application verification cache with fresh data"""
    import time
    
    # Cache applications by name
    for app in applications:
        if app.get('name'):
            _application_verification_cache['applications'][app['name']] = app
    
    # Cache components by (app_name, component_name)
    for component in components:
        if component.get('name') and component.get('applicationId'):
            # Find application name for this component
            app_name = None
            for app in applications:
                if app.get('id') == component['applicationId']:
                    app_name = app.get('name')
                    break
            
            if app_name:
                cache_key = (app_name, component['name'])
                _application_verification_cache['components'][cache_key] = component
    
    _application_verification_cache['timestamp'] = time.time()

def clear_application_verification_cache():
    """Clear the application verification cache"""
    _application_verification_cache['applications'] = {}
    _application_verification_cache['components'] = {}
    _application_verification_cache['timestamp'] = None

def service_exists_in_cache(service_name, env_id, env_services_cache, headers=None, fallback_check=True):
    """
    Fast lookup to check if service exists in cache with optional fallback.
    Returns (exists, service_data) tuple.
    
    Args:
        service_name: Name of the service to check
        env_id: Environment ID
        env_services_cache: Current environment services cache
        headers: Request headers for fallback API check
        fallback_check: If True, perform fresh API check on cache miss
    """
    service_name_lower = service_name.lower()
    
    # First check cache
    if service_name_lower in env_services_cache:
        service_data = env_services_cache[service_name_lower]
        return True, service_data
    
    # Cache miss - perform fallback check if enabled and headers provided
    if fallback_check and headers:
        print(f"  └─ 🔍 Cache miss for '{service_name}' - performing fresh API check...")
        try:
            # Force refresh the environment cache and check again
            fresh_cache = get_environment_services_cached(env_id, headers, force_refresh=True)
            if service_name_lower in fresh_cache:
                service_data = fresh_cache[service_name_lower]
                print(f"  └─ ✅ Found '{service_name}' in fresh cache (was missing from stale cache)")
                return True, service_data
            else:
                print(f"  └─ ❌ '{service_name}' confirmed missing from environment {env_id}")
        except Exception as e:
            print(f"  └─ ⚠️  Fallback check failed: {e}")
    
    return False, None

def add_service_to_cache(service_name, service_data, env_id):
    """
    Add a newly created service to the cache for immediate lookup.
    """
    if env_id in _environment_services_cache['data']:
        service_name_lower = service_name.lower()
        _environment_services_cache['data'][env_id][service_name_lower] = service_data

# ============================================================================
# PHASE 1: RULE BATCHING IMPLEMENTATION
# ============================================================================

class RuleBatch:
    """Container for batched rules with validation and fallback support"""
    
    def __init__(self, application_name, component_name):
        self.application_name = application_name
        self.component_name = component_name
        self.rules = []
        self.validation_errors = []
        self.created_rules = []
        self.failed_rules = []
    
    def add_rule(self, rule_name, filter_type, filter_value):
        """Add a rule to the batch with validation"""
        try:
            validated_rule = self._validate_and_build_rule(rule_name, filter_type, filter_value)
            if validated_rule:
                self.rules.append(validated_rule)
                return True
            else:
                self.validation_errors.append(f"Invalid rule: {rule_name}")
                return False
        except Exception as e:
            self.validation_errors.append(f"Rule validation error for {rule_name}: {str(e)}")
            return False
    
    def _validate_and_build_rule(self, rule_name, filter_type, filter_value):
        """Validate and build a rule structure for API submission"""
        
        # Helper function to validate value
        def is_valid_value(value):
            if value is None:
                return False
            if isinstance(value, str) and (not value.strip() or value.lower() == 'null'):
                return False
            if isinstance(value, list) and len(value) == 0:
                return False
            return True
        
        if not is_valid_value(filter_value):
            return None
        
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
            'tags': 'tags',
            'repository': 'repository',
            'cidr': 'cidr',
            'fqdn': 'fqdn',
            'netbios': 'netbios'
        }
        
        api_filter_name = filter_name_mapping.get(filter_type.lower(), filter_type)
        
        # Special handling for different filter types
        if api_filter_name == 'tags':
            if isinstance(filter_value, list) and all(isinstance(tag, dict) and ('value' in tag or ('key' in tag and 'value' in tag)) for tag in filter_value):
                filter_content = filter_value
            else:
                tags = filter_value if isinstance(filter_value, list) else [filter_value]
                filter_content = [{"value": tag} for tag in tags if tag and len(str(tag).strip()) >= 3]
        elif api_filter_name == 'keyLike':
            if isinstance(filter_value, (list, dict)):
                if isinstance(filter_value, list):
                    filter_content = filter_value[0] if filter_value else ""
                elif isinstance(filter_value, dict):
                    filter_content = str(filter_value.get('value', ''))
            else:
                filter_content = filter_value
        else:
            filter_content = filter_value
        
        # Build the rule structure
        rule = {
            "name": rule_name,
            "filter": {
                api_filter_name: filter_content
            }
        }
        
        return rule
    
    def get_batch_payload(self):
        """Generate the API payload for batch rule creation"""
        return {
            "selector": {
                "applicationSelector": {"name": self.application_name, "caseSensitive": False},
                "componentSelector": {"name": self.component_name, "caseSensitive": False}
            },
            "rules": self.rules
        }

def create_component_rules_batch(application_name, component, headers):
    """
    PHASE 1 OPTIMIZATION: Create all component rules in batches
    """
    
    print(f"\n[Batch Rule Creation]")
    print(f"└─ Application: {application_name}")
    print(f"└─ Component: {component['ComponentName']}")
    
    # Create rule batch container
    rule_batch = RuleBatch(application_name, component['ComponentName'])
    
    # Helper function to validate value (same as original)
    def is_valid_value(value):
        if value is None:
            return False
        if isinstance(value, str) and (not value.strip() or value.lower() == 'null'):
            return False
        return True
    
    # Collect all rules for this component
    rules_added = 0
    
    # SearchName rule
    if component.get('SearchName') and is_valid_value(component.get('SearchName')):
        rule_name = f"Rule for keyLike for {component['ComponentName']}"
        if rule_batch.add_rule(rule_name, 'keyLike', component['SearchName']):
            rules_added += 1
    
    # Tags rule
    if component.get('Tags') and is_valid_value(component.get('Tags')):
        rule_name = f"Rule for tags for {component['ComponentName']}"
        if rule_batch.add_rule(rule_name, 'tags', component['Tags']):
            rules_added += 1
    
    # Repository rule
    repository_names = get_repositories_from_component(component)
    if repository_names:
        rule_name = f"Rule for repository for {component['ComponentName']}"
        if rule_batch.add_rule(rule_name, 'repository', repository_names):
            rules_added += 1
    
    # Other standard rules
    rule_mappings = [
        ('Cidr', 'cidr'),
        ('Fqdn', 'fqdn'),
        ('Netbios', 'netbios'),
        ('Hostnames', 'hostnames'),
        ('OsNames', 'osNames'),
        ('ProviderAccountId', 'providerAccountId'),
        ('ProviderAccountName', 'providerAccountName'),
        ('ResourceGroup', 'resourceGroup'),
        ('AssetType', 'assetType')
    ]
    
    for yaml_key, api_key in rule_mappings:
        if component.get(yaml_key) and is_valid_value(component.get(yaml_key)):
            rule_name = f"Rule for {api_key} for {component['ComponentName']}"
            if rule_batch.add_rule(rule_name, api_key, component[yaml_key]):
                rules_added += 1
    
    print(f"└─ Collected {rules_added} standard rules for batch creation")
    
    # Report validation errors
    if rule_batch.validation_errors:
        print(f"└─ ⚠️  {len(rule_batch.validation_errors)} validation errors:")
        for error in rule_batch.validation_errors:
            print(f"   └─ {error}")
    
    # Create rules in batch if we have any valid rules
    batch_success = False
    if rule_batch.rules:
        batch_success = _execute_rule_batch(rule_batch, headers)
    
    # Handle MultiCondition rules separately (these use different API structure)
    multicondition_success = True
    multicondition_types = ['MultiConditionRule', 'MultiConditionRules', 'MULTI_MultiConditionRules', 'MultiMultiConditionRules']
    
    for rule_type in multicondition_types:
        if component.get(rule_type) and is_valid_value(component.get(rule_type)):
            try:
                print(f"└─ Creating {rule_type} rules separately...")
                if rule_type == 'MultiConditionRule':
                    create_multicondition_component_rules(application_name, component['ComponentName'], [component.get(rule_type)], headers)
                else:
                    create_multicondition_component_rules(application_name, component['ComponentName'], component.get(rule_type), headers)
            except Exception as e:
                print(f"└─ ❌ Error creating {rule_type}: {e}")
                multicondition_success = False
    
    overall_success = batch_success and multicondition_success
    
    if overall_success:
        print(f"└─ ✅ All rules created successfully for {component['ComponentName']}")
    else:
        print(f"└─ ⚠️  Some rules failed for {component['ComponentName']}")
    
    return overall_success

def _execute_rule_batch(rule_batch, headers):
    """Execute a batch of rules with fallback to individual creation"""
    
    if not rule_batch.rules:
        return True
    
    print(f"└─ Attempting batch creation of {len(rule_batch.rules)} rules...")
    
    try:
        # Attempt batch creation
        api_url = construct_api_url("/v1/components/rules")
        payload = rule_batch.get_batch_payload()
        
        if DEBUG:
            print(f"└─ Batch payload:")
            print(json.dumps(payload, indent=2))
        
        response = requests.post(api_url, headers=headers, json=payload)
        
        if response.status_code == 201:
            print(f"└─ ✅ Batch creation successful: {len(rule_batch.rules)} rules created")
            rule_batch.created_rules = rule_batch.rules.copy()
            return True
        elif response.status_code == 409:
            print(f"└─ ℹ️  Some rules already exist (409), considering as success")
            rule_batch.created_rules = rule_batch.rules.copy()
            return True
        else:
            print(f"└─ ⚠️  Batch creation failed (HTTP {response.status_code}), falling back to individual creation")
            return _fallback_to_individual_rules(rule_batch, headers)
    
    except Exception as e:
        print(f"└─ ❌ Batch creation error: {e}")
        print(f"└─ 🔄 Falling back to individual rule creation...")
        return _fallback_to_individual_rules(rule_batch, headers)

def _fallback_to_individual_rules(rule_batch, headers):
    """Fallback to creating rules individually when batch fails"""
    
    success_count = 0
    total_rules = len(rule_batch.rules)
    
    print(f"└─ Creating {total_rules} rules individually...")
    
    for rule in rule_batch.rules:
        try:
            # Create individual rule payload
            individual_payload = {
                "selector": {
                    "applicationSelector": {"name": rule_batch.application_name, "caseSensitive": False},
                    "componentSelector": {"name": rule_batch.component_name, "caseSensitive": False}
                },
                "rules": [rule]
            }
            
            api_url = construct_api_url("/v1/components/rules")
            response = requests.post(api_url, headers=headers, json=individual_payload)
            
            if response.status_code in [201, 409]:  # Created or already exists
                rule_batch.created_rules.append(rule)
                success_count += 1
                if response.status_code == 201:
                    print(f"   └─ ✅ Created: {rule['name']}")
                else:
                    print(f"   └─ ℹ️  Exists: {rule['name']}")
            else:
                rule_batch.failed_rules.append(rule)
                print(f"   └─ ❌ Failed: {rule['name']} (HTTP {response.status_code})")
                
        except Exception as e:
            rule_batch.failed_rules.append(rule)
            print(f"   └─ ❌ Error creating {rule['name']}: {e}")
    
    print(f"└─ Individual creation complete: {success_count}/{total_rules} successful")
    
    return success_count == total_rules

# ============================================================================
# PHASE 2: BATCH VERIFICATION IMPLEMENTATION
# ============================================================================

class BatchVerificationEngine:
    """Handles batch verification of applications and components"""
    
    def __init__(self, headers):
        self.headers = headers
    
    def verify_applications_batch(self, applications):
        """Verify multiple applications were created correctly"""
        
        print(f"\n[Batch Application Verification]")
        print(f"└─ Verifying {len(applications)} applications...")
        
        # Check if we have valid cached data
        if _is_application_verification_cache_valid():
            print(f"└─ Using cached application data for verification")
            cached_apps = _application_verification_cache['applications']
        else:
            print(f"└─ Fetching fresh application data for verification...")
            # Fetch all applications in one API call
            try:
                all_apps = self._fetch_all_applications()
                all_components = self._fetch_all_components()
                
                # Update cache with fresh data
                _update_application_verification_cache(all_apps, all_components)
                cached_apps = _application_verification_cache['applications']
                
            except Exception as e:
                print(f"└─ ❌ Error fetching applications for verification: {e}")
                return {'successful': [], 'failed': applications, 'partial': []}
        
        verification_results = {
            'successful': [],
            'failed': [],
            'partial': []
        }
        
        for app in applications:
            app_name = app.get('AppName')
            if app_name in cached_apps:
                verification_results['successful'].append({
                    'application': app,
                    'phoenix_data': cached_apps[app_name]
                })
                print(f"   └─ ✅ {app_name}: Verified")
            else:
                verification_results['failed'].append(app)
                print(f"   └─ ❌ {app_name}: Not found")
        
        print(f"└─ Verification complete: {len(verification_results['successful'])}/{len(applications)} successful")
        
        return verification_results
    
    def verify_components_batch(self, application_name, components):
        """Verify multiple components for an application were created correctly"""
        
        print(f"\n[Batch Component Verification]")
        print(f"└─ Verifying {len(components)} components for {application_name}...")
        
        verification_results = {
            'successful': [],
            'failed': [],
            'partial': []
        }
        
        # Use cached component data
        cached_components = _application_verification_cache['components']
        
        for component in components:
            component_name = component.get('ComponentName')
            cache_key = (application_name, component_name)
            
            if cache_key in cached_components:
                verification_results['successful'].append({
                    'component': component,
                    'phoenix_data': cached_components[cache_key]
                })
                print(f"   └─ ✅ {component_name}: Verified")
            else:
                verification_results['failed'].append(component)
                print(f"   └─ ❌ {component_name}: Not found")
        
        print(f"└─ Component verification complete: {len(verification_results['successful'])}/{len(components)} successful")
        
        return verification_results
    
    def verify_rules_batch(self, application_name, component_name, expected_rules):
        """Verify all rules for a component were created"""
        
        if not expected_rules:
            return {'created': [], 'failed': [], 'duplicates': []}
        
        print(f"\n[Batch Rule Verification]")
        print(f"└─ Verifying {len(expected_rules)} rules for {application_name}/{component_name}...")
        
        try:
            # Fetch existing rules for component in single API call
            existing_rules = self._fetch_component_rules(application_name, component_name)
            
            verification_matrix = self._compare_rule_sets(expected_rules, existing_rules)
            
            print(f"└─ Rule verification complete:")
            print(f"   └─ Created: {len(verification_matrix['created'])}")
            print(f"   └─ Failed: {len(verification_matrix['failed'])}")  
            print(f"   └─ Duplicates: {len(verification_matrix['duplicates'])}")
            
            return verification_matrix
            
        except Exception as e:
            print(f"└─ ❌ Error verifying rules: {e}")
            return {'created': [], 'failed': expected_rules, 'duplicates': []}
    
    def _fetch_all_applications(self):
        """Fetch all applications from Phoenix"""
        api_url = construct_api_url("/v1/applications")
        params = {"pageSize": 1000}  # Large page size to get most apps
        
        response = requests.get(api_url, headers=self.headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        applications = data.get('content', [])
        
        # Handle pagination if needed
        total_pages = data.get('totalPages', 1)
        for page in range(1, total_pages):
            params['pageNumber'] = page
            response = requests.get(api_url, headers=self.headers, params=params)
            response.raise_for_status()
            applications.extend(response.json().get('content', []))
        
        return applications
    
    def _fetch_all_components(self):
        """Fetch all components from Phoenix"""
        api_url = construct_api_url("/v1/components")
        params = {"pageSize": 1000}  # Large page size
        
        response = requests.get(api_url, headers=self.headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        components = data.get('content', [])
        
        # Handle pagination if needed
        total_pages = data.get('totalPages', 1)
        for page in range(1, total_pages):
            params['pageNumber'] = page
            response = requests.get(api_url, headers=self.headers, params=params)
            response.raise_for_status()
            components.extend(response.json().get('content', []))
        
        return components
    
    def _fetch_component_rules(self, application_name, component_name):
        """Fetch all rules for a specific component"""
        api_url = construct_api_url("/v1/components/rules")
        params = {
            "applicationSelector": {"name": application_name, "caseSensitive": False},
            "componentSelector": {"name": component_name, "caseSensitive": False}
        }
        
        response = requests.get(api_url, headers=self.headers, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def _compare_rule_sets(self, expected_rules, existing_rules):
        """Compare expected rules with existing rules"""
        
        verification_matrix = {
            'created': [],
            'failed': [],
            'duplicates': []
        }
        
        # Create lookup sets for comparison
        existing_rule_signatures = set()
        for rule in existing_rules:
            if rule.get('filter'):
                # Create a signature based on filter content
                filter_str = json.dumps(rule['filter'], sort_keys=True)
                existing_rule_signatures.add(filter_str)
        
        for expected_rule in expected_rules:
            if expected_rule.get('filter'):
                expected_signature = json.dumps(expected_rule['filter'], sort_keys=True)
                
                if expected_signature in existing_rule_signatures:
                    verification_matrix['created'].append(expected_rule)
                else:
                    verification_matrix['failed'].append(expected_rule)
            else:
                verification_matrix['failed'].append(expected_rule)
        
        return verification_matrix

def verify_application_creation_batch(applications, headers):
    """
    PHASE 2 OPTIMIZATION: Verify batch of applications were created correctly
    """
    verifier = BatchVerificationEngine(headers)
    return verifier.verify_applications_batch(applications)

def verify_components_creation_batch(application_name, components, headers):
    """
    PHASE 2 OPTIMIZATION: Verify batch of components were created correctly
    """
    verifier = BatchVerificationEngine(headers)
    return verifier.verify_components_batch(application_name, components)

def verify_rules_creation_batch(application_name, component_name, expected_rules, headers):
    """
    PHASE 2 OPTIMIZATION: Verify batch of rules were created correctly
    """
    verifier = BatchVerificationEngine(headers)
    return verifier.verify_rules_batch(application_name, component_name, expected_rules)

@dispatch(dict)
def get_phoenix_components(headers2):
    """
    Fetches all Phoenix components with proper pagination handling.
    Uses caching to reduce API calls in quick-check mode.
    
    Args:
        headers: Request headers containing authorization
        
    Returns:
        list: Complete list of all components across all pages
    """
    global headers
    if not headers:
        headers = headers2
    
    # Check if we have valid cached data
    if _is_cache_valid():
        print(f" * Using cached components data ({len(_component_cache['data'])} components)")
        return _component_cache['data']
    
    components = []
    page_size = 1000  # Use maximum page size to minimize API calls
    page_number = 0
    total_pages = None
    total_elements = 0
    all_requests = []  # Store all request/response data
    
    print("\n[Component Listing]")
    print(" * Fetching all components with optimized pagination (page size: 1000)...")
    
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
            
            # Store this request/response for debugging
            request_info = {
                "page_number": page_number,
                "params": params,
                "response_summary": {
                    "components_count": len(data.get('content', [])),
                    "total_elements": data.get('totalElements', 0),
                    "total_pages": data.get('totalPages', 0),
                    "page_size": data.get('pageSize', 0),
                    "is_last": data.get('last', False),
                    "is_first": data.get('first', False)
                }
            }
            all_requests.append(request_info)
            
            # Save debug response for ALL pages to track complete pagination
            save_debug_response(
                operation_type="component_fetch",
                response_data=data,
                request_data=params,
                endpoint="/v1/components",
                additional_info=f"page_{page_number:02d}_of_{total_pages or 'unknown'}"
            )
            
            # Add components from current page
            page_components = data.get('content', [])
            components.extend(page_components)
            
            # Update total pages on first iteration
            if total_pages is None:
                total_pages = data.get('totalPages', 1)
                total_elements = data.get('totalElements', 0)
                print(f" * Found {total_elements} total components across {total_pages} pages (page size: {page_size})")
                
                # If there are a lot of pages, try to increase page size further
                if total_pages > 20:
                    print(f" * High page count detected, will use larger page size for remaining pages")
            
            print(f" * Fetched page {page_number + 1}/{total_pages} ({len(page_components)} components) - Total so far: {len(components)}")
            
            # Print sample components from this page if in debug mode
            if DEBUG and page_components:
                print(f"   Sample components from page {page_number + 1}:")
                for i, comp in enumerate(page_components[:3]):  # Show first 3 components
                    env_name = comp.get('applicationId', 'Unknown')
                    print(f"   - [{env_name}] {comp.get('name', 'Unknown')}")
                if len(page_components) > 3:
                    print(f"   ... and {len(page_components) - 3} more components")
            
            page_number += 1
            
            # Add minimal delay between pages to avoid rate limiting (with larger page size, fewer requests needed)
            if page_number < total_pages:
                time.sleep(0.1)
                
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
            
            if hasattr(response, 'status_code'):
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
                    print(f" * HTTP {response.status_code} error, stopping pagination")
                    break
            else:
                print(" * Network error, stopping pagination")
                break
    
    print(f"\n[Component Fetch Complete]")
    print(f" * Total components fetched: {len(components)}")
    print(f" * Expected total: {total_elements}")
    print(f" * Pages fetched: {len(all_requests)}")
    print(f" * Page size used: {page_size}")
    print(f" * Total API requests: {len(all_requests)}")
    
    if len(components) != total_elements:
        print(f" ! WARNING: Fetched {len(components)} components but expected {total_elements}")
        print(f" ! This may indicate pagination issues or API errors")
        
        # Save detailed request summary for debugging
        save_debug_response(
            operation_type="component_fetch_summary",
            response_data={
                "total_components_fetched": len(components),
                "expected_total": total_elements,
                "pages_fetched": len(all_requests),
                "page_size": page_size,
                "all_requests": all_requests,
                "discrepancy": total_elements - len(components)
            },
            request_data={"operation": "complete_pagination_summary"},
            endpoint="/v1/components",
            additional_info="pagination_issue_detected"
        )
    else:
        print(f" ✓ Successfully fetched all components!")
        
        # Save successful pagination summary
        save_debug_response(
            operation_type="component_fetch_summary",
            response_data={
                "total_components_fetched": len(components),
                "expected_total": total_elements,
                "pages_fetched": len(all_requests),
                "page_size": page_size,
                "all_requests": all_requests,
                "status": "success"
            },
            request_data={"operation": "complete_pagination_summary"},
            endpoint="/v1/components",
            additional_info="success"
        )
    
    # Cache the fetched components for future use
    _update_component_cache(components)
    
    return components


def get_phoenix_components_lazy(access_token2=None):
    """
    Get components with lazy loading support. Uses cached data if available,
    otherwise fetches from API and caches for future use.
    """
    global access_token
    if access_token2 and not access_token:
        access_token = access_token2
    
    # If we have cached data, use it
    if _is_cache_valid():
        return _component_cache['data']
    
    # Otherwise fetch and cache
    return get_phoenix_components(access_token)

def get_phoenix_components_in_environment(env_id, access_token2):
    """
    Get all components/services for a specific environment.
    Filters the complete dataset by environment ID.
    
    Args:
        env_id: The environment ID to filter by
        access_token2: Authentication token
        
    Returns:
        list: Components filtered by environment ID
    """
    global access_token
    if not access_token:
        access_token = access_token2
    
    all_components = get_phoenix_components_lazy(access_token)
    
    # Filter by environment ID with validation
    env_components = [x for x in all_components if x.get('applicationId') == env_id]
    
    if DEBUG:
        print(f" * get_phoenix_components_in_environment: {len(env_components)} components in environment {env_id}")
        print(f" * Total components in system: {len(all_components)}")
    
    return env_components


def environment_service_exist(env_id, phoenix_components, service_name):
    """
    Check if a service exists in an environment with case-insensitive comparison.
    
    Args:
        env_id: Environment ID
        phoenix_components: List of Phoenix components (pre-filtered or all components)
        service_name: Name of the service to check
        
    Returns:
        bool: True if service exists, False otherwise
    """
    service_name_lower = service_name.lower()
    
    # If phoenix_components is empty (lazy loading), fetch on-demand
    if not phoenix_components:
        phoenix_components = get_phoenix_components_lazy()
    
    # Filter components by environment ID if not already filtered
    env_specific_components = [
        comp for comp in phoenix_components 
        if comp.get('applicationId') == env_id
    ]
    
    if DEBUG:
        print(f" * environment_service_exist: Checking {len(env_specific_components)} services in environment {env_id}")
        print(f" * Looking for service: {service_name}")
    
    # Search for the service in the environment-specific components
    for component in env_specific_components:
        if component['name'].lower() == service_name_lower:
            if DEBUG:
                print(f" * Found service {service_name} in environment {env_id}")
            return True
    
    # If not found, return False
    if DEBUG:
        print(f" * Service {service_name} not found in environment {env_id}")
        print(f" * Available services in environment: {[comp['name'] for comp in env_specific_components[:5]]}")
        if len(env_specific_components) > 5:
            print(f" * ... and {len(env_specific_components) - 5} more services")
    
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
        # Try to fetch services filtered by environment first (if API supports it)
        print(f" * Attempting to fetch services filtered by environment ID: {env_id}")
        
        # First attempt: Try filtering by applicationId directly via API
        params_filtered = {
            "pageSize": 1000,
            "sort": "name,asc",
            "applicationId": env_id  # Try environment-specific filtering
        }
        
        filtered_response = requests.get(api_url, headers=headers, params=params_filtered)
        
        if filtered_response.status_code == 200:
            # API supports filtering by applicationId
            print(" * Using API-level environment filtering")
            data = filtered_response.json()
            
            save_debug_response(
                operation_type="service_fetch_filtered",
                response_data=data,
                request_data=params_filtered,
                endpoint="/v1/components",
                additional_info=f"env_{env_id[:8]}"
            )
            
            total_elements = data.get('totalElements', 0)
            total_pages = data.get('totalPages', 1)
            print(f" * Found {total_elements} services in environment {env_name} across {total_pages} pages")
            
            all_services_fetched = data.get('content', [])
            
            # Fetch remaining pages if needed
            for page in range(1, total_pages):
                params_filtered['pageNumber'] = page
                response = requests.get(api_url, headers=headers, params=params_filtered)
                response.raise_for_status()
                all_services_fetched.extend(response.json().get('content', []))
                print(f" * Fetched page {page + 1}/{total_pages}")
            
            # CRITICAL FIX: API filtering by applicationId is not working correctly
            # We need to filter client-side to ensure we only get services from the target environment
            print(f" * Client-side filtering by environment ID: {env_id}")
            env_services = [service for service in all_services_fetched if service.get('applicationId') == env_id]
            print(f" * After client-side filtering: {len(env_services)} services confirmed in target environment")
            
            # For debugging, also check if service exists in other environments
            all_services = all_services_fetched  # Will be used for cross-environment check
            
        else:
            # API doesn't support filtering, fall back to fetch all and filter
            print(" * API doesn't support environment filtering, fetching all services...")
            
            params = {
                "pageSize": 1000,  # Use larger page size to reduce pagination
                "sort": "name,asc"  # Consistent sorting
            }
            
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Save debug response if enabled
            save_debug_response(
                operation_type="service_fetch",
                response_data=data,
                request_data=params,
                endpoint="/v1/components"
            )
            
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
            
            # Filter services by environment ID
            print(f" * Filtering services by environment ID: {env_id}")
            env_services = [service for service in all_services if service.get('applicationId') == env_id]
            print(f" * After filtering: {len(env_services)} services in environment {env_name}")
        
        # Validate that all services in env_services actually belong to the target environment
        print(f" * Validating client-side filtering for {len(env_services)} services...")
        invalid_services = [s for s in env_services if s.get('applicationId') != env_id]
        if invalid_services:
            print(f" ! ERROR: Client-side filtering failed! Found {len(invalid_services)} services with incorrect environment ID!")
            for svc in invalid_services[:3]:  # Show first 3 invalid services
                print(f"   └─ {svc.get('name', 'Unknown')} has applicationId: {svc.get('applicationId')}")
            print(f" ! This indicates a bug in the filtering logic - please report this issue")
        else:
            print(f" ✓ All {len(env_services)} services correctly filtered for environment {env_id}")
        
        # Debug: Check if service exists in ANY location (only if we fetched all services)
        if 'all_services' in locals() and len(all_services) > len(env_services):
            services_found_elsewhere = []
            for service in all_services:
                if service['name'].lower() == service_name_lower:
                    services_found_elsewhere.append(service)
            
            if services_found_elsewhere:
                print(f" * Service '{service_name}' found {len(services_found_elsewhere)} time(s) in system:")
                for i, svc in enumerate(services_found_elsewhere, 1):
                    app_id = svc.get('applicationId')
                    svc_id = svc.get('id', 'Unknown')
                    
                    # Try to determine if this is an environment or application
                    # Environment IDs are typically longer UUIDs, application IDs can be shorter
                    if len(app_id) > 30 and '-' in app_id:
                        location_type = "Environment"
                    else:
                        location_type = "Application"
                    
                    print(f"   {i}. {location_type} ID: {app_id} (Service ID: {svc_id})")
                    
                    if app_id == env_id:
                        print(f"      ✓ This matches our target environment!")
                    else:
                        print(f"      ! Different from target environment: {env_id}")
                
                # Check if any match our target environment
                matching_services = [s for s in services_found_elsewhere if s.get('applicationId') == env_id]
                if not matching_services:
                    print(f" ! Service exists in {len(services_found_elsewhere)} other location(s) but NOT in target environment")
                    print(f" ! Target environment ID: {env_id}")
                    
                    # Show if any are in applications vs environments
                    app_locations = [s for s in services_found_elsewhere if len(s.get('applicationId', '')) <= 30]
                    env_locations = [s for s in services_found_elsewhere if len(s.get('applicationId', '')) > 30]
                    
                    if app_locations:
                        print(f" ! Found {len(app_locations)} instance(s) as application components")
                    if env_locations:
                        print(f" ! Found {len(env_locations)} instance(s) as environment services")
        
        print(f" * Environment-specific services count: {len(env_services)}")
        
        # Add detailed debug info about pagination results
        if DEBUG:
            print(f" * Debug: Total services fetched across all pages: {len(all_services)}")
            print(f" * Debug: Services by environment breakdown:")
            env_breakdown = {}
            for service in all_services:
                app_id = service.get('applicationId', 'Unknown')
                env_breakdown[app_id] = env_breakdown.get(app_id, 0) + 1
            for app_id, count in sorted(env_breakdown.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"   └─ Environment {app_id}: {count} services")
            if len(env_breakdown) > 10:
                print(f"   └─ ... and {len(env_breakdown) - 10} more environments")
        
        # First try exact case-insensitive match in the correct environment
        matched_services = []
        for service in env_services:
            if service['name'].lower() == service_name_lower:
                matched_services.append(service)
                print(f" + Service found: {service['name']} (ID: {service.get('id')})")
                print(f"   └─ Environment: {service.get('applicationId')}")
                
                # Double-check this is actually in the target environment (should always be true after client-side filtering)
                if service.get('applicationId') == env_id:
                    print(f" ✓ Service confirmed in target environment {env_name}")
                    return True, service.get('id')
                else:
                    print(f" ! ERROR: Service found in filtered results but wrong environment ID!")
                    print(f"   └─ Expected: {env_id}")
                    print(f"   └─ Found: {service.get('applicationId')}")
                    print(f" ! This indicates a critical filtering bug - please report this issue")
                    continue
        
        # If we found matches but none were in the right environment, something is wrong
        if matched_services:
            print(f" ! Found {len(matched_services)} service(s) with name '{service_name}' but none in target environment")
            print(f" ! This suggests the client-side filtering is not working correctly")
        
        # If not found, look for similar services in the same environment
        similar_services = []
        for service in env_services:
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
        
        # Check if we should look for environment-specific version
        env_specific_name = f"{service_name}-{env_name.lower()}"
        print(f" * Checking for environment-specific service name: {env_specific_name}")
        
        for service in env_services:
            if service['name'].lower() == env_specific_name.lower():
                print(f" ✓ Found environment-specific service: {service['name']} (ID: {service.get('id')})")
                print(f" ✓ This resolves cross-environment naming conflicts")
                return True, service.get('id')
        
        # Service not found in target environment
        print(f" ! Service '{service_name}' not found in environment '{env_name}'")
        
        # Show helpful information about where it exists
        if 'services_found_elsewhere' in locals() and services_found_elsewhere:
            print(f" ! Service exists in {len(services_found_elsewhere)} other location(s)")
            print(f" ! This is normal - services can exist in multiple environments")
            print(f" ! Consider:")
            print(f"   1. Creating '{service_name}' in environment '{env_name}'")
            print(f"   2. Or using environment-specific name '{env_specific_name}'")
        
        if DEBUG:
            print(f" ! Available services in environment {env_name}:")
            for service in sorted(env_services[:10], key=lambda x: x['name']):  # Show first 10
                print(f"   └─ {service['name']}")
            if len(env_services) > 10:
                print(f"   └─ ... and {len(env_services) - 10} more services")
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
        
        # Save debug response if enabled
        save_debug_response(
            operation_type="application_environment_fetch",
            response_data=data,
            request_data=None,  # GET request has no body
            endpoint="/v1/applications"
        )
        
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
    Tries alternative API approaches before falling back to empty list
    """
    print("🛠️  Handling API compatibility issue...")
    print("📝 This might be due to:")
    print("   • API version mismatch between client and server")
    print("   • Server-side enum definition changes")
    print("   • Backend configuration issues")
    
    # Try alternative API approaches
    alternative_approaches = [
        "/v1/applications?minimal=true",
        "/v1/applications?pageSize=1000",
        "/v1/applications?type=APPLICATION",
        "/v1/applications?type=ENVIRONMENT"
    ]
    
    for approach in alternative_approaches:
        try:
            print(f"🔄 Trying alternative API approach: {approach}")
            api_url = construct_api_url(approach)
            response = requests.get(api_url, headers=headers)
            
            if response.status_code == 200:
                print("✅ Alternative API approach successful!")
                data = response.json()
                components = data.get('content', [])
                print(f"📊 Retrieved {len(components)} applications/environments")
                
                # Validate the data structure
                if components and isinstance(components, list):
                    # Check if we have valid application/environment objects
                    valid_items = [item for item in components if isinstance(item, dict) and 'name' in item and 'type' in item]
                    if valid_items:
                        print(f"✅ Found {len(valid_items)} valid applications/environments")
                        return valid_items
                
            elif response.status_code == 400 and b'ENVIRONMENT_CLOUD' not in response.content:
                # Different 400 error, might be worth continuing
                print(f"⚠️  Got 400 status but different error: {response.content}")
                continue
            else:
                print(f"⚠️  Alternative approach failed with status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Alternative approach failed with exception: {str(e)}")
            continue
        except Exception as e:
            print(f"⚠️  Unexpected error in alternative approach: {str(e)}")
            continue
    
    print("⚠️  All alternative approaches failed")
    print("🔄 Attempting direct individual resource checks...")
    
    # Try to get individual applications/environments by common names
    # This helps detect existing resources even when listing fails
    common_names = ['Production', 'Staging', 'Development', 'Test']
    found_items = []
    
    for name in common_names:
        try:
            # Try to get specific application/environment
            search_url = construct_api_url(f"/v1/applications?name={name}")
            response = requests.get(search_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                items = data.get('content', [])
                for item in items:
                    if item.get('name') == name:
                        found_items.append(item)
                        print(f"✅ Found existing resource: {name} (type: {item.get('type', 'unknown')})")
        except:
            # Silently continue if individual checks fail
            pass
    
    if found_items:
        print(f"✅ Successfully identified {len(found_items)} existing resources through individual checks")
        return found_items
    
    # Final fallback: return empty list but log the issue thoroughly
    print("⚠️  Returning empty applications/environments list")
    print("💡 Script will proceed assuming no existing apps/environments")
    print("🚨 WARNING: This may cause duplicate creation attempts")
    print("🔍 Check Phoenix UI manually to verify existing resources")
    
    return []


def get_environment_by_name(env_name, headers):
    """
    Try to get a specific environment by name
    This is a fallback method when the main listing API fails
    """
    try:
        # Try direct search by name
        api_url = construct_api_url(f"/v1/applications?name={env_name}")
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            # Save debug response if enabled
            try:
                data = response.json()
                save_debug_response(
                    operation_type="environment_fetch",
                    response_data=data,
                    request_data={"name": env_name},
                    endpoint=f"/v1/applications?name={env_name}"
                )
            except Exception:
                pass  # Don't fail if debug saving fails
            data = response.json()
            environments = [item for item in data.get('content', []) 
                          if item.get('type') == 'ENVIRONMENT' and item.get('name') == env_name]
            if environments:
                print(f"✅ Found environment '{env_name}' via direct search")
                return environments[0]
        
        # Try alternative pagination approach
        api_url = construct_api_url("/v1/applications?pageSize=1000")
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            for item in data.get('content', []):
                if item.get('type') == 'ENVIRONMENT' and item.get('name') == env_name:
                    print(f"✅ Found environment '{env_name}' via pagination search")
                    return item
                    
    except Exception as e:
        print(f"⚠️  Error searching for environment '{env_name}': {str(e)}")
    
    return None


@dispatch(str, str, dict, int, dict)
def add_service(applicationSelectorName, env_id, service, tier, headers2):
    """
    OPTIMIZED: Create service without redundant verifications.
    Returns (success, service_id) tuple.
    """
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
        
        # Handle 409 conflict - service already exists
        if response.status_code == 409:
            print(f" * Service name '{service_name}' conflicts with existing service - analyzing...")
            # Check if it exists in the target environment (legitimate duplicate)
            try:
                env_services_cache = get_environment_services_cached(env_id, headers)
                if service_name.lower() in env_services_cache:
                    existing_service = env_services_cache[service_name.lower()]
                    print(f" ✓ SERVICE UPDATE: Service '{service_name}' already exists in target environment '{applicationSelectorName}'")
                    print(f" ✓ Business rule: Update rules for existing service in same environment")
                    print(f" ✓ Using existing service for rule updates (ID: {existing_service.get('id')})")
                    return True, existing_service.get('id')  # Service exists - update rules
                else:
                    # Service exists in DIFFERENT environment - this should be allowed
                    print(f" * Service {service_name} exists in different environment(s)")
                    print(f" * This is allowed - creating environment-specific version")
                    
                    # Use environment-specific naming to avoid global conflicts
                    unique_service_name = f"{service_name}-{applicationSelectorName.lower()}"
                    print(f" * Retrying with environment-specific name: {unique_service_name}")
                    
                    # Update payload and retry
                    payload["name"] = unique_service_name
                    response = requests.post(api_url, headers=headers, json=payload)
                    
                    if response.status_code == 200 or response.status_code == 201:
                        response_data = response.json()
                        service_id = response_data.get('id')
                        print(f" ✓ Created environment-specific service: {unique_service_name} (ID: {service_id})")
                        return True, service_id
                    else:
                        print(f" ! Failed to create environment-specific service: {response.status_code}")
                        return False, None
                        
            except Exception as cache_error:
                print(f" ! Error checking service cache: {cache_error}")
                return False, None
        
        response.raise_for_status()
        
        # Extract service ID from response
        response_data = response.json()
        service_id = response_data.get('id')
        
        print(f" + Added Service: {service_name} (ID: {service_id})")
        return True, service_id
        
    except requests.exceptions.RequestException as e:
        print(f"Error creating service {service_name}: {e}")
        if hasattr(response, 'content'):
            print(f"Response content: {response.content}")
        return False, None

@dispatch(str, str, dict, int, str, dict)
def add_service(applicationSelectorName, env_id, service, tier, team, headers2):
    """
    OPTIMIZED: Create service with team support without redundant verifications.
    Returns (success, service_id) tuple.
    """
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
        # Create service payload directly (existence already checked by caller)
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
            # Service name conflict - determine if it's a legitimate duplicate or cross-environment naming
            print(f" * Service name '{service_name}' conflicts with existing service - analyzing...")
            
            try:
                # Check if service exists in the TARGET environment (update rules)
                env_services_cache = get_environment_services_cached(env_id, headers)
                print(f" * Refreshed cache now contains {len(env_services_cache)} services for environment {env_id}")
                if service_name.lower() in env_services_cache:
                    existing_service = env_services_cache[service_name.lower()]
                    print(f" ✓ SERVICE UPDATE: Service '{service_name}' already exists in target environment '{applicationSelectorName}'")
                    print(f" ✓ Business rule: Update rules for existing service in same environment")
                    print(f" ✓ Using existing service for rule updates (ID: {existing_service.get('id')})")
                    return True, existing_service.get('id')  # Service exists - update rules
                else:
                    # Service exists in DIFFERENT environment - this is the key fix!
                    print(f" * Service {service_name} exists in different environment(s)")
                    print(f" * This is allowed - services can have same name across environments")
                    
                    # CRITICAL FIX: Don't treat cross-environment naming as an error
                    # The 409 conflict is likely due to global name constraints in the API
                    # We should use environment-specific naming to avoid conflicts
                    
                    unique_service_name = f"{service_name}-{applicationSelectorName.lower()}"
                    print(f" * Creating service with environment-specific name: {unique_service_name}")
                    
                    # Check if the environment-specific name already exists
                    if unique_service_name.lower() in env_services_cache:
                        existing_service = env_services_cache[unique_service_name.lower()]
                        print(f" ✓ Environment-specific service already exists (ID: {existing_service.get('id')})")
                        return True, existing_service.get('id')
                    
                    # Create with environment-specific name
                    payload["name"] = unique_service_name
                    print(f" * Retrying creation with unique name: {unique_service_name}")
                    response = requests.post(api_url, headers=headers, json=payload)
                        
            except Exception as cache_error:
                print(f" ! Error checking service cache: {cache_error}")
                # Fallback to original suffix logic
                unique_service = f"{service_name}-{applicationSelectorName.lower()}"
                print(f" * Attempting to create service as {unique_service}")
                payload["name"] = unique_service
                response = requests.post(api_url, headers=headers, json=payload)
        
        # Handle second 409 conflict (suffixed name also exists)
        if response.status_code == 409:
            print(f" ! Suffixed service name also exists - checking if it's in target environment...")
            try:
                env_services_cache = get_environment_services_cached(env_id, headers)
                suffixed_name = payload["name"]  # This is the suffixed name
                if suffixed_name.lower() in env_services_cache:
                    existing_service = env_services_cache[suffixed_name.lower()]
                    print(f" + Found existing suffixed service: {suffixed_name} (ID: {existing_service.get('id')})")
                    return True, existing_service.get('id')  # Use existing suffixed service
                else:
                    print(f" ! Suffixed service exists in different environment - cannot create service")
                    return False, None
            except Exception as e:
                print(f" ! Error checking suffixed service: {e}")
                return False, None
        
        response.raise_for_status()
        
        # Extract service ID from response
        response_data = response.json()
        service_id = response_data.get('id')
        created_service_name = payload["name"]
        
        print(f" + Service creation successful: {created_service_name} (ID: {service_id})")
        return True, service_id
        
    except requests.exceptions.RequestException as e:
        print(f"Error creating service {service_name}: {e}")
        if hasattr(response, 'content'):
            print(f"Response content: {response.content}")
        return False, None


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


def check_application_exists(app_name, headers):
    """
    Check if an application exists by trying to find it directly
    This is a fallback method when the main listing API fails
    """
    try:
        # Try to search for the application by name
        api_url = construct_api_url(f"/v1/applications?name={app_name}")
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Save debug response if enabled
            save_debug_response(
                operation_type="application_fetch",
                response_data=data,
                request_data={"name": app_name},
                endpoint=f"/v1/applications?name={app_name}"
            )
            
            applications = [item for item in data.get('content', []) 
                          if item.get('type') == 'APPLICATION' and item.get('name') == app_name]
            if applications:
                print(f"✅ Found application '{app_name}' via direct search (ID: {applications[0].get('id')})")
                return applications[0]
        
        # Try alternative approach - get first page of applications and search
        api_url = construct_api_url("/v1/applications?pageSize=1000")
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            for item in data.get('content', []):
                if item.get('type') == 'APPLICATION' and item.get('name') == app_name:
                    print(f"✅ Found application '{app_name}' via pagination search (ID: {item.get('id')})")
                    return item
                    
    except Exception as e:
        print(f"⚠️  Error searching for application '{app_name}': {str(e)}")
    
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
    
    print(f"\n[Deployment Operation]")
    print(f"└─ Found {len(applications)} applications to process")
    print(f"└─ Found {len(environments)} environments to process")
    print(f"└─ Found {len(phoenix_apps_envs)} Phoenix apps/envs")
    
    # Track deployment set to service mismatches
    deployment_set_mismatches = []
    
    # Handle API compatibility issues
    if not phoenix_apps_envs:
        print(f"⚠️  No Phoenix apps/envs retrieved - likely due to API compatibility issue")
        print(f"🔄 Switching to individual application detection mode...")
        
        # In this mode, we'll try to create deployments and let the API tell us if apps exist
        available_apps = {}  # Empty - we'll detect during deployment attempts
        available_services = {}
        fallback_mode = True
    else:
        # Normal mode - we have the full list
        available_apps = {app['name']: app['id'] for app in phoenix_apps_envs if app.get('type') == "APPLICATION"}
        available_services = {}
        fallback_mode = False
        
        # Debug: Show available applications
        print(f"└─ Available applications in Phoenix:")
        for app_name, app_id in available_apps.items():
            print(f"   └─ {app_name} (ID: {app_id})")
            
        # Get all services for each environment with proper pagination
        all_services = get_phoenix_components(headers)
        for env in phoenix_apps_envs:
            if env.get('type') == "ENVIRONMENT":
                available_services[env['name']] = {svc['name']: svc['id'] for svc in all_services if svc['applicationId'] == env['id']}
                print(f"└─ Total services loaded for '{env['name']}': {len(available_services[env['name']])}")
    
    # Debug: Show applications to process
    print(f"└─ Applications from config to process:")
    for app in applications:
        app_name = app.get('AppName', 'Unknown')
        deployment_set = app.get('Deployment_set', 'None')
        print(f"   └─ {app_name} (Deployment_set: {deployment_set})")
    
    # Process each application
    for app in applications:
        app_name = app.get('AppName')
        if not app_name:
            continue
            
        print(f"\n[Processing Application: {app_name}]")
        
        # Check if application exists (normal mode vs fallback mode)
        app_exists = False
        app_id = None
        
        if fallback_mode:
            # In fallback mode, try to find the application directly
            print(f"└─ Checking if application exists (fallback mode)...")
            app_data = check_application_exists(app_name, headers)
            if app_data:
                app_exists = True
                app_id = app_data.get('id')
                available_apps[app_name] = app_id  # Cache for future use
            else:
                print(f"└─ ⚠️  Application '{app_name}' not found - it may need to be created first")
                print(f"└─ 💡 Skipping deployment for this application")
                continue
        else:
            # Normal mode - check against the pre-loaded list
            if app_name not in available_apps:
                print(f"└─ Error: Application not found in Phoenix listing")
                continue
            else:
                app_exists = True
                app_id = available_apps[app_name]
                
        deployment_set = app.get('Deployment_set')
        if not deployment_set:
            print(f"└─ Error: No deployment set defined")
            continue
            
        print(f"└─ ✅ Application found (ID: {app_id})")
        print(f"└─ Processing deployment set: {deployment_set}")

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
                    # Log deployment set mismatch
                    mismatch_info = {
                        'app_name': app_name,
                        'deployment_set': deployment_set,
                        'service_name': service_name,
                        'service_deployment_set': service.get('Deployment_set'),
                        'service_deployment_tag': service.get('Deployment_tag'),
                        'environment': env_name
                    }
                    deployment_set_mismatches.append(mismatch_info)
            
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
                    
                    # Save debug response if enabled
                    response_data = response.json() if response.content else {"status": "deployed", "message": "Deployment successful"}
                    save_debug_response(
                        operation_type="deployment",
                        response_data=response_data,
                        request_data=deployment_payload,
                        endpoint=f"/v1/applications/{app_id}/deploy"
                    )
                    
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
    
    # Report deployment set mismatches
    if deployment_set_mismatches:
        print(f"\n[Deployment Set Mismatches Report]")
        print(f"└─ Found {len(deployment_set_mismatches)} deployment set mismatches:")
        
        # Group by deployment set for better readability
        mismatches_by_deployment_set = {}
        for mismatch in deployment_set_mismatches:
            deployment_set = mismatch['deployment_set']
            if deployment_set not in mismatches_by_deployment_set:
                mismatches_by_deployment_set[deployment_set] = []
            mismatches_by_deployment_set[deployment_set].append(mismatch)
        
        for deployment_set, mismatches in mismatches_by_deployment_set.items():
            print(f"\n  [Deployment Set: {deployment_set}]")
            print(f"  └─ {len(mismatches)} services don't match this deployment set:")
            
            for mismatch in mismatches:
                service_ds = mismatch['service_deployment_set'] or 'None'
                service_dt = mismatch['service_deployment_tag'] or 'None'
                print(f"    └─ Service: {mismatch['service_name']}")
                print(f"       └─ Has Deployment_set: {service_ds}")
                print(f"       └─ Has Deployment_tag: {service_dt}")
                print(f"       └─ Required: {deployment_set}")
                print(f"       └─ Environment: {mismatch['environment']}")
                
                # Log to error log as well
                log_error(
                    'Deployment Set Mismatch',
                    f"{mismatch['app_name']} -> {mismatch['service_name']}",
                    mismatch['environment'],
                    f"Deployment set mismatch: app requires '{deployment_set}' but service has Deployment_set='{service_ds}', Deployment_tag='{service_dt}'",
                    f"Service configuration may need to be updated to match application deployment set"
                )
    else:
        print(f"\n[Deployment Set Mismatches Report]")
        print(f"└─ ✅ No deployment set mismatches found")
    
    print(f"\n[Final Deployment Summary]")
    print(f"└─ Total deployments processed: {total_deployments}")
    print(f"└─ Successful deployments: {successful_deployments}")
    print(f"└─ Failed deployments: {failed_deployments}")
    print(f"└─ Deployment set mismatches: {len(deployment_set_mismatches)}")


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
                    
                    # Save debug response if enabled
                    response_data = response.json() if response.content else {"status": "deployed", "message": "Deployment successful"}
                    save_debug_response(
                        operation_type="deployment",
                        response_data=response_data,
                        request_data=deployment,
                        endpoint="/v1/applications/deploy"
                    )
                    
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


def get_assets(applicationEnvironmentId, type, headers2):
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
        api_url = construct_api_url(f"/v1/assets?pageNumber=0&pageSize=1000")
        response = requests.post(api_url, headers=headers, json = asset_request)
        response.raise_for_status()

        data = response.json()
        assets = [asset['name'] for asset in data.get('content', [])]
        total_pages = data.get('totalPages', 1)
        for i in range(1, total_pages):
            api_url = construct_api_url(f"/v1/assets?pageNumber={i}&pageSize=1000")
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


def create_components_from_assets(applicationEnvironments, phoenix_components, headers2):
    global headers
    if not headers:
        headers = headers2
    types = ["CONTAINER", "CLOUD"]
    phoenix_component_names = [pcomponent.get('name') for pcomponent in phoenix_components]
    auto_created_components = []  # Track created components for YAML export
    
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
                        
                        # Extract team names from environment tags
                        team_names = [next((tag['value'] for tag in appEnv['tags'] if 'value' in tag and 'key' in tag and tag['key'] == 'pteam'), None)]
                        team_names = [name for name in team_names if name is not None]  # Remove None values
                        
                        print(f"Created component with name {component_name} in environment: {appEnv.get('name')}")
                        component_to_create = {
                            "Status": None,
                            "Type": None,
                            "TeamNames": team_names,
                            "ComponentName": component_name
                        }
                        create_custom_component(appEnv['name'], component_to_create, headers)
                        print(f"Created component with name {component_name} in environment: {appEnv.get('name')}")
                        
                        # Track the created component for YAML export
                        auto_created_components.append({
                            'environment_name': appEnv.get('name'),
                            'application_name': appEnv.get('applicationName', appEnv.get('name')),  # Use app name if available
                            'component_name': component_name,
                            'team_names': team_names,
                            'status': None,
                            'type': None,
                            'asset_count': len(group),
                            'asset_type': type,
                            'original_group_name': group[0]
                        })
    
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
    page_size = 1000
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
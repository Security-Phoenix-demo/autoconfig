import time
import os
import argparse
import traceback
import stat
import glob
import configparser
import yaml
from git import Repo
from datetime import datetime, timedelta
from threading import Thread, Event
from itertools import chain
from collections import defaultdict
from providers.Phoenix import get_phoenix_components, populate_phoenix_teams, get_auth_token , create_teams, create_team_rules, assign_users_to_team, populate_applications_and_environments, create_environment, add_environment_services, add_cloud_asset_rules, add_thirdparty_services, create_applications, create_deployments, create_autolink_deployments, create_teams_from_pteams, create_components_from_assets, create_user_for_application, load_users_from_phoenix, update_environment, check_and_create_missing_users, create_user_with_role, track_application_component_operations, initialize_debug_session
import providers.Phoenix as phoenix_module
from providers.Utils import populate_domains, get_subdomains, populate_users_with_all_team_access, add_PAT_to_github_repo_url
from providers.YamlHelper import populate_repositories_from_config, populate_teams, populate_hives, populate_subdomain_owners, populate_environments_from_env_groups_from_config, populate_all_access_emails_from_config, populate_applications_from_config, load_flag_for_create_users_from_config, load_run_config, load_remote_configuration_locations, load_github_repo_folder, load_github_config_file_name, load_teams_folder, load_hives_config

# Global Variables
resource_folder = os.path.join(os.path.dirname(__file__), 'Resources')
access_token = None
headers = {}
CLIENT_ID = None
CLIENT_SECRET = None

# Global report tracking
execution_report = {
    'config_files': [],
    'total_start_time': None,
    'total_end_time': None,
    'actions_performed': [],
    'summary': {
        'teams': {'attempted': 0, 'successful': 0, 'failed': 0, 'details': []},
        'users': {'attempted': 0, 'successful': 0, 'failed': 0, 'details': []},
        'applications': {'attempted': 0, 'successful': 0, 'failed': 0, 'details': []},
        'environments': {'attempted': 0, 'successful': 0, 'failed': 0, 'details': []},
        'services': {'attempted': 0, 'successful': 0, 'failed': 0, 'details': []},
        'components': {'attempted': 0, 'successful': 0, 'failed': 0, 'details': []},
        'deployments': {'attempted': 0, 'successful': 0, 'failed': 0, 'details': []},
        'repositories': {'attempted': 0, 'successful': 0, 'failed': 0, 'details': []},
        'cloud_assets': {'attempted': 0, 'successful': 0, 'failed': 0, 'details': []},
        'errors': []
    }
}


def track_operation(category, operation_name, item_name, success=True, error_msg=None):
    """Track the success or failure of operations for reporting"""
    global execution_report
    
    if category not in execution_report['summary']:
        execution_report['summary'][category] = {'attempted': 0, 'successful': 0, 'failed': 0, 'details': []}
    
    execution_report['summary'][category]['attempted'] += 1
    
    detail = {
        'operation': operation_name,
        'item': item_name,
        'success': success,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    if success:
        execution_report['summary'][category]['successful'] += 1
        detail['status'] = 'SUCCESS'
    else:
        execution_report['summary'][category]['failed'] += 1
        detail['status'] = 'FAILED'
        detail['error'] = error_msg
        execution_report['summary']['errors'].append({
            'category': category,
            'operation': operation_name,
            'item': item_name,
            'error': error_msg,
            'timestamp': detail['timestamp']
        })
    
    execution_report['summary'][category]['details'].append(detail)


def generate_execution_report():
    """Generate a comprehensive execution report"""
    global execution_report
    
    execution_report['total_end_time'] = datetime.now()
    total_duration = execution_report['total_end_time'] - execution_report['total_start_time']
    
    print("\n" + "="*80)
    print("PHOENIX AUTOCONFIG EXECUTION REPORT")
    print("="*80)
    
    print(f"\n📅 Execution Time: {execution_report['total_start_time'].strftime('%Y-%m-%d %H:%M:%S')} - {execution_report['total_end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️  Total Duration: {str(total_duration).split('.')[0]}")
    
    print(f"\n📂 Configuration Files Processed: {len(execution_report['config_files'])}")
    for config_file in execution_report['config_files']:
        print(f"   • {os.path.basename(config_file)}")
    
    # Auto-created components information
    if execution_report.get('auto_created_components_file'):
        print(f"\n🔧 Auto-Created Components: {execution_report.get('auto_created_components_count', 0)}")
        print(f"📁 Saved to: {os.path.relpath(execution_report['auto_created_components_file'], resource_folder)}")
    
    print(f"\n🔧 Actions Performed: {', '.join(execution_report['actions_performed'])}")
    
    # Summary by category
    print(f"\n📊 OPERATION SUMMARY")
    print("-"*50)
    
    total_attempted = 0
    total_successful = 0
    total_failed = 0
    
    for category, stats in execution_report['summary'].items():
        if category == 'errors':
            continue
            
        if stats['attempted'] > 0:
            success_rate = (stats['successful'] / stats['attempted']) * 100
            status_icon = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 50 else "❌"
            
            print(f"{status_icon} {category.upper()}: {stats['successful']}/{stats['attempted']} successful ({success_rate:.1f}%)")
            
            total_attempted += stats['attempted']
            total_successful += stats['successful']
            total_failed += stats['failed']
    
    if total_attempted > 0:
        overall_success_rate = (total_successful / total_attempted) * 100
        print(f"\n🎯 OVERALL SUCCESS RATE: {total_successful}/{total_attempted} ({overall_success_rate:.1f}%)")
    
    # Detailed breakdown
    print(f"\n📋 DETAILED BREAKDOWN")
    print("-"*50)
    
    for category, stats in execution_report['summary'].items():
        if category == 'errors' or stats['attempted'] == 0:
            continue
            
        print(f"\n{category.upper()} ({stats['attempted']} attempted):")
        
        # Group by operation type
        operations = defaultdict(list)
        for detail in stats['details']:
            operations[detail['operation']].append(detail)
        
        for operation, items in operations.items():
            successful_items = [item for item in items if item['success']]
            failed_items = [item for item in items if not item['success']]
            
            print(f"  {operation}:")
            print(f"    ✅ Successful ({len(successful_items)}):")
            for item in successful_items[:5]:  # Show first 5
                print(f"      • {item['item']}")
            if len(successful_items) > 5:
                print(f"      ... and {len(successful_items) - 5} more")
            
            if failed_items:
                print(f"    ❌ Failed ({len(failed_items)}):")
                for item in failed_items[:5]:  # Show first 5
                    print(f"      • {item['item']} - {item.get('error', 'Unknown error')}")
                if len(failed_items) > 5:
                    print(f"      ... and {len(failed_items) - 5} more")
    
    # Error summary from execution report
    report_errors = execution_report['summary']['errors']
    
    # Try to read additional errors from the errors.log file
    log_file_errors = []
    try:
        errors_log_path = os.path.join(os.path.dirname(__file__), 'errors.log')
        if os.path.exists(errors_log_path):
            with open(errors_log_path, 'r') as f:
                content = f.read()
                if content.strip():
                    # Parse error entries from log file
                    error_entries = content.split('--------------------------------------------------------------------------------')
                    for entry in error_entries:
                        if 'TIME:' in entry and 'ERROR:' in entry:
                            lines = entry.strip().split('\n')
                            error_info = {}
                            for line in lines:
                                if line.startswith('TIME:'):
                                    error_info['timestamp'] = line.replace('TIME:', '').strip()
                                elif line.startswith('OPERATION:'):
                                    error_info['operation'] = line.replace('OPERATION:', '').strip()
                                elif line.startswith('NAME:'):
                                    error_info['item'] = line.replace('NAME:', '').strip()
                                elif line.startswith('ERROR:'):
                                    error_info['error'] = line.replace('ERROR:', '').strip()
                                elif line.startswith('ENVIRONMENT:'):
                                    error_info['environment'] = line.replace('ENVIRONMENT:', '').strip()
                            
                            if error_info.get('operation') and error_info.get('error'):
                                # Filter out success messages that were incorrectly logged as errors
                                error_message = error_info.get('error', '').lower()
                                if not any(success_word in error_message for success_word in ['successfully', 'success', 'created successfully', 'completed successfully']):
                                    log_file_errors.append(error_info)
    except Exception as e:
        print(f"└─ Warning: Could not read errors.log file: {e}")
    
    total_errors = len(report_errors) + len(log_file_errors)
    
    if total_errors > 0:
        print(f"\n❌ COMPREHENSIVE ERROR SUMMARY ({total_errors} total)")
        print("-"*50)
        
        # Group errors by category from execution report
        error_by_category = defaultdict(list)
        for error in report_errors:
            error_by_category[error['category']].append(error)
        
        # Add errors from log file
        for error in log_file_errors:
            category = error.get('operation', 'OTHER').split()[0].upper()
            error_by_category[category].append({
                'operation': error.get('operation', 'Unknown'),
                'item': error.get('item', 'Unknown'),
                'error': error.get('error', 'Unknown error'),
                'timestamp': error.get('timestamp', 'Unknown time'),
                'source': 'log_file'
            })
        
        # Display errors by category
        for category, errors in error_by_category.items():
            print(f"\n{category.upper()} Errors ({len(errors)}):")
            for i, error in enumerate(errors[:5]):  # Show first 5 errors per category
                source_indicator = " [LOG]" if error.get('source') == 'log_file' else ""
                print(f"  {i+1}. {error['operation']} - {error['item']}{source_indicator}")
                error_text = error['error'][:120] + '...' if len(error['error']) > 120 else error['error']
                print(f"     Error: {error_text}")
                if error.get('timestamp'):
                    print(f"     Time: {error['timestamp']}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more errors")
        
        # Show recent errors from log file separately if there are many
        if len(log_file_errors) > 3:
            print(f"\n📋 RECENT ERRORS FROM LOG FILE ({len(log_file_errors)} total):")
            print("-"*50)
            for error in log_file_errors[-3:]:  # Show last 3 errors
                print(f"  • {error.get('operation', 'Unknown')} - {error.get('item', 'Unknown')}")
                print(f"    {error.get('error', 'Unknown error')[:100]}...")
                print(f"    Time: {error.get('timestamp', 'Unknown')}")
    else:
        print(f"\n✅ NO ERRORS ENCOUNTERED")
    
    print(f"\n" + "="*80)
    print("END OF REPORT")
    print("="*80)


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
        Supports subfolder paths like /COMPANY/COMPANY-core-structure.yaml
    """
    config_files_to_use = get_config_files_to_use()
    if phoenix_module.DEBUG:
        print(f"Config files to use from run-config.yaml: {config_files_to_use}")

    if not config_files_to_use:
        print(f"No config files to use from Resources folder")
        return []
    
    found_config_files = []
    
    for config_file in config_files_to_use:
        # Handle subfolder paths (e.g., /COMPANY/COMPANY-core-structure.yaml)
        if config_file.startswith('/'):
            # Remove leading slash and construct full path
            relative_path = config_file[1:]  # Remove leading '/'
            full_path = os.path.join(resource_folder, relative_path)
        else:
            # Direct file in Resources folder
            full_path = os.path.join(resource_folder, config_file)
        
        # Check if file exists and is a YAML file
        if os.path.exists(full_path) and (full_path.endswith('.yaml') or full_path.endswith('.yml')):
            found_config_files.append(full_path)
            if phoenix_module.DEBUG:
                print(f"Found config file: {full_path}")
        else:
            print(f"Warning: Config file not found: {full_path}")
    
    print(f"Using config files for processing: {[os.path.relpath(f, resource_folder) for f in found_config_files]}")
    
    return found_config_files

def load_config_ini(config_file_path=None):
    """
    Load configuration parameters from config.ini file.
    
    :param config_file_path: Optional path to config.ini file. If not provided, 
                           looks for config.ini in the Resources folder
    :return: Dictionary containing configuration values
    """
    config = {}
    
    if not config_file_path:
        config_file_path = os.path.join(resource_folder, 'config.ini')
    
    if not os.path.exists(config_file_path):
        print(f"Config file not found: {config_file_path}")
        print("Using default values for asset component creation parameters")
        return config
    
    try:
        parser = configparser.ConfigParser()
        parser.read(config_file_path)
        
        # Load asset component creation parameters from [asset_component_creation] section
        if 'asset_component_creation' in parser:
            section = parser['asset_component_creation']
            
            # ASSET_NAME_SIMILARITY_THRESHOLD (float, 0.0 to 1.0)
            if 'asset_name_similarity_threshold' in section:
                try:
                    threshold = section.getfloat('asset_name_similarity_threshold')
                    if 0.0 <= threshold <= 1.0:
                        config['ASSET_NAME_SIMILARITY_THRESHOLD'] = threshold
                        print(f"✅ Loaded ASSET_NAME_SIMILARITY_THRESHOLD = {threshold}")
                    else:
                        print(f"⚠️  Warning: asset_name_similarity_threshold must be between 0.0 and 1.0, got {threshold}")
                except ValueError as e:
                    print(f"⚠️  Warning: Invalid asset_name_similarity_threshold value: {e}")
            
            # ASSET_GROUP_MIN_SIZE_FOR_COMPONENT_CREATION (integer, >= 1)
            if 'asset_group_min_size_for_component_creation' in section:
                try:
                    min_size = section.getint('asset_group_min_size_for_component_creation')
                    if min_size >= 1:
                        config['ASSET_GROUP_MIN_SIZE_FOR_COMPONENT_CREATION'] = min_size
                        print(f"✅ Loaded ASSET_GROUP_MIN_SIZE_FOR_COMPONENT_CREATION = {min_size}")
                    else:
                        print(f"⚠️  Warning: asset_group_min_size_for_component_creation must be >= 1, got {min_size}")
                except ValueError as e:
                    print(f"⚠️  Warning: Invalid asset_group_min_size_for_component_creation value: {e}")
        
        # Also check [phoenix] section for backward compatibility with existing configs
        elif 'phoenix' in parser:
            section = parser['phoenix']
            
            if 'asset_name_similarity_threshold' in section:
                try:
                    threshold = section.getfloat('asset_name_similarity_threshold')
                    if 0.0 <= threshold <= 1.0:
                        config['ASSET_NAME_SIMILARITY_THRESHOLD'] = threshold
                        print(f"✅ Loaded ASSET_NAME_SIMILARITY_THRESHOLD = {threshold} (from [phoenix] section)")
                    else:
                        print(f"⚠️  Warning: asset_name_similarity_threshold must be between 0.0 and 1.0, got {threshold}")
                except ValueError as e:
                    print(f"⚠️  Warning: Invalid asset_name_similarity_threshold value: {e}")
            
            if 'asset_group_min_size_for_component_creation' in section:
                try:
                    min_size = section.getint('asset_group_min_size_for_component_creation')
                    if min_size >= 1:
                        config['ASSET_GROUP_MIN_SIZE_FOR_COMPONENT_CREATION'] = min_size
                        print(f"✅ Loaded ASSET_GROUP_MIN_SIZE_FOR_COMPONENT_CREATION = {min_size} (from [phoenix] section)")
                    else:
                        print(f"⚠️  Warning: asset_group_min_size_for_component_creation must be >= 1, got {min_size}")
                except ValueError as e:
                    print(f"⚠️  Warning: Invalid asset_group_min_size_for_component_creation value: {e}")
        
        if config:
            print(f"📁 Loaded configuration from: {config_file_path}")
        else:
            print(f"ℹ️  No asset component creation parameters found in config file")
            
    except Exception as e:
        print(f"❌ Error reading config file {config_file_path}: {e}")
        print("Using default values for asset component creation parameters")
    
    return config


def save_auto_created_components_to_yaml(auto_created_components, output_file=None):
    """
    Save auto-created components to a YAML file in the Resources folder.
    
    :param auto_created_components: List of components that were auto-created
    :param output_file: Optional custom output file path
    :return: Path to the saved YAML file
    """
    if not auto_created_components:
        print("ℹ️  No auto-created components to save")
        return None
    
    # Generate filename if not provided
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(resource_folder, f"phx-auto-components_{timestamp}.yaml")
    
    # Structure the YAML data
    yaml_data = {
        'metadata': {
            'generated_by': 'Phoenix AutoConfig - action_create_components_from_assets',
            'generated_at': datetime.now().isoformat(),
            'description': 'Auto-created components from environment assets',
            'total_components': len(auto_created_components)
        },
        'Applications': {}
    }
    
    # Group components by environment/application
    for component in auto_created_components:
        env_name = component.get('environment_name', 'Unknown')
        app_name = component.get('application_name', env_name)  # Use env name as app name if not specified
        component_name = component.get('component_name', 'Unknown')
        team_names = component.get('team_names', [])
        
        # Ensure application exists in structure
        if app_name not in yaml_data['Applications']:
            yaml_data['Applications'][app_name] = {
                'Environments': {}
            }
        
        # Ensure environment exists in application
        if env_name not in yaml_data['Applications'][app_name]['Environments']:
            yaml_data['Applications'][app_name]['Environments'][env_name] = {
                'Components': {}
            }
        
        # Add component with phx-auto prefix
        prefixed_component_name = f"phx-auto-{component_name}"
        yaml_data['Applications'][app_name]['Environments'][env_name]['Components'][prefixed_component_name] = {
            'Status': component.get('status'),
            'Type': component.get('type'),
            'TeamNames': team_names,
            'auto_created': True,
            'original_name': component_name,
            'asset_count': component.get('asset_count', 0),
            'asset_type': component.get('asset_type', 'UNKNOWN')
        }
    
    # Save to YAML file
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, indent=2, sort_keys=False)
        
        print(f"✅ Saved {len(auto_created_components)} auto-created components to: {output_file}")
        print(f"📁 File location: {os.path.relpath(output_file, resource_folder)}")
        
        # Show summary
        app_count = len(yaml_data['Applications'])
        env_count = sum(len(app['Environments']) for app in yaml_data['Applications'].values())
        print(f"📊 Summary: {len(auto_created_components)} components across {env_count} environments in {app_count} applications")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error saving auto-created components to YAML: {e}")
        return None


def clear_error_logs():
    """Clear all error logs from errors.log file"""
    try:
        errors_log_path = os.path.join(os.path.dirname(__file__), 'errors.log')
        if os.path.exists(errors_log_path):
            # Clear the file by truncating it
            with open(errors_log_path, 'w') as f:
                f.truncate(0)
            print(f"✅ Successfully cleared error logs: {errors_log_path}")
            
            # Also check for any other log files in the directory
            log_files_cleared = 1
            current_dir = os.path.dirname(__file__)
            
            # Look for other common log file patterns
            other_log_patterns = ['*.log', 'debug.log', 'phoenix.log', 'application.log']
            for pattern in other_log_patterns:
                for log_file in glob.glob(os.path.join(current_dir, pattern)):
                    if log_file != errors_log_path and os.path.isfile(log_file):
                        try:
                            with open(log_file, 'w') as f:
                                f.truncate(0)
                            print(f"✅ Successfully cleared additional log file: {os.path.basename(log_file)}")
                            log_files_cleared += 1
                        except Exception as e:
                            print(f"⚠️ Warning: Could not clear {os.path.basename(log_file)}: {e}")
            
            print(f"🎯 Total log files cleared: {log_files_cleared}")
        else:
            print(f"ℹ️ No errors.log file found at: {errors_log_path}")
            print(f"ℹ️ No logs to clear")
    except Exception as e:
        print(f"❌ Error clearing error logs: {e}")
        return False
    
    return True


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
    
    # Load configuration from config.ini
    config_ini_params = load_config_ini()
    
    # Update Phoenix module parameters with config.ini values
    if 'ASSET_NAME_SIMILARITY_THRESHOLD' in config_ini_params:
        phoenix_module.ASSET_NAME_SIMILARITY_THRESHOLD = config_ini_params['ASSET_NAME_SIMILARITY_THRESHOLD']
        print(f"🔧 Set ASSET_NAME_SIMILARITY_THRESHOLD = {phoenix_module.ASSET_NAME_SIMILARITY_THRESHOLD}")
    
    if 'ASSET_GROUP_MIN_SIZE_FOR_COMPONENT_CREATION' in config_ini_params:
        phoenix_module.ASSET_GROUP_MIN_SIZE_FOR_COMPONENT_CREATION = config_ini_params['ASSET_GROUP_MIN_SIZE_FOR_COMPONENT_CREATION']
        print(f"🔧 Set ASSET_GROUP_MIN_SIZE_FOR_COMPONENT_CREATION = {phoenix_module.ASSET_GROUP_MIN_SIZE_FOR_COMPONENT_CREATION}")
    action_teams = args.action_teams == 'true'
    action_create_users_from_teams = args.action_create_users_from_teams == 'true'
    action_code = args.action_code == 'true'
    action_cloud = args.action_cloud == 'true'
    action_deployment = args.action_deployment == 'true'
    action_autolink_deploymentset = args.action_autolink_deploymentset == 'true'
    action_autocreate_teams_from_pteam = args.action_autocreate_teams_from_pteam == 'true'
    action_create_components_from_assets = args.action_create_components_from_assets == 'true'
    
    # Parse create_users_from_responsable flag (defaults to true)
    create_users_from_responsable = args.create_users_from_responsable == 'true'

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
        execution_report['actions_performed'].append('Teams')
        all_team_access = populate_users_with_all_team_access(teams, defaultAllAccessAccounts)
        
        if action_create_users_from_teams:
            print("Creating users from team configuration")
            current_users_emails = list(u.get("email") for u in load_users_from_phoenix(headers))
            created_users_emails = []
            for team in teams:
                for member in team.get('TeamMembers', []):
                    try:
                        if not member.get('Name'):
                            error_msg = f"Missing Name field for team member with email {member.get('EmailAddress', 'NO_EMAIL')}"
                            print(f"⚠️ Error: {error_msg}")
                            track_operation('users', 'create_user_from_team', member.get('EmailAddress', 'NO_EMAIL'), False, error_msg)
                            continue
                            
                        name_parts = member['Name'].split()
                        if len(name_parts) < 2:
                            error_msg = f"Invalid name format for {member['Name']} - needs first and last name"
                            print(f"⚠️ Error: {error_msg}")
                            track_operation('users', 'create_user_from_team', member.get('EmailAddress', member['Name']), False, error_msg)
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
                            try:
                                create_user_with_role(email, first_name, last_name, phoenix_role, headers)
                                created_users_emails.append(email)
                                track_operation('users', 'create_user_from_team', email, True)
                            except Exception as e:
                                track_operation('users', 'create_user_from_team', email, False, str(e))
                                raise e
                        else:
                            track_operation('users', 'skip_existing_user', email, True, 'User already exists')
                            
                    except Exception as e:
                        error_msg = f"Error processing team member: {str(e)}"
                        print(f"⚠️ {error_msg}")
                        track_operation('users', 'create_user_from_team', member.get('EmailAddress', member.get('Name', 'UNKNOWN')), False, error_msg)
                        if phoenix_module.DEBUG:
                            print(f"Member data: {member}")
        
        # Track team creation
        try:
            new_pteams = create_teams(teams, pteams, access_token)
            for team in teams:
                team_name = team.get('TeamName', team.get('AzureDevopsAreaPath', 'Unknown Team'))
                track_operation('teams', 'create_team', team_name, True)
        except Exception as e:
            for team in teams:
                team_name = team.get('TeamName', team.get('AzureDevopsAreaPath', 'Unknown Team'))
                track_operation('teams', 'create_team', team_name, False, str(e))
        
        # Track user creation and team assignments
        try:
            check_and_create_missing_users(teams, all_team_access, hive_staff, access_token)
            create_team_rules(teams, pteams, access_token)
            assign_users_to_team(pteams, new_pteams, teams, all_team_access, hive_staff, access_token)
            
            # Track successful team rules and assignments
            for team in teams:
                team_name = team.get('TeamName', team.get('AzureDevopsAreaPath', 'Unknown Team'))
                track_operation('teams', 'create_team_rules', team_name, True)
                track_operation('teams', 'assign_users_to_team', team_name, True)
        except Exception as e:
            for team in teams:
                team_name = team.get('TeamName', team.get('AzureDevopsAreaPath', 'Unknown Team'))
                track_operation('teams', 'create_team_rules', team_name, False, str(e))
                track_operation('teams', 'assign_users_to_team', team_name, False, str(e))

        elapsed_time = time.time() - start_time
        print(f"[Diagnostic] [Teams] Time Taken: {elapsed_time}")
        start_time = time.time()

    # Cloud actions
    if action_cloud:
        print("Performing Cloud Actions")
        execution_report['actions_performed'].append('Cloud')
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
            track_operation('repositories', 'load_repository', repo['RepositoryName'], True)

    
        if load_flag_for_create_users_from_config(config_file_path):
            print("Creating users from Environment 'Responsable' field")
            current_users_emails = list(u.get("email") for u in load_users_from_phoenix(access_token))
            print(f"Users in Phoenix {current_users_emails}")
            created_users_emails = []
            for env in environments:
                try:
                    created_user_email = create_user_for_application(current_users_emails, created_users_emails, env.get('Responsable'), access_token)
                    if created_user_email:
                        created_users_emails.append(created_user_email)
                        track_operation('users', 'create_user_from_environment', created_user_email, True)
                    else:
                        responsible_email = env.get('Responsable', 'UNKNOWN')
                        track_operation('users', 'skip_existing_user', responsible_email, True, 'User already exists')
                except Exception as e:
                    responsible_email = env.get('Responsable', 'UNKNOWN')
                    track_operation('users', 'create_user_from_environment', responsible_email, False, str(e))
        
        # First handle environment updates
        print("\n[Environment Updates]")
        for environment in environments:
            env_name = environment['Name']
            existing_env = next((env for env in app_environments if env.get('type') == 'ENVIRONMENT' and env['name'] == environment['Name']), None)
            if not existing_env:
                # Create environments as needed
                print(f"Creating environment: {env_name}")
                try:
                    create_environment(environment, headers)
                    track_operation('environments', 'create_environment', env_name, True)
                except Exception as e:
                    track_operation('environments', 'create_environment', env_name, False, str(e))
            else:
                print(f"Updating environment: {env_name}")
                try:
                    update_environment(environment, existing_env, headers)
                    track_operation('environments', 'update_environment', env_name, True)
                except Exception as e:
                    print(f"Warning: Failed to update environment {env_name}: {str(e)}")
                    track_operation('environments', 'update_environment', env_name, False, str(e))
                    continue

        # Then handle services
        print("\n[Service Updates]")
        app_environments = populate_applications_and_environments(headers)
        try:
            add_environment_services(repos, subdomains, environments, app_environments, phoenix_components, subdomain_owners, teams, access_token, track_operation, args.quick_check, args.silent)
            # Note: Individual service tracking is now handled within add_environment_services
            track_operation('cloud_assets', 'process_environment_services', f"{len(environments)} environments", True)
        except Exception as e:
            track_operation('cloud_assets', 'process_environment_services', f"{len(environments)} environments", False, str(e))
        
        print("[Diagnostic] [Cloud] Time Taken:", time.time() - start_time)
        print("Starting Cloud Asset Rules")
        try:
            add_cloud_asset_rules(repos, access_token)
            for repo in repos:
                track_operation('cloud_assets', 'add_cloud_asset_rules', repo['RepositoryName'], True)
        except Exception as e:
            for repo in repos:
                track_operation('cloud_assets', 'add_cloud_asset_rules', repo['RepositoryName'], False, str(e))
        
        print("[Diagnostic] [Cloud] Time Taken:", time.time() - start_time)
        print("Starting Third Party Rules")
        try:
            add_thirdparty_services(phoenix_components, app_environments, subdomain_owners, headers)
            track_operation('cloud_assets', 'add_thirdparty_services', 'Third Party Services', True)
        except Exception as e:
            track_operation('cloud_assets', 'add_thirdparty_services', 'Third Party Services', False, str(e))
    
        elapsed_time = time.time() - start_time
        print(f"[Diagnostic] [Cloud] Time Taken: {elapsed_time}")
        start_time = time.time()

    if action_code:
        print("Performing Code Actions")
        execution_report['actions_performed'].append('Code')
        applications = populate_applications_from_config(config_file_path)
        
        # Determine if we should create users from Responsable field
        # Priority: CLI argument > config file flag
        should_create_users = create_users_from_responsable or load_flag_for_create_users_from_config(config_file_path)
        
        if should_create_users:
           print("🔧 Creating users from Application 'Responsable' field")
           print(f"   └─ Source: {'CLI flag' if create_users_from_responsable else 'config file'}")
           
           try:
               print("   └─ Fetching existing users from Phoenix...")
               # Add timeout protection for user fetching
               import signal
               def timeout_handler(signum, frame):
                   raise TimeoutError("User fetching timeout")
               
               # Set 30 second timeout for user fetching
               signal.signal(signal.SIGALRM, timeout_handler)
               signal.alarm(30)
               
               try:
                   current_users_emails = list(u.get("email") for u in load_users_from_phoenix(access_token))
                   # Convert all emails to lowercase for consistent comparison
                   current_users_emails = [email.lower() if email else "" for email in current_users_emails]
                   print(f"   └─ Found {len(current_users_emails)} existing users")
               finally:
                   signal.alarm(0)  # Clear the timeout
                   
           except TimeoutError:
               print(f"   └─ ⚠️  Timeout fetching existing users (30s limit exceeded)")
               print(f"   └─ Continuing with empty user list (users may be created even if they exist)")
               current_users_emails = []
           except Exception as e:
               print(f"   └─ ⚠️  Failed to fetch existing users: {e}")
               print(f"   └─ Continuing with empty user list (users may be created even if they exist)")
               current_users_emails = []
           
           created_users_emails = []
           
           # Get unique responsible emails first
           responsible_emails = list(set([app.get('Responsable', '').lower() for app in applications if app.get('Responsable')]))
           print(f"   └─ Found {len(responsible_emails)} unique responsible emails to process")
           
           for i, app in enumerate(applications):
               responsible_email = app.get('Responsable', '').strip()
               if not responsible_email:
                   print(f"   └─ [{i+1}/{len(applications)}] Skipping app '{app.get('AppName', 'Unknown')}' - no Responsable email")
                   continue
                   
               print(f"   └─ [{i+1}/{len(applications)}] Processing '{app.get('AppName', 'Unknown')}' -> {responsible_email}")
               
               try:
                   # Check if user already exists (case-insensitive)
                   if responsible_email.lower() in current_users_emails:
                       print(f"      └─ ✅ User already exists: {responsible_email}")
                       track_operation('users', 'skip_existing_user', responsible_email, True, 'User already exists')
                       continue
                   
                   # Check if we've already created this user in this run
                   if responsible_email.lower() in [email.lower() for email in created_users_emails]:
                       print(f"      └─ ✅ User already created in this run: {responsible_email}")
                       track_operation('users', 'skip_existing_user', responsible_email, True, 'User created earlier in this run')
                       continue
                   
                   # Attempt to create user with timeout protection
                   print(f"      └─ 🆕 Creating new user: {responsible_email}")
                   created_user_email = create_user_for_application(current_users_emails, created_users_emails, responsible_email, access_token)
                   
                   if created_user_email:
                       created_users_emails.append(created_user_email)
                       # Update the current users list to prevent duplicates
                       current_users_emails.append(created_user_email.lower())
                       track_operation('users', 'create_user_from_application', created_user_email, True)
                       print(f"      └─ ✅ User created successfully: {created_user_email}")
                   else:
                       print(f"      └─ ⚠️  User creation returned None (likely already exists): {responsible_email}")
                       track_operation('users', 'skip_existing_user', responsible_email, True, 'User creation returned None')
                       
               except Exception as e:
                   error_msg = f"Error processing user {responsible_email}: {str(e)}"
                   print(f"      └─ ❌ {error_msg}")
                   track_operation('users', 'create_user_from_application', responsible_email, False, str(e))
                   # Continue processing other users instead of stopping
                   continue
           
           print(f"   └─ 📊 User creation summary: {len(created_users_emails)} new users created")
        else:
           print("⏭️  Skipping user creation from 'Responsable' field (disabled via CLI flag)")
        
        # Set up component tracking callback before application creation
        track_application_component_operations(track_operation)
        
        # Track application creation (call the function once but track each application)
        try:
            create_applications(applications, app_environments, phoenix_components, headers)
            for app in applications:
                app_name = app.get('AppName', 'Unknown Application')
                track_operation('applications', 'create_application', app_name, True)
        except Exception as e:
            for app in applications:
                app_name = app.get('AppName', 'Unknown Application')
                track_operation('applications', 'create_application', app_name, False, str(e))
        
        print(f"[Diagnostic] [Code] Time Taken: {time.time() - start_time}")
        start_time = time.time()

    if action_deployment:
        print("Performing deployment action")
        execution_report['actions_performed'].append('Deployment')
        # reload apps/envs before deployment
        app_environments = populate_applications_and_environments(headers)
        environments = populate_environments_from_env_groups_from_config(config_file_path)
        applications = populate_applications_from_config(config_file_path)
        
        # Track deployment creation (call the function once but track each application)
        try:
            create_deployments(applications, environments, app_environments, headers)
            for app in applications:
                app_name = app.get('AppName', 'Unknown Application')
                track_operation('deployments', 'create_deployment', app_name, True)
        except Exception as e:
            for app in applications:
                app_name = app.get('AppName', 'Unknown Application')
                track_operation('deployments', 'create_deployment', app_name, False, str(e))
        print(f"[Diagnostic] [Deployment] Time Taken: {time.time() - start_time}")
        start_time = time.time()

    if action_autolink_deploymentset:
        print("Performing autolink deployment set action")
        execution_report['actions_performed'].append('Autolink Deployment')
        environments = populate_environments_from_env_groups_from_config(config_file_path)
        applications = populate_applications_from_config(config_file_path)
        
        try:
            create_autolink_deployments(applications, environments, headers)
            track_operation('deployments', 'create_autolink_deployments', f"{len(applications)} applications", True)
        except Exception as e:
            track_operation('deployments', 'create_autolink_deployments', f"{len(applications)} applications", False, str(e))
        print(f"[Diagnostic] [Autolink deploymentset] Time Taken: {time.time() - start_time}")
        start_time = time.time()

    if action_autocreate_teams_from_pteam:
        print("Performing autocreate teams from pteam")
        execution_report['actions_performed'].append('Autocreate Teams from PTeam')
        environments = populate_environments_from_env_groups_from_config(config_file_path)
        applications = populate_applications_from_config(config_file_path)
        
        try:
            create_teams_from_pteams(applications, environments, pteams, access_token)
            track_operation('teams', 'create_teams_from_pteams', f"{len(applications)} applications", True)
        except Exception as e:
            track_operation('teams', 'create_teams_from_pteams', f"{len(applications)} applications", False, str(e))
        print(f"[Diagnostic] [Autocreate teams from pteam] Time Taken: {time.time() - start_time}")
        start_time = time.time()

    if action_create_components_from_assets:
        print("Performing create components/services from assets")
        execution_report['actions_performed'].append('Create Components from Assets')
        
        try:
            auto_created_components = create_components_from_assets(app_environments, phoenix_components, headers)
            track_operation('components', 'create_components_from_assets', f"{len(phoenix_components)} components", True)
            
            # Save auto-created components to YAML file
            if auto_created_components:
                yaml_file_path = save_auto_created_components_to_yaml(auto_created_components)
                if yaml_file_path:
                    execution_report['auto_created_components_file'] = yaml_file_path
                    execution_report['auto_created_components_count'] = len(auto_created_components)
            else:
                print("ℹ️  No components were auto-created during this run")
                
        except Exception as e:
            track_operation('components', 'create_components_from_assets', f"{len(phoenix_components)} components", False, str(e))
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
    parser.add_argument("--create_users_from_responsable", type=str, default="true",
                        required=False, help="Flag to enable automatic user creation from application 'Responsable' field (default: true)")
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
    parser.add_argument("--clear-logs", action="store_true", help="Clear all error logs and exit")
    parser.add_argument("--debug-save-response", action="store_true", 
                        help="Save sample JSON responses for each API operation type (deployment, component, application, team operations)")
    parser.add_argument("--json-to-save", type=int, default=10,
                        help="Number of JSON responses to save for each operation type (default: 10, use 0 for unlimited)")
    parser.add_argument("--quick-check", type=int, default=10,
                        help="Enable quick-check mode: validate service creation every N services (default: 10, use 1 to validate every service)")
    parser.add_argument("--silent", action="store_true",
                        help="Enable silent mode: suppress service creation validation during processing, only validate at the end")
    
    # Parse arguments
    args = parser.parse_args()

    # Handle --clear-logs flag early (before any other processing)
    if getattr(args, 'clear_logs', False):
        print("🧹 Clearing all error logs...")
        success = clear_error_logs()
        if success:
            print("✅ Log clearing completed successfully")
        else:
            print("❌ Log clearing completed with errors")
        exit(0)

    # Set DEBUG mode in all relevant modules if --verbose is passed
    if args.verbose:
        phoenix_module.DEBUG = True
        import providers.YamlHelper as yaml_helper_module
        yaml_helper_module.DEBUG = True
    
    # Set debug response saving mode if flag is passed
    if getattr(args, 'debug_save_response', False):
        phoenix_module.DEBUG_SAVE_RESPONSE = True
        phoenix_module.DEBUG_JSON_TO_SAVE = getattr(args, 'json_to_save', 10)
        
        # Initialize debug session with API domain
        api_domain = getattr(args, 'api_domain', phoenix_module.APIdomain)
        phoenix_module.initialize_debug_session(api_domain)
        
        if phoenix_module.DEBUG_JSON_TO_SAVE == 0:
            print("🐛 Debug response saving enabled - API responses will be saved with unlimited responses per operation type")
        else:
            print(f"🐛 Debug response saving enabled - saving up to {phoenix_module.DEBUG_JSON_TO_SAVE} responses per operation type")

    # Initialize report tracking
    execution_report['total_start_time'] = datetime.now()
    config_files = get_config_files(args.github_pat)
    execution_report['config_files'] = config_files
    
    print(f"🚀 Starting Phoenix AutoConfig execution at {execution_report['total_start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂 Processing {len(config_files)} configuration file(s)")
    
    for config_file in config_files:
        try:
            print(f"Started processing config file {config_file}")
            perform_actions(args, config_file)
            print(f"Finished processing config file {config_file}")
            track_operation('config_files', 'process_config_file', os.path.basename(config_file), True)
        except Exception as e:
            error_msg = f"Error performing actions for {config_file}: {str(e)}"
            print(f"❌ {error_msg}")
            print(f"Full traceback: {traceback.format_exc()}")
            
            # Track the error in our report
            track_operation('config_files', 'process_config_file', os.path.basename(config_file), False, error_msg)
            
            phoenix_module.log_error(
                "Perform actions",
                config_file,
                "N/A",
                "Error performing actions",
                traceback.format_exc()
            )
    
    # Generate final execution report
    print(f"\n🏁 Execution completed. Generating report...")
    generate_execution_report()
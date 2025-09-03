#!/usr/bin/env python3
"""
Dry Run Test Script for Phoenix AutoConfig

This script simulates the run-phx.py execution with your specific parameters
but without making actual API calls to Phoenix. Perfect for testing configuration
loading and validation.

Usage:
    python3 test_dry_run.py [same arguments as run-phx.py]

Example (simulating your command):
    python3 test_dry_run.py #KEY pat1_PAT \\
        --action_teams false --action_code true --action_cloud false --action_deployment false \\
        --action_autolink_deploymentset false --action_autocreate_teams_from_pteam false \\
        --action_create_components_from_assets false --api_domain https://api.COMPANY2.securityphoenix.cloud \\
        @run-config.yaml @core-structure-COMPANY2-7.yaml
"""

import os
import sys
import argparse
import yaml
import traceback
from datetime import datetime

# Add the providers path to sys.path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'providers'))

from YamlHelper import (
    load_run_config, populate_teams, populate_hives, 
    populate_applications_from_config, populate_environments_from_env_groups_from_config,
    populate_repositories_from_config, populate_all_access_emails_from_config
)
from Linter import validate_application, validate_component, validate_environment, validate_service


class DryRunTester:
    def __init__(self):
        self.resource_folder = os.path.join(os.path.dirname(__file__), 'Resources')
        self.test_results = {
            'config_loading': {'success': False, 'error': None},
            'teams_loading': {'success': False, 'error': None, 'count': 0},
            'applications_loading': {'success': False, 'error': None, 'count': 0},
            'environments_loading': {'success': False, 'error': None, 'count': 0},
            'validation_results': {'applications': 0, 'components': 0, 'environments': 0, 'services': 0}
        }

    def test_config_loading(self):
        """Test loading run-config.yaml"""
        print("🔍 Testing run-config.yaml loading...")
        try:
            config = load_run_config(self.resource_folder)
            self.test_results['config_loading']['success'] = True
            
            print("✅ run-config.yaml loaded successfully")
            print(f"   📂 Config files to use: {len(config.get('ConfigFiles', []))}")
            for cf in config.get('ConfigFiles', []):
                print(f"     • {cf}")
            
            print(f"   👥 Teams folder: {config.get('TeamsFolder', 'Teams')}")
            print(f"   🏢 Hives enabled: {config.get('EnableHives', True)}")
            print(f"   🔗 GitHub repos: {len(config.get('GitHubRepositories', []))}")
            
            return config
        except Exception as e:
            self.test_results['config_loading']['error'] = str(e)
            print(f"❌ Failed to load run-config.yaml: {e}")
            return None

    def test_teams_loading(self):
        """Test loading team configurations"""
        print("\n👥 Testing teams loading...")
        try:
            teams = populate_teams(self.resource_folder)
            hives = populate_hives(self.resource_folder)
            
            self.test_results['teams_loading']['success'] = True
            self.test_results['teams_loading']['count'] = len(teams)
            
            print(f"✅ Teams loaded successfully: {len(teams)} teams")
            print(f"✅ Hives loaded successfully: {len(hives)} hive members")
            
            if teams:
                print("   Sample teams:")
                for team in teams[:3]:  # Show first 3 teams
                    team_name = team.get('TeamName', team.get('AzureDevopsAreaPath', 'Unknown'))
                    members = len(team.get('TeamMembers', []))
                    print(f"     • {team_name} ({members} members)")
            
            return teams, hives
        except Exception as e:
            self.test_results['teams_loading']['error'] = str(e)
            print(f"❌ Failed to load teams: {e}")
            return [], []

    def test_config_file_loading(self, config_file_path):
        """Test loading a specific configuration file"""
        print(f"\n📄 Testing configuration file: {os.path.relpath(config_file_path, self.resource_folder)}")
        
        if not os.path.exists(config_file_path):
            print(f"❌ Configuration file not found: {config_file_path}")
            return False
        
        try:
            # Test applications loading
            print("  🏗️  Testing applications loading...")
            applications = populate_applications_from_config(config_file_path)
            self.test_results['applications_loading']['success'] = True
            self.test_results['applications_loading']['count'] = len(applications)
            print(f"     ✅ {len(applications)} applications loaded")
            
            # Test environments loading
            print("  🌍 Testing environments loading...")
            environments = populate_environments_from_env_groups_from_config(config_file_path)
            self.test_results['environments_loading']['success'] = True
            self.test_results['environments_loading']['count'] = len(environments)
            print(f"     ✅ {len(environments)} environments loaded")
            
            # Test repositories loading
            print("  📁 Testing repositories loading...")
            repositories = populate_repositories_from_config(config_file_path)
            print(f"     ✅ {len(repositories)} repositories loaded")
            
            # Test all access emails loading
            print("  📧 Testing all-access emails loading...")
            all_access_emails = populate_all_access_emails_from_config(config_file_path)
            print(f"     ✅ {len(all_access_emails)} all-access emails loaded")
            
            return True
            
        except Exception as e:
            print(f"     ❌ Failed to load configuration: {e}")
            if "validate" in str(e).lower():
                print("     💡 This might be a validation error - check your YAML structure")
            return False

    def test_validation(self, config_file_path):
        """Test configuration validation using linter"""
        print(f"\n🔍 Testing validation for: {os.path.relpath(config_file_path, self.resource_folder)}")
        
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            validation_errors = []
            
            # Validate applications
            if 'DeploymentGroups' in config:
                print(f"  📦 Validating {len(config['DeploymentGroups'])} applications...")
                for app in config['DeploymentGroups']:
                    is_valid, errors = validate_application(app)
                    if is_valid:
                        self.test_results['validation_results']['applications'] += 1
                    else:
                        validation_errors.append(f"Application '{app.get('AppName', 'Unknown')}': {errors}")
                    
                    # Validate components
                    if 'Components' in app:
                        for component in app['Components']:
                            is_valid, errors = validate_component(component)
                            if is_valid:
                                self.test_results['validation_results']['components'] += 1
                            else:
                                validation_errors.append(f"Component '{component.get('ComponentName', 'Unknown')}': {errors}")
            
            # Validate environments
            if 'Environment Groups' in config:
                print(f"  🌍 Validating {len(config['Environment Groups'])} environments...")
                for env in config['Environment Groups']:
                    is_valid, errors = validate_environment(env)
                    if is_valid:
                        self.test_results['validation_results']['environments'] += 1
                    else:
                        validation_errors.append(f"Environment '{env.get('Name', 'Unknown')}': {errors}")
                    
                    # Validate services
                    if 'Services' in env:
                        for service in env['Services']:
                            is_valid, errors = validate_service(service)
                            if is_valid:
                                self.test_results['validation_results']['services'] += 1
                            else:
                                validation_errors.append(f"Service '{service.get('Service', 'Unknown')}': {errors}")
            
            if validation_errors:
                print(f"  ⚠️  Found {len(validation_errors)} validation errors:")
                for error in validation_errors[:5]:  # Show first 5 errors
                    print(f"     • {error}")
                if len(validation_errors) > 5:
                    print(f"     ... and {len(validation_errors) - 5} more errors")
                return False
            else:
                print("  ✅ All validations passed")
                return True
                
        except Exception as e:
            print(f"  ❌ Validation failed: {e}")
            return False

    def get_config_files_to_test(self):
        """Get configuration files from run-config.yaml"""
        try:
            config = load_run_config(self.resource_folder)
            config_files = []
            
            for config_path in config.get('ConfigFiles', []):
                if config_path.startswith('/'):
                    config_path = config_path[1:]  # Remove leading slash
                full_path = os.path.join(self.resource_folder, config_path)
                config_files.append(full_path)
            
            return config_files
        except Exception as e:
            print(f"❌ Failed to get config files: {e}")
            return []

    def print_summary(self):
        """Print test summary"""
        print(f"\n{'='*80}")
        print(f"📊 DRY RUN TEST SUMMARY")
        print(f"{'='*80}")
        
        # Configuration loading results
        config_status = "✅" if self.test_results['config_loading']['success'] else "❌"
        print(f"{config_status} Configuration Loading: {'SUCCESS' if self.test_results['config_loading']['success'] else 'FAILED'}")
        
        teams_status = "✅" if self.test_results['teams_loading']['success'] else "❌"
        print(f"{teams_status} Teams Loading: {'SUCCESS' if self.test_results['teams_loading']['success'] else 'FAILED'}")
        if self.test_results['teams_loading']['success']:
            print(f"   👥 {self.test_results['teams_loading']['count']} teams loaded")
        
        apps_status = "✅" if self.test_results['applications_loading']['success'] else "❌"
        print(f"{apps_status} Applications Loading: {'SUCCESS' if self.test_results['applications_loading']['success'] else 'FAILED'}")
        if self.test_results['applications_loading']['success']:
            print(f"   🏗️  {self.test_results['applications_loading']['count']} applications loaded")
        
        envs_status = "✅" if self.test_results['environments_loading']['success'] else "❌"
        print(f"{envs_status} Environments Loading: {'SUCCESS' if self.test_results['environments_loading']['success'] else 'FAILED'}")
        if self.test_results['environments_loading']['success']:
            print(f"   🌍 {self.test_results['environments_loading']['count']} environments loaded")
        
        # Validation results
        validation_results = self.test_results['validation_results']
        total_validated = sum(validation_results.values())
        print(f"\n🔍 Validation Results: {total_validated} items validated")
        print(f"   📦 Applications: {validation_results['applications']}")
        print(f"   🔧 Components: {validation_results['components']}")
        print(f"   🌍 Environments: {validation_results['environments']}")
        print(f"   🛠️  Services: {validation_results['services']}")
        
        # Overall result
        all_tests_passed = (
            self.test_results['config_loading']['success'] and
            self.test_results['teams_loading']['success'] and
            self.test_results['applications_loading']['success'] and
            self.test_results['environments_loading']['success']
        )
        
        if all_tests_passed:
            print(f"\n🎉 ALL TESTS PASSED! Configuration is ready for actual deployment.")
            print(f"💡 You can now run the actual command with confidence:")
            print(f"   python3 run-phx.py [your-client-id] [your-client-secret] [your-parameters]")
        else:
            print(f"\n⚠️  SOME TESTS FAILED. Please fix configuration issues before deployment.")
        
        return all_tests_passed

    def run_dry_run_test(self):
        """Run the complete dry run test"""
        print(f"🚀 Phoenix AutoConfig - Dry Run Test")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Resource folder: {self.resource_folder}")
        
        # Test basic configuration loading
        config = self.test_config_loading()
        if not config:
            return False
        
        # Test teams loading
        teams, hives = self.test_teams_loading()
        
        # Test configuration files
        config_files = self.get_config_files_to_test()
        
        if not config_files:
            print("❌ No configuration files found to test")
            return False
        
        print(f"\n📄 Testing {len(config_files)} configuration file(s):")
        
        all_passed = True
        for config_file in config_files:
            # Test loading
            load_success = self.test_config_file_loading(config_file)
            all_passed = all_passed and load_success
            
            # Test validation
            if load_success:
                validation_success = self.test_validation(config_file)
                all_passed = all_passed and validation_success
        
        # Print summary
        summary_passed = self.print_summary()
        
        return all_passed and summary_passed


def main():
    parser = argparse.ArgumentParser(
        description="Dry run test for Phoenix AutoConfig (simulates run-phx.py without API calls)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script tests your configuration loading and validation without making actual API calls.
All the normal run-phx.py arguments are accepted but ignored for this dry run test.

Example:
  python3 test_dry_run.py 14b3d7dc-b6ee-41af-98fe-14c502bf332c pat1_492552c3c9174826bbec609a34f33aa589b7dbfcf0ab40e68cb913c17f13f71f \\
      --action_teams false --action_code true --action_cloud false --action_deployment false \\
      --action_autolink_deploymentset false --action_autocreate_teams_from_pteam false \\
      --action_create_components_from_assets false --api_domain https://api.COMPANY2.securityphoenix.cloud
        """
    )
    
    # Accept all the same arguments as run-phx.py but ignore them for dry run
    parser.add_argument("client_id", nargs='?', default="test-client-id", help="Client ID (ignored in dry run)")
    parser.add_argument("client_secret", nargs='?', default="test-client-secret", help="Client Secret (ignored in dry run)")
    parser.add_argument("--github_pat", type=str, help="GitHub Personal Access Token (ignored in dry run)")
    parser.add_argument("--api_domain", type=str, help="Phoenix API domain (ignored in dry run)")
    parser.add_argument("--action_teams", type=str, default="false", help="Flag triggering teams action (ignored in dry run)")
    parser.add_argument("--action_create_users_from_teams", type=str, default="false", help="Flag triggering automatic user creation from team configuration (ignored in dry run)")
    parser.add_argument("--action_code", type=str, default="false", help="Flag triggering code action (ignored in dry run)")
    parser.add_argument("--action_cloud", type=str, default="false", help="Flag triggering cloud action (ignored in dry run)")
    parser.add_argument("--action_deployment", type=str, default="false", help="Flag triggering deployment action (ignored in dry run)")
    parser.add_argument("--action_autolink_deploymentset", type=str, default="false", help="Flag triggering autolink deploymentset action (ignored in dry run)")
    parser.add_argument("--action_autocreate_teams_from_pteam", type=str, default="false", help="Flag triggering autocreate teams from pteam action (ignored in dry run)")
    parser.add_argument("--action_create_components_from_assets", type=str, default="false", help="Flag triggering create components from assets action (ignored in dry run)")
    parser.add_argument("--action_create_components_from_assets_tag", type=str, default="false", help="Flag triggering create components from assets action (tag-based grouping) (ignored in dry run)")
    parser.add_argument("--type", type=str, choices=["all", "cloud", "code", "infrastructure", "web"], help="Asset type to process (ignored in dry run)")
    parser.add_argument("--tag-base", type=str, help="Base tag key for tag-based grouping (ignored in dry run)")
    parser.add_argument("--tag-alternative", type=str, help="Alternative tag keys for tag-based grouping (ignored in dry run)")
    parser.add_argument("--create_automatically_groups", type=str, choices=["yes", "no"], default="no", help="Create automatically groups (ignored in dry run)")
    parser.add_argument("--silent", action="store_true", help="Skip confirmation prompts (ignored in dry run)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug output (ignored in dry run)")
    
    args = parser.parse_args()
    
    print("ℹ️  NOTE: This is a DRY RUN test. All API-related arguments are ignored.")
    print("ℹ️  This test validates configuration loading and YAML structure only.\n")
    
    # Create and run dry run tester
    tester = DryRunTester()
    success = tester.run_dry_run_test()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

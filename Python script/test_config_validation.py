#!/usr/bin/env python3
"""
Configuration Validation Test Script for Phoenix AutoConfig

This script provides a comprehensive way to test YAML configuration files
using the linter validation without making actual API calls to Phoenix.

Usage:
    python3 test_config_validation.py [config_file] [--detailed] [--summary-only]

Examples:
    # Test the configuration specified in run-config.yaml
    python3 test_config_validation.py

    # Test a specific configuration file
    python3 test_config_validation.py Resources/COMPANY2/core-structure-COMPANY2-7.yaml

    # Test with detailed output
    python3 test_config_validation.py --detailed

    # Test with summary only (no individual validation messages)
    python3 test_config_validation.py --summary-only
"""

import os
import sys
import yaml
import argparse
from datetime import datetime

# Add the providers path to sys.path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'providers'))

from Linter import (
    validate_application, 
    validate_component, 
    validate_environment, 
    validate_service,
    validate_multi_condition_rule
)
from YamlHelper import load_run_config


class ConfigValidator:
    def __init__(self, detailed=False, summary_only=False):
        self.detailed = detailed
        self.summary_only = summary_only
        self.resource_folder = os.path.join(os.path.dirname(__file__), 'Resources')
        self.validation_results = {
            'applications': {'valid': 0, 'invalid': 0, 'errors': []},
            'components': {'valid': 0, 'invalid': 0, 'errors': []},
            'environments': {'valid': 0, 'invalid': 0, 'errors': []},
            'services': {'valid': 0, 'invalid': 0, 'errors': []},
            'multi_condition_rules': {'valid': 0, 'invalid': 0, 'errors': []}
        }

    def print_validation_result(self, name, item_type, result, errors=None):
        """Print validation result with appropriate formatting"""
        if self.summary_only:
            return
            
        status = "✅ VALID" if result else "❌ INVALID"
        print(f"\n{status}: {item_type} '{name}'")
        
        if not result and errors and self.detailed:
            print(f"  Errors: {errors}")

    def validate_config_file(self, config_file_path):
        """Validate a single configuration file"""
        print(f"\n{'='*80}")
        print(f"🔍 VALIDATING: {os.path.relpath(config_file_path, self.resource_folder)}")
        print(f"{'='*80}")
        
        if not os.path.exists(config_file_path):
            print(f"❌ ERROR: Configuration file not found: {config_file_path}")
            return False
        
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            print(f"❌ ERROR: Failed to parse YAML file: {e}")
            return False
        
        if not config:
            print(f"⚠️  WARNING: Configuration file is empty or contains no data")
            return False
        
        # Validate Applications (DeploymentGroups)
        if 'DeploymentGroups' in config:
            print(f"\n📦 VALIDATING APPLICATIONS ({len(config['DeploymentGroups'])} found)")
            for app in config['DeploymentGroups']:
                app_name = app.get('AppName', 'Unknown Application')
                is_valid, errors = validate_application(app)
                
                if is_valid:
                    self.validation_results['applications']['valid'] += 1
                else:
                    self.validation_results['applications']['invalid'] += 1
                    self.validation_results['applications']['errors'].append({
                        'name': app_name,
                        'errors': errors
                    })
                
                self.print_validation_result(app_name, "Application", is_valid, errors)
                
                # Validate Components within this Application
                if 'Components' in app and app['Components']:
                    for component in app['Components']:
                        comp_name = component.get('ComponentName', 'Unknown Component')
                        is_valid, errors = validate_component(component)
                        
                        if is_valid:
                            self.validation_results['components']['valid'] += 1
                        else:
                            self.validation_results['components']['invalid'] += 1
                            self.validation_results['components']['errors'].append({
                                'name': f"{app_name}/{comp_name}",
                                'errors': errors
                            })
                        
                        self.print_validation_result(comp_name, "Component", is_valid, errors)
        
        # Validate Environments (Environment Groups)
        if 'Environment Groups' in config:
            print(f"\n🌍 VALIDATING ENVIRONMENTS ({len(config['Environment Groups'])} found)")
            for env in config['Environment Groups']:
                env_name = env.get('Name', 'Unknown Environment')
                is_valid, errors = validate_environment(env)
                
                if is_valid:
                    self.validation_results['environments']['valid'] += 1
                else:
                    self.validation_results['environments']['invalid'] += 1
                    self.validation_results['environments']['errors'].append({
                        'name': env_name,
                        'errors': errors
                    })
                
                self.print_validation_result(env_name, "Environment", is_valid, errors)
                
                # Validate Services within this Environment
                if 'Services' in env and env['Services']:
                    for service in env['Services']:
                        service_name = service.get('Service', 'Unknown Service')
                        is_valid, errors = validate_service(service)
                        
                        if is_valid:
                            self.validation_results['services']['valid'] += 1
                        else:
                            self.validation_results['services']['invalid'] += 1
                            self.validation_results['services']['errors'].append({
                                'name': f"{env_name}/{service_name}",
                                'errors': errors
                            })
                        
                        self.print_validation_result(service_name, "Service", is_valid, errors)
                        
                        # Validate Multi-Condition Rules within Services
                        if 'MULTI_MultiConditionRules' in service:
                            for i, mcr in enumerate(service['MULTI_MultiConditionRules']):
                                is_valid, errors = validate_multi_condition_rule(mcr)
                                mcr_name = f"{service_name}/MCR-{i+1}"
                                
                                if is_valid:
                                    self.validation_results['multi_condition_rules']['valid'] += 1
                                else:
                                    self.validation_results['multi_condition_rules']['invalid'] += 1
                                    self.validation_results['multi_condition_rules']['errors'].append({
                                        'name': mcr_name,
                                        'errors': errors
                                    })
                                
                                self.print_validation_result(mcr_name, "Multi-Condition Rule", is_valid, errors)
        
        return True

    def get_config_files_to_test(self, config_file=None):
        """Get list of configuration files to test"""
        if config_file:
            # Test specific file
            if os.path.isabs(config_file):
                return [config_file]
            else:
                return [os.path.join(self.resource_folder, config_file)]
        
        # Load from run-config.yaml
        try:
            run_config = load_run_config(self.resource_folder)
            config_files = []
            
            for config_path in run_config.get('ConfigFiles', []):
                if config_path.startswith('/'):
                    config_path = config_path[1:]  # Remove leading slash
                full_path = os.path.join(self.resource_folder, config_path)
                config_files.append(full_path)
            
            return config_files
        except Exception as e:
            print(f"❌ ERROR: Failed to load run-config.yaml: {e}")
            return []

    def print_summary(self):
        """Print validation summary"""
        print(f"\n{'='*80}")
        print(f"📊 VALIDATION SUMMARY")
        print(f"{'='*80}")
        
        total_valid = 0
        total_invalid = 0
        
        for category, results in self.validation_results.items():
            valid = results['valid']
            invalid = results['invalid']
            total = valid + invalid
            
            if total > 0:
                success_rate = (valid / total) * 100
                status_icon = "✅" if success_rate == 100 else "⚠️" if success_rate >= 80 else "❌"
                
                print(f"{status_icon} {category.upper()}: {valid}/{total} valid ({success_rate:.1f}%)")
                
                if invalid > 0 and self.detailed:
                    print(f"   Failed items:")
                    for error in results['errors'][:5]:  # Show first 5 errors
                        print(f"     • {error['name']}: {error['errors']}")
                    if len(results['errors']) > 5:
                        print(f"     ... and {len(results['errors']) - 5} more")
                
                total_valid += valid
                total_invalid += invalid
        
        overall_total = total_valid + total_invalid
        if overall_total > 0:
            overall_success_rate = (total_valid / overall_total) * 100
            print(f"\n🎯 OVERALL: {total_valid}/{overall_total} items valid ({overall_success_rate:.1f}%)")
        
        if total_invalid == 0:
            print(f"\n🎉 ALL CONFIGURATIONS ARE VALID! Ready for deployment.")
        else:
            print(f"\n⚠️  {total_invalid} validation errors found. Please fix before deployment.")
        
        return total_invalid == 0

    def run_validation(self, config_file=None):
        """Run the full validation process"""
        print(f"🚀 Phoenix AutoConfig - Configuration Validation")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        config_files = self.get_config_files_to_test(config_file)
        
        if not config_files:
            print(f"❌ No configuration files found to validate")
            return False
        
        print(f"📂 Testing {len(config_files)} configuration file(s):")
        for cf in config_files:
            print(f"   • {os.path.relpath(cf, self.resource_folder)}")
        
        all_valid = True
        for config_file_path in config_files:
            file_valid = self.validate_config_file(config_file_path)
            all_valid = all_valid and file_valid
        
        summary_valid = self.print_summary()
        
        return all_valid and summary_valid


def main():
    parser = argparse.ArgumentParser(
        description="Validate Phoenix AutoConfig YAML configuration files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 test_config_validation.py
  python3 test_config_validation.py Resources/COMPANY2/core-structure-COMPANY2-7.yaml
  python3 test_config_validation.py --detailed
  python3 test_config_validation.py --summary-only
        """
    )
    
    parser.add_argument('config_file', nargs='?', 
                       help='Specific configuration file to validate (optional)')
    parser.add_argument('--detailed', action='store_true',
                       help='Show detailed error messages for failed validations')
    parser.add_argument('--summary-only', action='store_true',
                       help='Show only the summary, skip individual validation messages')
    
    args = parser.parse_args()
    
    # Create validator
    validator = ConfigValidator(detailed=args.detailed, summary_only=args.summary_only)
    
    # Run validation
    success = validator.run_validation(args.config_file)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

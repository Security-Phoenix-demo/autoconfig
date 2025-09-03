# Phoenix AutoConfig - Testing Guide

This guide explains how to test your Phoenix AutoConfig configuration before deploying it to production.

## 🎯 Quick Start

You want to test this command:
```bash
python3 run-phx.py Key pat1_PAT \
  --action_teams false --action_code true --action_cloud false --action_deployment false \
  --action_autolink_deploymentset false --action_autocreate_teams_from_pteam false \
  --action_create_components_from_assets false \
  --api_domain https://api.COMPANY2.securityphoenix.cloud \
  @run-config.yaml @core-structure-COMPANY2-7.yaml
```

**First, test your configuration:**

```bash
# Navigate to the Python script directory
cd "Python script"

# Run the dry run test (no API calls made)
python3 test_dry_run.py
```

## 🛠️ Available Testing Tools

### 1. Configuration Validation (`test_config_validation.py`)

Validates your YAML configuration files using the built-in linter:

```bash
# Test all configurations from run-config.yaml
python3 test_config_validation.py

# Test a specific file
python3 test_config_validation.py Resources/COMPANY2/core-structure-COMPANY2-7.yaml

# Get detailed error messages
python3 test_config_validation.py --detailed

# Show only summary (no individual validation messages)
python3 test_config_validation.py --summary-only
```

**What it validates:**
- ✅ Applications (DeploymentGroups)
- ✅ Components within applications
- ✅ Environments (Environment Groups)
- ✅ Services within environments
- ✅ Multi-condition rules
- ✅ Required fields and data types
- ✅ Field value constraints

### 2. Dry Run Test (`test_dry_run.py`)

Simulates the actual run-phx.py execution without making API calls:

```bash
# Basic dry run test
python3 test_dry_run.py

# Simulate your exact command (arguments are ignored for testing)
python3 test_dry_run.py 14b3d7dc-b6ee-41af-98fe-14c502bf332c pat1_492552c3c9174826bbec609a34f33aa589b7dbfcf0ab40e68cb913c17f13f71f \
  --action_teams false --action_code true --action_cloud false --action_deployment false \
  --action_autolink_deploymentset false --action_autocreate_teams_from_pteam false \
  --action_create_components_from_assets false \
  --api_domain https://api.COMPANY2.securityphoenix.cloud
```

**What it tests:**
- ✅ run-config.yaml loading
- ✅ Teams configuration loading
- ✅ Configuration file parsing
- ✅ Applications and environments loading
- ✅ Repositories loading
- ✅ All-access emails loading
- ✅ Complete validation pipeline

### 3. Manual Linter Test (Command Line)

Quick validation from command line:

```bash
cd "Python script"
python3 -c "
from providers.Linter import *
import yaml
with open('Resources/COMPANY2/core-structure-COMPANY2-7.yaml', 'r') as f:
    config = yaml.safe_load(f)
for app in config.get('DeploymentGroups', []):
    valid, errors = validate_application(app)
    print(f'{app.get(\"AppName\")}: {\"✅\" if valid else \"❌\" + str(errors)}')
"
```

## 📋 Testing Workflow

### Step 1: Basic Validation
```bash
python3 test_config_validation.py --summary-only
```
If this fails, fix YAML structure issues first.

### Step 2: Detailed Validation
```bash
python3 test_config_validation.py --detailed
```
Review and fix any validation errors.

### Step 3: Complete Dry Run
```bash
python3 test_dry_run.py
```
This tests the complete loading pipeline.

### Step 4: Run Actual Command
Once all tests pass, run your actual command:
```bash
python3 run-phx.py 14b3d7dc-b6ee-41af-98fe-14c502bf332c pat1_492552c3c9174826bbec609a34f33aa589b7dbfcf0ab40e68cb913c17f13f71f \
  --action_teams false --action_code true --action_cloud false --action_deployment false \
  --action_autolink_deploymentset false --action_autocreate_teams_from_pteam false \
  --action_create_components_from_assets false \
  --api_domain https://api.COMPANY2.securityphoenix.cloud
```

## 🔍 Understanding Test Results

### ✅ Success Indicators
- All configurations load without errors
- All validations pass
- No linter errors reported
- Summary shows 100% success rates

### ❌ Common Issues and Solutions

#### YAML Parsing Errors
```
❌ Failed to parse YAML file: ...
```
**Solution:** Check YAML syntax, indentation, and special characters.

#### Validation Errors
```
❌ INVALID: Application 'MyApp'
  Errors: {'AppName': ['required field']}
```
**Solution:** Add missing required fields or fix data types.

#### File Not Found
```
❌ Configuration file not found: Resources/COMPANY2/core-structure-COMPANY2-7.yaml
```
**Solution:** Check file paths in run-config.yaml and verify files exist.

#### Linter Schema Errors
```
❌ Linter errors: {'TeamNames': ['must be of list type']}
```
**Solution:** Fix data types (e.g., convert string to list).

## 📁 Your Configuration Setup

Based on your current setup:
- **Run Config:** `Resources/run-config.yaml`
- **Main Config:** `Resources/COMPANY2/core-structure-COMPANY2-7.yaml`
- **Teams Folder:** `Resources/COMPANY2/COMPANY2-Teams`
- **Hives:** Disabled (`EnableHives: false`)

## 🚨 Important Notes

1. **Always test before production:** Run validation tests before deploying to production Phoenix instances.

2. **API credentials:** The test scripts don't require real API credentials - they test configuration loading only.

3. **No API calls:** All test scripts are safe to run - they don't make any actual API calls to Phoenix.

4. **Exit codes:** Scripts return 0 for success, 1 for failure - useful for CI/CD pipelines.

5. **Verbose output:** Add `--verbose` to the actual run-phx.py command for detailed debugging.

## 💡 Pro Tips

- Run `test_config_validation.py` after any configuration changes
- Use `test_dry_run.py` to verify the complete loading pipeline
- Keep validation error messages for troubleshooting
- Test in a staging environment before production deployment

## 🆘 Getting Help

If tests fail:
1. Check the error messages carefully
2. Verify YAML syntax and structure
3. Ensure all required fields are present
4. Check data types match schema requirements
5. Review file paths and permissions

For complex issues, run with `--detailed` flag to get more diagnostic information.

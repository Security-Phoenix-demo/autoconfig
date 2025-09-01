from cerberus import Validator, schema_registry

schema_registry.add("ticketing_schema", {
                "TIntegrationName": {
                    "type": "string",
                    "required": True
                },
                "Backlog": {
                    "type": "string",
                    "required": True
                }
                })


schema_registry.add("messaging_schema", {
                "MIntegrationName": {
                    "type": "string",
                    "required": True
                },
                "Channel": {
                    "type": "string",
                    "required": True
                }
                })

schema_registry.add('multi_condition_rule_schema',{
                "RepositoryName": {
                    "type": ["string", "list"],
                    "required": False
                },
                "SearchName": {
                    "type": "string",
                    "required": False
                },
                "AssetType": {
                    "type": "string",
                    "required": False,
                    "allowed": [
                        "REPOSITORY", "SOURCE_CODE", "BUILD", "WEBSITE_API", "CONTAINER", "INFRA", "CLOUD", "WEB", "FOSS", "SAST"
                    ]
                },
                "Tag": {
                    "type": ["string", "list"],
                    "required": False
                },
                "Tags": {
                    "type": "list",
                    "required": False, # todo check this
                    "schema": {
                        "type": "string"
                    }
                },
                "Tag_rule": {
                    "type": ["string", "list"],
                    "required": False
                },
                "Tags_rule": {
                    "type": "list",
                    "required": False,
                    "schema": {
                        "type": "string"
                    }
                },
                "Tag_label": {
                    "type": ["string", "list"],
                    "required": False
                },
                "Tags_label": {
                    "type": "list",
                    "required": False,
                    "schema": {
                        "type": "string"
                    }
                },
                "Cidr": {
                    "type": "string",
                    "required": False
                },
                "Fqdn": {
                    "type": "list",
                    "schema": {
                        "type": "string"
                    },
                    "required": False
                },
                "Netbios": {
                    "type": "list",
                    "schema": {
                        "type": "string"
                    },
                    "required": False
                },
                "OsNames": {
                    "type": "list",
                    "schema": {
                        "type": "string"
                    },
                    "required": False
                },
                "Hostnames": {
                    "type": "list",
                    "schema": {
                        "type": "string"
                    },
                    "required": False
                },
                "ProviderAccountId": {
                    "type": "list",
                    "schema": {
                        "type": "string"
                    },
                    "required": False
                },
                "ProviderAccountName": {
                    "type": "list",
                    "schema": {
                        "type": "string"
                    },
                    "required": False
                },
                "ResourceGroup": {
                    "type": "list",
                    "schema": {
                        "type": "string"
                    },
                    "required": False
                }
            })

# Validate a component from a config yaml file
def validate_component(component):
    v = Validator({
        "ComponentName": {
            "type": "string",
            "required": True
        },
        "Status": {
            "type": "string",
            "required": False
        },
        "AppID": {
            "type": "integer",
            "required": False
        },
        "Type": {
            "type": "string",
            "required": False
        },
        "TeamNames": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "Ticketing": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": "ticketing_schema"
            },
            "required": False
        },
        "Messaging": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": "messaging_schema"
            },
            "required": False
        },
        "RepositoryName": {
            "type": ["string", "list"],
            "required": False
        },
        "SearchName": {
            "type": "string",
            "required": False
        },
        "AssetType": {
            "type": "string",
            "required": False,
            "allowed": [
                "REPOSITORY", "SOURCE_CODE", "BUILD", "WEBSITE_API", "CONTAINER", "INFRA", "CLOUD", "WEB", "FOSS", "SAST"
            ]
        },
        "Tags": {
            "type": "list",
            "required": False,
            "schema": {
                "type": "string"
            }
        },
        "Tag_label": {
            "type": ["string", "list"],
            "required": False
        },
        "Tags_label": {
            "type": "list",
            "required": False,
            "schema": {
                "type": "string"
            }
        },
        "Cidr": {
            "type": "string",
            "required": False
        },
        "Fqdn": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "Netbios": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "OsNames": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "Hostnames": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "ProviderAccountId": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "ProviderAccountName": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "ResourceGroup": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "MultiConditionRule": {
            "type": "dict",
            "schema": "multi_condition_rule_schema",
            "required": False
        },
        "MULTI_MultiConditionRules": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": "multi_condition_rule_schema"
            },
            "required": False
        },
        "Tier": {
            "type": "integer",
            "required": False
        },
        "Domain": {
            "type": "string",
            "required": False
        },
        "SubDomain": {
            "type": "string",
            "required": False
        },
        "AutomaticSecurityReview": {
            "type": "boolean",
            "required": False
        },
        "Tag_rule": {
            "type": ["string", "list"],
            "required": False
        },
        "Tags_rule": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "Deployment_set": {
            "type": "string",
            "required": False
        },
        "Ticketing": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": "ticketing_schema"
            },
            "required": False
        },
        "Messaging": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": "messaging_schema"
            },
            "required": False
        }
    }, allow_unknown=False)
    
    try:
        if v.validate(component):
            # Additional custom validation for repository + asset type structure
            structure_valid, structure_errors = validate_repository_asset_structure(component, "component")
            if not structure_valid:
                return (False, {"repository_asset_structure": structure_errors})
            return (True, "")
        return (False, v.errors)
    except Exception as e:
        print(f"Exception occurred while linting component {component}, error: {e}")
        return (False, "Unknown error while linting")


def validate_application(application):
    v = Validator({
        "AppName": {
            "type": "string",
            "required": True
        },
        "AppID": {
            "type": "integer",
            "required": False
        },
        "Status": {
            "type": "string",
            "required": False
        },
        "TeamNames": {
            "type": "list",
            "required": False,
            "schema": {
                "type": "string"
            }
        },
        "Domain": {
            "type": "string",
            "required": False
        },
        "SubDomain": {
            "type": "string",
            "required": False
        },
        "ReleaseDefinitions": {
            "type": "list",
            "required": True
        },
        "Responsable": {
            "type": "string",
            "required": True
        },
        "Tier": {
            "type": "integer",
            "required": False
        },
        "Deployment_set": {
            "type": "string",
            "required": False
        },
        "Ticketing": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": "ticketing_schema"
            },
            "required": False
        },
        "Messaging": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": "messaging_schema"
            },
            "required": False
        },
        "Components": {
            "type": "list",
            "required": False
        },
        "Tag_label": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "Tags_label": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        }
    }, allow_unknown=False)
    
    try:
        if v.validate(application):
            return (True, "")
        return (False, v.errors)
    except Exception as e:
        print(f"Exception occurred while linting application {application}, error: {e}")
        return (False, "Uknown error while linting")


def validate_environment(environment):
    v = Validator({
        "Name": {
            "type": "string",
            "required": True
        },
        "Type": {
            "type": "string",
            "required": True
        },
        "Tier": {
            "type": "integer",
            "required": True
        },
        "Status": {
            "type": "string",
            "required": True
        },
        "Responsable": {
            "type": "string",
            "required": False  # Made optional since we also accept 'Responsible'
        },
        "Responsible": {
            "type": "string", 
            "required": False  # Alternative field name for 'Responsable'
        },
        "TeamName": {
            "type": "string",
            "required": False
        },
        "Tag_label": {
            "type": "list",
            "required": False
        },
        "Ticketing": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": "ticketing_schema"
            },
            "required": False
        },
        "Messaging": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": "messaging_schema"
            },
            "required": False
        },
        "Services": {
            "type": "list",
            "required": False
        }
    }, allow_unknown=False)
    
    try:
        if v.validate(environment):
            # Custom validation: ensure either 'Responsable' or 'Responsible' is present
            if not (environment.get('Responsable') or environment.get('Responsible')):
                return (False, {'Responsable_or_Responsible': ['At least one of Responsable or Responsible is required']})
            return (True, "")
        return (False, v.errors)
    except Exception as e:
        print(f"Exception occurred while linting environment {environment}, error: {e}")
        return (False, "Uknown error while linting")


# Validate a service from a config yaml file
def validate_service(service):
    v = Validator({
        "Service": {
            "type": "string",
            "required": True
        },
        "Type": {
            "type": "string",
            "required": True
        },
        "Tier": {
            "type": "integer",
            "required": False
        },
        "TeamName": {
            "type": "string",
            "required": False
        },
        "Ticketing": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": "ticketing_schema"
            },
            "required": False
        },
        "Messaging": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": "messaging_schema"
            },
            "required": False
        },
        "Deployment_set": {
            "type": "string",
            "required": False
        },
        "Deployment_tag": {
            "type": "string",
            "required": False
        },
        "MultiConditionRule": {
            "type": "dict",
            "schema": "multi_condition_rule_schema",
            "required": False
        },
        "MULTI_MultiConditionRules": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": "multi_condition_rule_schema"
            },
            "required": False
        },
        "MultiMultiConditionRules": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": "multi_condition_rule_schema"
            },
            "required": False
        },
        "MultiConditionRules": {
            "type": "list",
            "schema": {
                "type": "dict",
                "schema": "multi_condition_rule_schema"
            },
            "required": False
        },
        "RepositoryName": {
            "type": ["string", "list"],
            "required": False
        },
        "SearchName": {
            "type": "string",
            "required": False
        },
        "Tag": {
            "type": ["list", "string"],
            "required": False
        },
        "Tag_rule": {
            "type": ["list", "string"],
            "required": False
        },
        "Tags_rule": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "Tag_label": {
            "type": ["string", "list"],
            "required": False
        },
        "Tags_label": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "Cidr": {
            "type": "string",
            "required": False
        },
        "Fqdn": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "Netbios": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "OsNames": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "Hostnames": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "ProviderAccountId": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "ProviderAccountName": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "ResourceGroup": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        },
        "AssetType": {
            "type": "string",
            "required": False,
            "allowed": [
                "REPOSITORY", "SOURCE_CODE", "BUILD", "WEBSITE_API", "CONTAINER", "INFRA", "CLOUD", "WEB", "FOSS", "SAST"
            ]
        },
        "Tags": {
            "type": "list",
            "schema": {
                "type": "string"
            },
            "required": False
        }
    }, allow_unknown=False)
    
    try:
        if v.validate(service):
            # Additional custom validation for repository + asset type structure
            structure_valid, structure_errors = validate_repository_asset_structure(service, "service")
            if not structure_valid:
                return (False, {"repository_asset_structure": structure_errors})
            return (True, "")
        return (False, v.errors)
    except Exception as e:
        print(f"Exception occurred while linting service {service}, error: {e}")
        return (False, "Unknown error while linting")

# Validate a multi-condition rule from a config yaml file
def validate_multi_condition_rule(mcr):
    v = Validator(schema_registry.get('multi_condition_rule_schema'), allow_unknown=False)
    
    try:
        if v.validate(mcr):
            return (True, "")
        return (False, v.errors)
    except Exception as e:
        print(f"Exception occurred while linting multi-condition rule {mcr}, error: {e}")
        return (False, "Unknown error while linting")


# Custom validation rule: Check if RepositoryName + AssetType should be in multi-condition rules
def validate_repository_asset_structure(item, item_type="component"):
    """
    Validates that when both RepositoryName and AssetType are present at the top level,
    they should be contained within a multi-condition rule structure.
    
    Args:
        item: Component or Service dictionary
        item_type: Type of item being validated ("component" or "service")
    
    Returns:
        tuple: (is_valid, error_message)
    """
    errors = []
    
    # Check if both RepositoryName and AssetType are present at the top level
    has_repository_name = 'RepositoryName' in item and item['RepositoryName'] is not None
    has_asset_type = 'AssetType' in item and item['AssetType'] is not None
    
    # Check if multi-condition rules are already present
    has_multi_condition_rules = any([
        'MultiConditionRule' in item,
        'MULTI_MultiConditionRules' in item,
        'MultiConditionRules' in item,
        'MultiMultiConditionRules' in item
    ])
    
    if has_repository_name and has_asset_type:
        if not has_multi_condition_rules:
            # Check if there are multiple repositories (list format)
            repo_name = item['RepositoryName']
            is_multiple_repos = isinstance(repo_name, list) and len(repo_name) > 1
            
            if is_multiple_repos:
                errors.append(
                    f"Multiple repositories detected with AssetType. "
                    f"Use 'MULTI_MultiConditionRules' to define separate rules for each repository: {repo_name}"
                )
            else:
                errors.append(
                    f"Both 'RepositoryName' and 'AssetType' are present at {item_type} level. "
                    f"Consider using 'MultiConditionRule' for single repository or 'MULTI_MultiConditionRules' for multiple repositories."
                )
        else:
            # If multi-condition rules exist, warn about potential duplication
            errors.append(
                f"Warning: Both top-level 'RepositoryName'/'AssetType' and multi-condition rules are present. "
                f"Consider consolidating into multi-condition rules only to avoid conflicts."
            )
    
    # Additional check: If multiple repositories in list format, recommend multi-condition rules
    if has_repository_name and not has_asset_type:
        repo_name = item['RepositoryName']
        if isinstance(repo_name, list) and len(repo_name) > 1:
            errors.append(
                f"Multiple repositories detected without AssetType: {repo_name}. "
                f"Consider using 'MULTI_MultiConditionRules' for better organization and to specify AssetType for each."
            )
    
    return (len(errors) == 0, errors)
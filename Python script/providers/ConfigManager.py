
ENVIRONMENTS = 'environments'
APPLICATIONS = 'applications'


def validate_config_repo(applied_configs, config_repo):
    # This method validates whether config_repo was already applied or needs to be overridden
    # Returns True if config_repo should be applied and False if it shouldn't be applied
    if config_repo in applied_configs:
        print(f'Detected duplicate configuration repo {config_repo}')
        override_repo = input(f'Would you like to override the {config_repo}? [yes | no]')
        if 'yes' == override_repo:
            applied_configs[config_repo] = {}
            return True
        else:
            return False
    applied_configs[config_repo] = {}
    return True

def try_to_add_config(applied_configs, config_repo, config_type, config, prompt_on_duplicate):
    configs_to_not_apply = []
    filtered_configs = []
    for applied_config_key, applied_config_value in applied_configs.copy().items():
        if len(applied_configs) > 1 and applied_config_key == config_repo:
            continue
        if ENVIRONMENTS == config_type:
            for environment in applied_config_value.get(ENVIRONMENTS, []).copy():
                for incomming_env in config:
                    if environment['Name'] == incomming_env['Name']:
                        print(f'Detected environment {incomming_env['Name']} definition in {config_repo} that was already defined in {applied_config_key}')
                        should_include = input(f'Do you want to include the new definition for {incomming_env['Name']}? [yes|no]') if prompt_on_duplicate else 'no'
                        if "no" == should_include:
                            configs_to_not_apply.append(incomming_env['Name'])

            filtered_configs = [x for x in config if x['Name'] not in configs_to_not_apply]
            if config_repo not in applied_configs:
                applied_configs[config_repo] = {}
            applied_configs[config_repo].update({ENVIRONMENTS: filtered_configs})
        if APPLICATIONS == config_type:
            for application in applied_config_value.get(APPLICATIONS, []).copy():
                for incomming_app in config:
                    if application['AppName'] == incomming_app['AppName']:
                        print(f'Detected application {incomming_app['AppName']} definition in {config_repo} that was already defined in {applied_config_key}')
                        should_include = input(f'Do you want to include the new definition for {incomming_app['AppName']}? [yes|no]') if prompt_on_duplicate else 'no'
                        if "no" == should_include:
                            configs_to_not_apply.append(incomming_app['AppName'])
            filtered_configs = [x for x in config if x['AppName'] not in configs_to_not_apply]
            if config_repo not in applied_configs:
                applied_configs[config_repo] = {}
            applied_configs[config_repo].update({APPLICATIONS: filtered_configs})

    return filtered_configs


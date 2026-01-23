There are three key folders:
- _envcommon/
- environments/
- modules/

_envcommon/ contains terragrunt configuration that's shared across multiple environments. This includes boilerplate like loading env variables.

environments/ contains terragrunt .hcl files that define environment specific variables. This is where terragrunt commands should actually be run from.

modules/ contains terraform code that defines the infrastructure that will be deployed.

Env variables are required to deploy. There are located in .env and can be loaded with xargs. You do not need to use `assume` to execute terragrunt commands, as it is handled by the provider configuration.
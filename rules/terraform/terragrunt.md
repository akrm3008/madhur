Aisy uses terraform and terragrunt to manage state across multiple environments and AWS accounts. 

Terragrunt handles creating providers (and an AWS region data source) in root.hcl. You do not need to declare those in terraform modules, other than very specific edge cases.

When calling terragrunt commands, use TG_NON_INTERACTIVE=true.

Terragrunt commands include:
- terragrunt init
- terragrunt plan
- terragrunt apply

ALWAYS run terragrunt plan and ask for user input before running an apply.

You can use terragrunt run --all to run in multiple directories.

Terragrunt commands should be run from `infra-config/environments/<env>/`, e.x. `infra-config/environments/prod/eks-cluster`.
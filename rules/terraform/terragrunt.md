Aisy uses terraform and terragrunt to manage state across multiple environments and AWS accounts. 

Terragrunt handles creating providers (and an AWS region data source) in root.hcl. You do not need to declare those in terraform modules, other than very specific edge cases.
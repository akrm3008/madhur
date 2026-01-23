There are three aws accounts, generally referred to by their profile name:
- aisy-primary (administrative, largely not used, contains terraform and terragrunt state resources)
- aisy-prod (production resources and shared infrastructure)
- aisy-dev (development resources)

Granted is used to manage aws profiles. The easiest way to use this is `assume <profile_name> --exec '<aws_command>'`, e.x. `assume aisy-prod --exec 'aws sts get-caller-identity'`. You can also use `assume <profile_name>` to export the credentials into your shell for the remainder of the session.
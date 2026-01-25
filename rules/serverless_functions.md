Serverless functions are a number of modules of Python code which run on AWS Lambda.

To create a new lambda, you must:
- Create the code in serverless-functions/
- Create a new ECR repo (and cache repo) in infra-config/
- Create a new lambda in infra-config/
- Update the CI config in common-python-utils/ to add the new image config, using the CI CLI command
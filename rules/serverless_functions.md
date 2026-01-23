Serverless functions are a number of modules of Python code which run on AWS Lambda.

To create a new lambda, you must:
- Create the code in serverless-functions/
- Create a new ECR repo (and cache repo) in infra-config/
- Create a new lambda
- Update the existing CI permissions to have permission to push to that ECR repo and update the lambda
- Update the CI config in aisy-common/ to add the new image config
- Update the CI config in argocd-config/ to specify to build the new image
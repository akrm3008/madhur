# Infrastructure Access

## Database Access

- **Host:** localhost:9999
- **Database:** hasura
- **Schema:** public
- **Username:** postgres
- **Auth:** pgpass file (~/.pgpass)

```bash
# Connect to database
PGPASSFILE=~/.pgpass psql -h localhost -p 9999 -U postgres -d hasura

# Run a query
PGPASSFILE=~/.pgpass psql -h localhost -p 9999 -U postgres -d hasura -c "SELECT * FROM table LIMIT 10;"
```

## AWS Access

Use `assume` with `--exec` to run commands with AWS credentials:

```bash
# Open a subshell with credentials
assume aisy-dev --exec bash

# Or run a single command
assume aisy-dev --exec "aws sts get-caller-identity"
```

**Note:** Don't rely on `assume` setting env vars in current shell - stale credentials in `~/.aws/credentials` may override. Always use `--exec` flag.

## Docker / ECR Access

**ECR Registry:** `780193927358.dkr.ecr.eu-west-1.amazonaws.com`

**Available Repositories:**
- `prefect-domain-collection` - Domain collection flows
- `prefect-content-discovery` - Content discovery flows

### ECR Login

Pipes don't work directly with `assume --exec`. Use a script file:

```bash
# Create login script (do this once)
cat > /tmp/ecr_login.sh << 'EOF'
#!/bin/bash
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin 780193927358.dkr.ecr.eu-west-1.amazonaws.com
EOF
chmod +x /tmp/ecr_login.sh

# Login to ECR
assume aisy-dev --exec "/tmp/ecr_login.sh"
```

### Pull Images

```bash
# Pull domain collection image
docker pull 780193927358.dkr.ecr.eu-west-1.amazonaws.com/prefect-domain-collection:latest

# Pull content discovery image
docker pull 780193927358.dkr.ecr.eu-west-1.amazonaws.com/prefect-content-discovery:latest
```

### Inspect Container Contents

```bash
# Check if a file exists in the image
docker run --rm 780193927358.dkr.ecr.eu-west-1.amazonaws.com/prefect-domain-collection:latest \
  ls -la /app/asm-prefect/configurations/

# Run a shell to explore
docker run -it --rm 780193927358.dkr.ecr.eu-west-1.amazonaws.com/prefect-domain-collection:latest bash
```

## Running Tests in Docker

To test code changes before deployment, you can run containers locally:

```bash
# Run a specific flow/task in the container
docker run -it --rm \
  -v /path/to/local/code:/app/asm-prefect-dev \
  780193927358.dkr.ecr.eu-west-1.amazonaws.com/prefect-content-discovery:latest \
  python -c "from module import function; function()"
```

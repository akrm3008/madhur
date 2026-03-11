# Infrastructure Access

## Daily Setup Script

Run this every morning (or whenever tunnels/credentials expire) to set up the dev environment. **WSL only** — this script is designed for Windows Subsystem for Linux and will not work on macOS or native Linux.

**Interactive (user's terminal):**
```bash
cd <aisy_root>/common-python-utils
source ./scripts/wsl/aisy-setup.sh dev   # or "prod" for production
```

**Non-interactive (Claude Code) — ask the user for their sudo password first:**
```bash
cd <aisy_root>/common-python-utils && bash -c 'source ./scripts/wsl/aisy-setup.sh dev' <<< "<sudo_password>" 2>&1
```

Pass the sudo password via here-string (`<<<`) so the script reads it on stdin. Claude Code has no TTY, so sudo credential caching doesn't work — the password must be fed directly to the script.

The script handles: AWS SSO auth, DB password retrieval from Secrets Manager, cloudflared RDS tunnel (`localhost:9999`), EFS tunnel + mount (`/mnt/efs`), Prefect profile, and `~/.pgpass` update.

## Hasura Metadata

Metadata deploys are handled by CI on push to `dev`/`main`. For local operations use `aisy-hasura/scripts/metadata.sh`:

```bash
./scripts/metadata.sh dev          # Check inconsistencies (default)
./scripts/metadata.sh dev export   # Export server metadata
./scripts/metadata.sh dev diff     # Diff local vs server
./scripts/metadata.sh dev apply    # Apply locally (prefer CI via push)
```

**Codegen note:** `app-frontend/` codegen uses a local `schema.graphql` file, not remote introspection. When adding new Hasura actions, you must also update the local `schema.graphql` for codegen to succeed.

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

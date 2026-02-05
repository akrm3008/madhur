# Infrastructure Access

## Daily Setup Script

Run this every morning (or whenever tunnels/credentials expire) to set up the dev environment.

**Interactive (user's terminal):**
```bash
cd ~/Projects/aisy/common-python-utils
source ./scripts/wsl/aisy-setup.sh dev   # or "prod" for production
```

**Non-interactive (Claude Code) — ask the user for their sudo password first:**
```bash
echo "<sudo_password>" | sudo -S -v 2>/dev/null; cd <aisy_root>/common-python-utils && bash -c 'source ./scripts/wsl/aisy-setup.sh dev' 2>&1
```

Cache sudo credentials *before* the script runs (using `;` not `&&`). This way `sudo -n true` inside the script finds cached credentials and skips the stdin password prompt.

The script handles: AWS SSO auth, DB password retrieval from Secrets Manager, cloudflared RDS tunnel (`localhost:9999`), EFS tunnel + mount (`/mnt/efs`), Prefect profile, and `~/.pgpass` update.

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

```bash
# Login to ECR and pull images
assume aisy-dev --exec bash
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin 780193927358.dkr.ecr.eu-west-1.amazonaws.com
docker pull 780193927358.dkr.ecr.eu-west-1.amazonaws.com/prefect-content-discovery:latest
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

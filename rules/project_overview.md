---
paths:
  - "**"
---

# Aisy Project Overview

Aisy is a security intelligence platform that automates attack surface management (ASM) and vulnerability management for organizations. It discovers, catalogues, and assesses an organisation's internet-facing assets, then imports, deduplicates, correlates, classifies, and triages vulnerability findings from third-party scanners.

## Mono-Repo Structure

- **common-python-utils/** — Shared Python library: SQLAlchemy ORM models, DB helpers, Alembic migrations, CLI tools. All database models live here.
- **asm-prefect/** — Prefect pipelines for domain collection and content discovery (subdomain enumeration, DNS resolution, httpx verification, waymore, ffuf, nuclei, trufflehog).
- **vuln-mgmt-prefect/** — All vulnerability management pipelines: import, dedup, correlation, classification, enrichment, boundary analysis, threat modeling. Contains `ML_GUIDE.md` for ML engineering reference.
- **app-frontend/** — React frontend (yarn). Customer-facing dashboard.
- **hasura-config/** — Hasura GraphQL Engine configuration. Auto-generates a GraphQL API from the Postgres schema.
- **evaluation-labeler-ui/** — Internal React tool for labeling deduplication training data.
- **aisy-supabase/** — Supabase configuration for auth (being migrated to Cognito).

## Data Flow

```
Organisation ── TLDs / ASNs
                    │
                    ▾
            Domain Collection ── Content Discovery
                                       │
                                       ▾
                            Boundary Analysis + Threat Modeling
                                       │
                                       ▾
            Imported Findings ── Dedup ── Correlate ── Classify ── Assign
```

1. **Organisation onboarding** — TLDs and ASNs are registered as scan targets.
2. **Domain collection** — DNS enumeration, IP resolution, live host verification, port scanning.
3. **Content discovery** — Endpoint fuzzing (ffuf), JS analysis, waymore URL collection, nuclei scanning.
4. **Boundary analysis** — LLM clusters live hosts into logical boundaries per threat model.
5. **Vulnerability management** — Findings imported from external scanners, deduplicated, correlated, classified by bug class, and assigned to teams.

## Key Conventions

- **Models live in `common-python-utils/src/db/models/`** — organised by domain subdirectory (business, domain_collection, content_discovery, vulnerability_management, infrastructure).
- **Schema changes use Alembic only** — never modify the DB directly. Use `generate_alembic_migration.sh`.
- **Hasura auto-generates GraphQL** — after migrations, reload Hasura metadata to expose new columns/tables.
- **organisation_id tenancy** — nearly every table has an `organisation_id` FK for multi-tenant isolation.
- **ORM source code is the canonical schema reference** — if the docs disagree with the models, the models win. Models path: `common-python-utils/src/db/models/`.

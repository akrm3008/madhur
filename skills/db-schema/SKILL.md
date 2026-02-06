# db-schema — Database Schema Reference

Use this skill when you need column-level detail about the database schema: exact column names, types, constraints, foreign keys, enums, or indexes.

The always-loaded `data_architecture.md` rule gives you table-level context. For deeper detail, use these sources:

## Primary Sources

1. **ORM models (canonical)** — `common-python-utils/src/db/models/`
   - `business/` — Organisation, TLD, ASN, User, memberships, onboarding
   - `domain_collection/` — DNSEntry, IP, LiveHost, Host, ports, geo, certs, scans
   - `content_discovery/` — Endpoint, EndpointLead, EndpointValue, metadata, nuclei, secrets
   - `vulnerability_management/` — ImportedFinding, duplicates, correlations, boundaries, assignments
   - `infrastructure/` — TaskRun

2. **ML Guide** — `ML_GUIDE.md` in each vuln-mgmt-prefect repo, Section 6
   - Schema overview oriented toward ML/analysis work
   - Querying tips, TLD tiers, key relationships

3. **Database schema guide** — `docs/database-schema-guide.md`
   - All 68 tables with relationship diagrams
   - Organised by pipeline stage

## When to Use

- Writing or modifying SQLAlchemy queries
- Creating Alembic migrations
- Debugging FK constraint errors
- Understanding how tables connect across domains

## Canonical Source

The ORM models in `common-python-utils/src/db/models/` are the single source of truth. If any documentation diverges from the code, the code wins.

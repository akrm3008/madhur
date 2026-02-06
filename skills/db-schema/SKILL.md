# db-schema — Full Database Schema Reference

Use this skill when you need column-level detail about the database schema: exact column names, types, constraints, foreign keys, enums, or indexes. The always-loaded `data_architecture.md` rule gives you table-level context; this skill gives you the full picture.

## Reference Files

- `reference/business.md` — Organisation, TLD, ASN, User, invitations, onboarding
- `reference/domain_collection.md` — DNSEntry, IP, LiveHost, Host, ports, geo, certs, scans
- `reference/content_discovery.md` — Endpoint, EndpointLead, EndpointValue, metadata, nuclei, secrets
- `reference/vulnerability_management.md` — ImportedFinding, duplicates, correlations, assignments, bug classes
- `reference/infrastructure.md` — TaskRun
- `reference/relationships.md` — Cross-domain FK map, common join paths, example patterns

## When to Use

- Writing or modifying SQLAlchemy queries
- Creating Alembic migrations
- Debugging FK constraint errors
- Understanding how tables connect across domains

## Canonical Source

The ORM models in `common-python-utils/src/db/models/` are the single source of truth. If this reference diverges from the code, the code wins.

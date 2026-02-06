---
paths:
  - "**"
---

# Data Architecture

All ORM models live in `common-python-utils/src/db/models/` and inherit from base classes in `models.py`:

- **Base** — bare DeclarativeBase
- **TimestampedBase** — adds `created_at`, `updated_at` (no `id`)
- **TimestampedIdBase** — adds `id`, `created_at`, `updated_at`

## Model Domains

- `business/` — Organisation, TLD, ASN, User, memberships, onboarding
- `domain_collection/` — DNSEntry, IP, LiveHost, Host, ports, geo, certs, scans
- `content_discovery/` — Endpoint, EndpointLead, EndpointValue, metadata, nuclei, secrets
- `vulnerability_management/` — ImportedFinding, duplicates, correlations, boundaries, assignments
- `infrastructure/` — TaskRun

Read the ORM model files directly for column-level detail. For ML/vuln-mgmt context, see `ML_GUIDE.md` in vuln-mgmt-prefect. For relationship diagrams, see `docs/database-schema-guide.md`.

## Cross-Domain Patterns

- **organisation_id tenancy** — present on nearly every table.
- **Many-to-many via association tables** — IPPort ↔ LiveHost, EndpointValue ↔ Param/Header/Title/TechTag, Finding ↔ DuplicateGroup/CorrelationGroup.
- **Polymorphic asset links** — BoundaryMembership and AttributeTagAssociation use nullable FKs to multiple asset tables.
- **JSONB for flexible data** — raw_data, task_metadata, subcategory_schema, questionnaire_responses.
- **Soft deletes** — boundaries use `deleted_at` timestamp.

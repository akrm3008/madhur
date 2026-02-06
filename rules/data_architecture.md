---
paths:
  - "**"
---

# Data Architecture

All ORM models live in `common-python-utils/src/db/models/` and inherit from base classes in `models.py`:

- **Base** — bare DeclarativeBase
- **TimestampedBase** — adds `created_at`, `updated_at` (no `id`)
- **TimestampedIdBase** — adds `id`, `created_at`, `updated_at`

## Domain: Business (`business/`)

Core multi-tenant entities. Everything chains off `Organisation`.

- **Organisation** (`organisations`) — top-level tenant. Has `name`, `type` (CUSTOMER/PROSPECT/BUG_BOUNTY/INTERNAL/DEMO), `allowed_email_domains`.
- **TLD** (`tlds`) — root domains to scan. FK to organisation. Has `tier`, `in_scope`, `skip_reason`.
- **ASN** (`org_asns`) — IP ranges to scan. FK to organisation.
- **User** (`users`) — identified by `cognito_sub`.
- **UserOrgMembership** (`user_org_memberships`) — many-to-many User ↔ Organisation with `role` (USER/OWNER).
- **UserInvitation**, **TrialScan**, **CustomerOnboarding**, **AdminImpersonationLog** — signup and onboarding flow.

## Domain: Domain Collection (`domain_collection/`)

Asset discovery pipeline. Starts from TLDs/ASNs, discovers the live attack surface.

- **DNSEntry** (`dns_entries`) — DNS records. `key` = hostname, `value` = resolved value, `record_type` (A/AAAA/CNAME). FK to `tlds`, `ips`, `live_hosts`. This is the starting point of asset discovery.
- **IP** (`ips`) — unique IP addresses (INET type). Has `cloud_provider`, `cdn`, `waf` enums.
- **LiveHost** (`live_hosts`) — hosts verified to respond on HTTP. `domain` includes scheme (e.g., `https://example.com`). One-to-one with Host.
- **Host** (`hosts`) — protocol context (`http`/`https`). Owns endpoints and content discovery scans.
- **IPPort** (`ip_ports`) — open ports on IPs. Many-to-many with LiveHost via `port_live_host_association`.
- **VHost** (`vhosts`) — virtual hosts discovered on ports.
- **IPGeolocation** (`ip_geolocations`) — geo data. One-to-one with IP.
- **ServiceLayer** (`service_layers`) — web server stack fingerprints (up to 3 layers). One-to-one with LiveHost.
- **CertificateIssue** (`certificate_issues`) — TLS cert problems. FK to LiveHost.
- **RelatedDomainLead** (`related_domain_leads`) — third-party domains found during analysis.
- **DomainCollectionScan** (`scans`) — tracks scan runs per TLD.

## Domain: Content Discovery (`content_discovery/`)

What's running on each live host — endpoints, parameters, headers, titles.

- **Endpoint** (`endpoints`) — confirmed paths. FK to `hosts`. Has `endpoint_path`, `http_method`.
- **EndpointLead** (`endpoint_leads`) — unverified paths from waymore/jsluice. Hierarchy: `host_id` > `dns_entry_id` > `tld_id` (most to least specific).
- **EndpointValue** (`endpoint_values`) — HTTP response snapshots (status_code, content_length, etc.). Tracks changes over time.
- **Param/Header/Title/TechTag** — metadata entities, many-to-many with EndpointValue via association tables.
- **ContentDiscoveryScan** (`content_discovery_scans`) — per-host scan tracking. Unique on (host_id, scan_type, http_method).
- **NucleiScanResult/NucleiExtractedResult** — vulnerability scan findings and extracted secrets.
- **SecretsScanResult** (`secrets_scan_results`) — secrets found by trufflehog.

## Domain: Vulnerability Management (`vulnerability_management/`)

Imported findings from external scanners, deduplicated, correlated, classified.

- **ImportedFinding** (`imported_findings`) — raw findings. Links to `tlds`, `live_hosts`, `ips`, `dns_entries`. Has `severity`, `status`, `raw_data` (JSONB).
- **FindingDuplicateGroup/Membership** — true duplicate groups. Has `master_finding_id`.
- **FindingCorrelationGroup/Membership** — AI-identified correlations. Supports linchpin cascade (fixing one finding impacts others' severity).
- **AssetReference** (`asset_references`) — polymorphic link from findings to any asset type.
- **Boundary** (`boundaries`) — LLM-generated asset groupings. Supports hierarchy via `parent_boundary_id`.
- **BoundaryMembership** (`boundary_memberships`) — polymorphic: links boundaries to IPs, live_hosts, dns_entries, ports, or vhosts.
- **ThreatModel** (`threat_models`) — configuration-driven definitions. FK to organisation.
- **Team** (`teams`) — owns boundaries, has SLA/contact info.
- **DomainAnalysis/DomainEndpointAnalysis** — AI risk assessments per host/endpoint.

## Domain: Infrastructure (`infrastructure/`)

- **TaskRun** (`task_runs`) — execution tracking for pipeline tasks. Links to `scans` and `content_discovery_scans`.

## Cross-Domain Patterns

- **organisation_id tenancy** — present on nearly every table.
- **Many-to-many via association tables** — IPPort ↔ LiveHost, EndpointValue ↔ Param/Header/Title/TechTag, Finding ↔ DuplicateGroup/CorrelationGroup.
- **Polymorphic asset links** — BoundaryMembership and AttributeTagAssociation use nullable FKs to multiple asset tables.
- **JSONB for flexible data** — raw_data, task_metadata, subcategory_schema, questionnaire_responses.
- **Soft deletes** — boundaries use `deleted_at` timestamp.

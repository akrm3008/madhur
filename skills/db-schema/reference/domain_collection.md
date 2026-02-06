# Domain Collection Models

Source: `common-python-utils/src/db/models/domain_collection/`

## DNSEntry (`dns_entries`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| organisation_id | Integer | FK → organisations.id, indexed |
| tld_id | Integer | FK → tlds.id |
| record_type | String(10) | A, AAAA, CNAME, etc. |
| key | String(250) | the hostname (e.g., `web.example.com`) |
| value | String(500) | resolved value (IP or CNAME target) |
| ip_id | Integer | FK → ips.id, nullable (set for A/AAAA) |
| live_host_id | Integer | FK → live_hosts.id, nullable |
| resolver | String(100) | nullable — DNS resolver used |

Indexes: trigram on key (GIN), composite on (tld_id, created_at), partial for CNAME/non-CNAME

Relationships: organisation, tld_record, ip, live_host

## IP (`ips`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| ip | INET | unique |
| organisation_id | Integer | FK → organisations.id, indexed |
| asn_id | Integer | FK → org_asns.id, nullable |
| cloud_provider | Enum(CloudProvider) | nullable |
| cdn | Enum(CDN) | nullable |
| waf | Enum(WAF) | nullable |
| waf_name_other | String(100) | nullable (when waf=OTHER) |
| is_ipv6 | Boolean | default False |

Relationships: organisation, asn, dns_entries, ports, geolocation (1:1)

### CloudProvider Enum
AWS, GOOGLE_CLOUD, AZURE, ORACLE, ZSCALER, OFFICE365

### CDN Enum
LEASEWEB, GCORE, CLOUDFRONT, FASTLY, GOOGLE, STACKPATH, GOCACHE, EDGECAST

### WAF Enum
AKAMAI, CLOUDFLARE, INCAPSULA, FASTLY, MODSECURITY, SUCURI, F5, FORTINET, BARRACUDA, AZURE_FRONT_DOOR, OTHER

## LiveHost (`live_hosts`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| organisation_id | Integer | FK → organisations.id, indexed |
| domain | String(250) | unique — includes scheme (`https://example.com`) |
| host_id | Integer | FK → hosts.id, unique |

Indexes: trigram on domain (GIN), btree on domain, composite (domain, created_at), composite (host_id, domain)

Relationships: organisation, dns_entries, ports (M2M via port_live_host_association), host (1:1), certificate_issues, service_layer (1:1), boundary_memberships

## Host (`hosts`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| organisation_id | Integer | FK → organisations.id, indexed |
| protocol | String(10) | default "https" |

Relationships: organisation, vhost, live_host (1:1), endpoints, endpoint_leads, content_discovery_scans

## VHost (`vhosts`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| organisation_id | Integer | FK → organisations.id |
| port_id | Integer | FK → ip_ports.id |
| host_id | Integer | FK → hosts.id, unique |
| vhost | String(250) | |

## IPPort (`ip_ports`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| organisation_id | Integer | FK → organisations.id |
| port | Integer | |
| ip_id | Integer | FK → ips.id, indexed |
| alive | Boolean | default False |
| last_seen_at | TIMESTAMP | nullable |
| last_scanned_at | TIMESTAMP | nullable |

Relationships: organisation, ip, live_hosts (M2M), vhosts

## PortLiveHostAssociation (`port_live_host_association`)

Base: TimestampedBase (composite PK)

| Column | Type | Constraints |
|--------|------|-------------|
| port_id | Integer | PK, FK → ip_ports.id |
| live_host_id | Integer | PK, FK → live_hosts.id |

## IPGeolocation (`ip_geolocations`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| organisation_id | Integer | FK → organisations.id |
| ip_id | Integer | FK → ips.id (CASCADE), unique |
| latitude, longitude | String(20) | nullable |
| city | String(100) | nullable |
| country | String(100) | nullable |
| continent | String(50) | nullable |
| isp | String(200) | nullable |
| organization | String(200) | nullable |
| connection_type | String(50) | nullable |

## ServiceLayer (`service_layers`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| organisation_id | Integer | FK → organisations.id |
| live_host_id | Integer | FK → live_hosts.id (CASCADE), unique |
| layer_1_type | String(50) | indexed |
| layer_2_type | String(50) | nullable, indexed |
| layer_3_type | String(50) | nullable, indexed |

## CertificateIssue (`certificate_issues`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| organisation_id | Integer | FK → organisations.id |
| live_host_id | Integer | FK → live_hosts.id |
| expired, self_signed, mismatched, revoked, untrusted | Boolean | default False |
| is_current | Boolean | default True, indexed |

## RelatedDomainLead (`related_domain_leads`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| organisation_id | Integer | FK → organisations.id |
| domain | String(255) | indexed |
| endpoint | String(1000) | nullable |
| source | String(100) | waymore, autodiscover, etc. |
| source_url | String(2000) | nullable |
| discovered_at | DateTime | auto |
| tld_id | Integer | FK → tlds.id |
| is_interesting | Boolean | default False |
| viewed_at | DateTime | nullable |

## DomainCollectionScan (`scans`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| organisation_id | Integer | FK → organisations.id |
| tld_id | Integer | FK → tlds.id |
| orchestrator_flow_run_id | String(250) | unique |
| pre_waymore_flow_run_id | String(250) | nullable |
| waymore_flow_run_id | String(250) | nullable |
| post_waymore_flow_run_id | String(250) | nullable |
| status | Enum(ScanStatus) | default PENDING |
| started_at, completed_at | DateTime | nullable |
| settings | JSON | nullable |
| results | JSON | nullable |

### ScanStatus Enum
PENDING, RUNNING, COMPLETED, FAILED, CANCELLED

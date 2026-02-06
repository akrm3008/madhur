# Content Discovery Models

Source: `common-python-utils/src/db/models/content_discovery/`

## Endpoint (`endpoints`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| host_id | Integer | FK → hosts.id |
| endpoint_path | String(1000) | |
| http_method | String(10) | |
| alive | Boolean | default True |
| last_seen_at | TIMESTAMP | nullable |
| last_scanned_at | TIMESTAMP | nullable |

Indexes: (created_at), (host_id, created_at)

Relationships: host, endpoint_values, endpoint_leads

## EndpointLead (`endpoint_leads`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| host_id | Integer | FK → hosts.id, nullable |
| endpoint_id | Integer | FK → endpoints.id, nullable |
| dns_entry_id | Integer | FK → dns_entries.id, nullable |
| tld_id | Integer | FK → tlds.id, nullable |
| domain_hint | String(255) | nullable — domain string when no DNSEntry match |
| endpoint_path | String(1000) | |
| source | String(100) | waymore, linkfinder, jsluice, etc. |
| is_interesting | Boolean | default False |
| viewed_at | TIMESTAMP | nullable |

Indexes: (host_id), (dns_entry_id), (tld_id), (tld_id, created_at), (created_at), (host_id, created_at), (source), partial index on host_id IS NOT NULL

Relationships: host, endpoint, dns_entry, tld

## EndpointValue (`endpoint_values`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| endpoint_id | Integer | FK → endpoints.id, indexed |
| status_code | Integer | nullable |
| content_length | Integer | nullable |
| content_type | String(250) | nullable |
| redirect_location | String(1024) | nullable |
| response_size | Integer | nullable — bytes |
| response_time | Float | nullable — seconds |
| words | Integer | nullable |
| lines | Integer | nullable |
| count_headers | Integer | nullable |
| words_title | Integer | nullable |
| length_title | Integer | nullable |
| count_css_files | Integer | nullable |
| count_js_files | Integer | nullable |
| count_tags | Integer | nullable |
| is_swagger | Boolean | default False |
| is_graphql | Boolean | default False |
| is_interesting | Boolean | default False |

Indexes: (endpoint_id), (endpoint_id, created_at), (created_at)

Relationships: endpoint, params (M2M), headers (M2M), titles (M2M), tech_tags (M2M)

## Param (`params`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| param | String(250) | unique |

## Header (`headers`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| header | String(250) | unique |

## Title (`titles`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| title | String(500) | unique |
| is_interesting | Boolean | default True |

## TechTag (`tech_tags`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| tech_tag | String(250) | unique |

## Association Tables

All use TimestampedBase (composite PK, no auto id):

- **EndpointValueParamAssociation** (`endpoint_value_param_association`): endpoint_value_id + param_id
- **EndpointValueHeaderAssociation** (`endpoint_value_header_association`): endpoint_value_id + header_id
- **EndpointValueTitleAssociation** (`endpoint_value_title_association`): endpoint_value_id + title_id
- **EndpointValueTechTagAssociation** (`endpoint_value_tech_tag_association`): endpoint_value_id + tech_tag_id

## ContentDiscoveryScan (`content_discovery_scans`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| host_id | Integer | FK → hosts.id (CASCADE) |
| scan_type | String(50) | |
| http_method | String(10) | default "GET" |
| target_url_override | String(500) | nullable |
| status | Enum(ContentDiscoveryScanStatus) | default PENDING |
| started_at, completed_at, last_scan_at | DateTime | nullable |
| error_message | String(1000) | nullable |
| endpoints_found | Integer | nullable |
| new_endpoints_found | Integer | nullable |

Unique: (host_id, scan_type, http_method)

### ContentDiscoveryScanStatus Enum
PENDING, RUNNING, COMPLETED, FAILED, SKIPPED

## NucleiScanResult (`nuclei_scan_results`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| organisation_id | Integer | FK, nullable |
| tld_id | Integer | FK, nullable |
| host_id | Integer | FK, nullable |
| task_run_id | Integer | FK, nullable |
| extracted_result_id | Integer | FK → nuclei_extracted_results.id, nullable |
| template_id | String(500) | indexed |
| severity | Enum(NucleiSeverity) | nullable |
| domain | String(500) | indexed |
| matched_at | String(2000) | nullable |
| endpoint | String(2000) | nullable |
| curl_command | Text | nullable |
| tags | ARRAY(String) | nullable |
| scan_type | String(50) | default "template" |
| scan_reason | String(50) | nullable |
| scan_date | DateTime | auto |

### NucleiSeverity Enum
INFO, LOW, MEDIUM, HIGH, CRITICAL

## NucleiExtractedResult (`nuclei_extracted_results`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| result_value | Text | |
| content_type | String(50) | default "generic" (jwt, credential, api_key, technology) |
| decoded_content | Text | nullable |
| discovered_at, last_seen_at | DateTime | auto |

Unique: (result_value, content_type)

## SecretsScanResult (`secrets_scan_results`)

Base: TimestampedIdBase

| Column | Type | Constraints |
|--------|------|-------------|
| id | Integer | PK |
| organisation_id | Integer | FK, indexed |
| tld_id | Integer | FK, indexed |
| file_path | String(1000) | |
| line_number | Integer | nullable |
| secret_type | String(100) | — DetectorName from trufflehog |
| secret_value | Text | |
| secret_value_v2 | Text | nullable — RawV2 |
| is_verified | Boolean | default False |
| discovered_at | DateTime | auto |
| reviewed_at | DateTime | nullable |
| is_false_positive | Boolean | default False |

Unique: (tld_id, file_path, secret_value)
